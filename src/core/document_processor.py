import os
from typing import List, Dict, Optional, Union, Any
import tempfile
import hashlib
from datetime import datetime
import PyPDF2
from openai import OpenAI
import pinecone
from pinecone import ServerlessSpec
import time
from ..utils.storage import upload_encrypted_pdf

class DocumentProcessor:
    def __init__(self, user_id: int = None, api_keys: Dict[str, str] = None):
        self.user_id = user_id
        self.api_keys = api_keys or {}
        self.pc = None
        self.namespace = str(user_id) if user_id is not None else None
        # Create user-specific index name
        self.index_name = f"edu-assistant-user-{user_id}" if user_id else "educational-assistant"
        self.stored_chunks = []  # Store chunks locally if Pinecone isn't available
        self._initialize_pinecone()

    def _initialize_pinecone(self) -> None:
        """Initialize Pinecone client if API key is available"""
        # Try user's API keys first, fallback to environment variables
        api_key = self.api_keys.get('pinecone_key') or os.environ.get("PINECONE_API_KEY")

        if not api_key:
            print("Warning: Pinecone API key not found. Required: PINECONE_API_KEY")
            self.pc = None
            return

        try:
            print("Initializing Pinecone with latest SDK (no environment required)")
            print(f"Using API key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else ''}")
            self.pc = pinecone.Pinecone(
                api_key=api_key
            )

            # Ensure index exists
            existing_indexes = [index.name for index in self.pc.list_indexes()]
            if self.index_name not in existing_indexes:
                print(f"Creating new Pinecone index: {self.index_name}")
                try:
                    self.pc.create_index(
                        name=self.index_name,
                        dimension=1536,  # OpenAI embeddings dimension
                        metric="cosine",
                        spec=ServerlessSpec(
                            cloud='aws',
                            region='us-east-1'
                        )
                    )
                    print(f"Waiting for index {self.index_name} to be ready...")
                    # Wait for index to be ready
                    time.sleep(20)
                except Exception as create_error:
                    # If index already exists (409 error), that's fine
                    if "ALREADY_EXISTS" in str(create_error) or "409" in str(create_error):
                        print(f"Index {self.index_name} already exists, continuing...")
                    else:
                        raise create_error
            else:
                print(f"Using existing index: {self.index_name}")

            # Verify we can access the index
            try:
                index = self.pc.Index(self.index_name)
                # Test the index with a simple describe operation
                stats = index.describe_index_stats()
                print(f"Index stats: {stats.total_vector_count} vectors")
            except Exception as index_error:
                print(f"Warning: Could not access index: {str(index_error)}")
                # Don't fail completely, the index might still work
                
            print("Pinecone initialized successfully")
            return True
        except Exception as e:
            error_msg = str(e)
            print(f"Warning: Failed to initialize Pinecone: {error_msg}")
            # Don't set pc to None if it's just an index access issue
            if "401" in error_msg or "Unauthorized" in error_msg:
                self.pc = None
            return False

    def _calculate_document_hash(self, file_content: bytes) -> str:
        """Calculate SHA-256 hash of document content"""
        return hashlib.sha256(file_content).hexdigest()

    def _check_document_exists(self, doc_hash: str) -> bool:
        """Check if document already exists in Pinecone for this user"""
        if not self.pc:
            # Check local database if Pinecone not available
            if self.user_id:
                from ..database.database import Database
                db = Database()
                db.initialize()
                existing = db.get_document_by_hash(self.user_id, doc_hash)
                return existing is not None
            return False

        try:
            index = self.pc.Index(self.index_name)
            # Query for document metadata with user-specific filter
            filter_dict = {"document_hash": doc_hash}
            if self.user_id:
                filter_dict["user_id"] = self.user_id
                
            results = index.query(
                vector=[0.0] * 1536,  # Dummy vector for metadata-only query
                filter=filter_dict,
                top_k=1,
                include_metadata=True,
                namespace=self.namespace
            )
            exists = len(results.matches) > 0
            if exists:
                print(f"Document with hash {doc_hash} already exists for user {self.user_id}")
                # Print metadata of existing document for debugging
                if results.matches:
                    metadata = results.matches[0].metadata
                    print(f"Existing document details: {metadata.get('filename', 'unknown')}")
            return exists
        except Exception as e:
            print(f"Error checking document existence in Pinecone: {str(e)}")
            return False

    def process_pdf(self, pdf_file) -> str:
        """Process uploaded PDF file and store in Pinecone if not already present"""
        try:
            # Calculate document hash
            doc_hash = self._calculate_document_hash(pdf_file.getvalue())

            # Check if document already exists
            if self._check_document_exists(doc_hash):
                print(f"Skipping upload for existing document: {pdf_file.name}")
                return "already_exists"

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(pdf_file.getvalue())
                tmp_path = tmp_file.name

            storage_key = upload_encrypted_pdf(self.user_id, pdf_file.name, pdf_file.getvalue())

            # Extract text from PDF
            text_chunks = self._extract_text(tmp_path)
            storage_success = False

            # Try to store in Pinecone if we have new content
            if self.pc and text_chunks:
                try:
                    storage_success = self._store_in_pinecone(text_chunks, doc_hash, pdf_file.name)
                except Exception as e:
                    print(f"Pinecone storage failed: {str(e)}")
                    storage_success = False
                    
            # Also save document metadata to local database
            if storage_success and self.user_id:
                from ..database.database import Database
                db = Database()
                db.initialize()
                try:
                    metadata = f"chunks: {len(text_chunks)}"
                    if storage_key:
                        metadata += f"; storage_key:{storage_key}"
                    db.save_document(self.user_id, pdf_file.name, doc_hash, metadata)
                except Exception as e:
                    print(f"Error saving document metadata: {str(e)}")

            # Clean up
            os.unlink(tmp_path)

            if storage_success:
                print(f"Successfully stored new document: {pdf_file.name}")
                try:
                    from ..utils.audit import log_action
                    meta = pdf_file.name
                    if storage_key:
                        meta += f"; storage_key={storage_key}"
                    log_action(self.user_id, "upload_document", meta)
                except Exception:
                    pass
                return "stored_in_pinecone"
            else:
                return "storage_failed"

        except Exception as e:
            raise Exception(f"Error processing PDF: {str(e)}")

    def _extract_text(self, pdf_path: str) -> List[str]:
        """Extract text from PDF and split into chunks"""
        chunks = []
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                for page in pdf_reader.pages:
                    text = page.extract_text()
                    # Increased chunk size to 2000 chars to ensure complete lists stay together
                    # Also add overlap to prevent splitting important content
                    chunk_size = 2000
                    overlap = 500
                    for i in range(0, len(text), chunk_size - overlap):
                        chunk = text[i:i + chunk_size]
                        if chunk.strip():  # Only add non-empty chunks
                            chunks.append(chunk)

            return chunks
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")

    def _store_in_pinecone(self, text_chunks: List[str], doc_hash: str, filename: str) -> bool:
        """Store text chunks in Pinecone index with document metadata"""
        if not self.pc:
            print("Pinecone not initialized, storing chunks locally")
            self.stored_chunks.extend(text_chunks)
            return False

        try:
            index = self.pc.Index(self.index_name)
            stored_count = 0
            batch_size = 10
            vectors_batch = []

            print(f"Starting to store document '{filename}' in Pinecone...")
            print(f"Total chunks to process: {len(text_chunks)}")

            # Generate embeddings and store in batches
            for i, chunk in enumerate(text_chunks):
                try:
                    embedding = self._get_embedding(chunk)
                    vector_id = f"doc_{doc_hash}_chunk_{i}"

                    # Store with document metadata
                    metadata = {
                        "text": chunk,
                        "document_hash": doc_hash,
                        "filename": filename,
                        "chunk_index": i,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Add user_id to metadata if available
                    if self.user_id:
                        metadata["user_id"] = self.user_id

                    vectors_batch.append((vector_id, embedding, metadata))

                    # Process batch when it reaches batch_size
                    if len(vectors_batch) >= batch_size:
                        index.upsert(vectors=vectors_batch, namespace=self.namespace)
                        stored_count += len(vectors_batch)
                        vectors_batch = []
                        print(f"Stored batch of {batch_size} chunks (Total: {stored_count}/{len(text_chunks)})")

                except Exception as e:
                    print(f"Error processing chunk {i}: {str(e)}")
                    continue

            # Store any remaining vectors
            if vectors_batch:
                index.upsert(vectors=vectors_batch, namespace=self.namespace)
                stored_count += len(vectors_batch)
                print(f"Stored final batch of {len(vectors_batch)} chunks")

            success = stored_count > 0
            print(f"Document storage {'successful' if success else 'failed'}: {stored_count}/{len(text_chunks)} chunks stored in Pinecone")
            return success

        except Exception as e:
            print(f"Error storing in Pinecone: {str(e)}")
            # Fallback to local storage
            self.stored_chunks.extend(text_chunks)
            return False

    def verify_document_storage(self, doc_hash: str) -> Dict[str, Any]:
        """Verify if a document is properly stored in Pinecone"""
        if not self.pc:
            return {
                "status": "not_stored",
                "message": "Pinecone is not initialized",
                "chunks_found": 0
            }

        try:
            index = self.pc.Index(self.index_name)
            # Query for document metadata
            results = index.query(
                vector=[0.0] * 1536,  # Dummy vector for metadata-only query
                filter={"document_hash": doc_hash},
                top_k=1000,
                include_metadata=True,
                namespace=self.namespace
            )

            chunks_found = len(results.matches)
            if chunks_found > 0:
                sample_metadata = results.matches[0].metadata
                return {
                    "status": "stored",
                    "message": f"Document found in Pinecone with {chunks_found} chunks",
                    "filename": sample_metadata.get("filename"),
                    "chunks_found": chunks_found,
                    "upload_time": sample_metadata.get("timestamp")
                }
            else:
                return {
                    "status": "not_found",
                    "message": "Document not found in Pinecone",
                    "chunks_found": 0
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error verifying document storage: {str(e)}",
                "chunks_found": 0
            }

    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using OpenAI"""
        try:
            # Use user's API key if available, fallback to environment
            api_key = self.api_keys.get('openai_key') or os.environ.get("OPENAI_API_KEY")
            client = OpenAI(api_key=api_key)
            response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"Error generating embedding: {str(e)}")

    def list_stored_documents(self) -> List[Dict[str, str]]:
        """Return a list of stored documents with their metadata for the current user"""
        # First try to get from local database
        if self.user_id:
            try:
                from ..database.database import Database
                db = Database()
                db.initialize()
                local_docs = db.get_user_documents(self.user_id)
                return [
                    {
                        "filename": doc["filename"],
                        "uploaded_at": doc["upload_timestamp"]
                    }
                    for doc in local_docs
                ]
            except Exception as e:
                print(f"Error getting documents from local database: {str(e)}")
        
        if not self.pc:
            return []

        try:
            index = self.pc.Index(self.index_name)
            # Query with a dummy vector to get metadata for this user
            filter_dict = {}
            if self.user_id:
                filter_dict["user_id"] = self.user_id
                
            results = index.query(
                vector=[0.0] * 1536,
                top_k=1000,  # Increased from 100 to 1000 to handle more documents
                include_metadata=True,
                filter=filter_dict if filter_dict else None,
                namespace=self.namespace
            )

            # Extract unique documents using document_hash, with timestamp-based sorting
            documents = {}
            for match in results.matches:
                doc_hash = match.metadata.get("document_hash")
                if doc_hash and doc_hash not in documents:
                    documents[doc_hash] = {
                        "filename": match.metadata.get("filename"),
                        "timestamp": match.metadata.get("timestamp")
                    }

            # Sort documents by timestamp, most recent first
            sorted_docs = sorted(
                documents.values(),
                key=lambda x: x["timestamp"] if x["timestamp"] else "",
                reverse=True
            )

            return [
                {"filename": info["filename"], "uploaded_at": info["timestamp"]}
                for info in sorted_docs
            ]
        except Exception as e:
            print(f"Error listing documents: {str(e)}")
            return []

    def get_context(
        self,
        question: str,
        specific_document: str = None,
        return_metadata: bool = False
    ) -> List[Union[str, Dict[str, Any]]]:
        """Return relevant context for the question from all available sources"""
        if not question:
            return []

        if self.pc:
            try:
                question_embedding = self._get_embedding(question)

                # Identify key relationship terms
                relationship_terms = [
                    "introduced", "met", "mentor", "worked with",
                    "studied", "learned from", "shadow", "interview"
                ]

                # Check if question is about relationships/meetings
                is_relationship_query = any(term in question.lower() for term in relationship_terms)

                # Query parameters optimized for relationship context
                index = self.pc.Index(self.index_name)
                
                # Build filter for user-specific and document-specific queries
                filter_dict = {}
                if self.user_id:
                    filter_dict["user_id"] = self.user_id
                if specific_document:
                    filter_dict["filename"] = specific_document
                
                results = index.query(
                    vector=question_embedding,
                    top_k=300 if is_relationship_query else 200,  # Increased for relationship queries
                    include_metadata=True,
                    filter=filter_dict if filter_dict else None,
                    namespace=self.namespace,
                    score_threshold=0.5 if is_relationship_query else 0.6  # Lower threshold for relationship context
                )

                print(f"\nQuerying for: {question}")
                print(f"Found {len(results.matches)} potential matches")

                # Process and sort matches
                sorted_matches = sorted(results.matches, key=lambda x: x.score, reverse=True)
                seen_content = set()
                contexts = []

                # Look for chunks containing key indicators
                key_indicators = [
                    # Success Skills indicators
                    "ten success skills",
                    "10 success skills",
                    "all ten skills",
                    "Technology of Success skills",
                    # Relationship/Meeting indicators
                    "introduced me to",
                    "I met",
                    "worked with",
                    "studied with",
                    "interviewed",
                    "shadowed"
                ]

                # Process matches with special handling
                for match in sorted_matches:
                    chunk_text = match.metadata.get("text", "").strip()
                    filename = match.metadata.get("filename", "unknown")

                    # Skip if we've seen this content
                    if not chunk_text or chunk_text in seen_content:
                        continue

                    # Check if this chunk contains key indicators
                    has_indicators = any(indicator.lower() in chunk_text.lower()
                                       for indicator in key_indicators)

                    # For relationship questions, look for connected context
                    if is_relationship_query:
                        relationship_relevance = sum(1 for term in relationship_terms
                                                  if term in chunk_text.lower())
                        if relationship_relevance > 0:
                            print(f"Found relationship context in {filename}")
                            print(f"Score: {match.score}")

                    seen_content.add(chunk_text)
                    contexts.append({
                        'text': chunk_text,
                        'score': match.score,
                        'has_indicators': has_indicators,
                        'filename': filename
                    })

                # Sort contexts prioritizing matches with indicators and higher scores
                sorted_contexts = sorted(
                    contexts,
                    key=lambda x: (x['has_indicators'], x['score']),
                    reverse=True
                )

                # Return more context for relationship queries
                limit = 25 if is_relationship_query else 15
                top_contexts = sorted_contexts[:limit]

                if return_metadata:
                    return top_contexts

                return [ctx['text'] for ctx in top_contexts]

            except Exception as e:
                print(f"Error querying Pinecone: {str(e)}")
                return []
        else:
            print("Pinecone not initialized")
            return []

    def delete_document(self, filename: str) -> Dict[str, Any]:
        """Delete a document and its chunks from Pinecone and local database"""
        if not self.pc:
            return {
                "status": "error",
                "message": "Pinecone is not initialized"
            }

        try:
            index = self.pc.Index(self.index_name)

            # Build filter for user-specific document deletion
            filter_dict = {"filename": filename}
            if self.user_id:
                filter_dict["user_id"] = self.user_id
                
            # Query for document metadata to find all related vectors
            results = index.query(
                vector=[0.0] * 1536,  # Dummy vector for metadata-only query
                filter=filter_dict,
                top_k=1000,  # Set high to ensure we get all chunks
                include_metadata=True,
                namespace=self.namespace
            )

            if not results.matches:
                return {
                    "status": "not_found",
                    "message": f"Document '{filename}' not found in the index"
                }

            # Collect vector IDs to delete
            vector_ids = [match.id for match in results.matches]

            # Delete vectors from Pinecone
            index.delete(ids=vector_ids, namespace=self.namespace)
            
            # Also delete from local database
            if self.user_id:
                try:
                    from ..database.database import Database
                    db = Database()
                    db.initialize()
                    # Find and delete document record
                    db.execute(
                        "DELETE FROM documents WHERE user_id = ? AND filename = ?",
                        (self.user_id, filename)
                    )
                except Exception as e:
                    print(f"Error deleting from local database: {str(e)}")

            try:
                from ..utils.audit import log_action
                log_action(self.user_id, "delete_document", filename)
            except Exception:
                pass

            return {
                "status": "success",
                "message": f"Successfully deleted document '{filename}' ({len(vector_ids)} chunks)",
                "chunks_deleted": len(vector_ids)
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error deleting document: {str(e)}"
            }

    def delete_document_by_hash(self, document_hash: str) -> Dict[str, Any]:
        """Delete a document by its hash from Pinecone"""
        if not self.pc:
            return {
                "status": "error",
                "message": "Pinecone is not initialized"
            }

        try:
            index = self.pc.Index(self.index_name)

            # Query for document metadata
            results = index.query(
                vector=[0.0] * 1536,  # Dummy vector for metadata-only query
                filter={"document_hash": document_hash},
                top_k=1000,  # Set high to ensure we get all chunks
                include_metadata=True,
                namespace=self.namespace
            )

            if not results.matches:
                return {
                    "status": "not_found",
                    "message": f"Document with hash '{document_hash}' not found"
                }

            # Collect vector IDs to delete
            vector_ids = [match.id for match in results.matches]

            # Delete vectors from Pinecone
            index.delete(ids=vector_ids, namespace=self.namespace)

            return {
                "status": "success",
                "message": f"Successfully deleted document with hash '{document_hash}' ({len(vector_ids)} chunks)",
                "chunks_deleted": len(vector_ids)
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error deleting document: {str(e)}"
            }
