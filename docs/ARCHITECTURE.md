# Architecture Deep Dive

This document provides a comprehensive technical overview of the Educational AI Assistant's agentic architecture, design patterns, and implementation details.

## Table of Contents
1. [System Overview](#system-overview)
2. [Agentic Design Pattern](#agentic-design-pattern)
3. [Tool Specifications](#tool-specifications)
4. [RAG Pipeline](#rag-pipeline)
5. [Multi-User Architecture](#multi-user-architecture)
6. [Data Flow](#data-flow)
7. [Security Model](#security-model)
8. [Scalability Considerations](#scalability-considerations)

---

## System Overview

The Educational AI Assistant implements a **tool-calling agent** pattern using LangChain's `AgentExecutor` framework. The system combines:

- **Reasoning Engine**: OpenAI GPT-4o-mini with function-calling capabilities
- **Memory System**: Windowed conversation buffer (6 turns)
- **Tool Layer**: Four specialized tools for retrieval and processing
- **Data Layer**: Vector DB (Pinecone) + Relational DB (PostgreSQL)

### Design Philosophy

The architecture follows these core principles:

1. **Separation of Concerns**: Agent reasoning is decoupled from tool implementation
2. **Grounding First**: Agent is instructed to always retrieve context before answering
3. **User Isolation**: Complete data separation at the namespace level
4. **Extensibility**: New tools can be added without modifying agent logic

---

## Agentic Design Pattern

### What Makes It Agentic?

Traditional chatbots follow **if-then logic**: "If user asks X, do Y." Agentic systems make **autonomous decisions** based on reasoning about the task.

#### Comparison

**Traditional Pattern:**
```
User: "Summarize chapter 3"
System: [Fixed summarization routine]
```

**Agentic Pattern:**
```
User: "Summarize chapter 3"
Agent Reasoning:
  1. User wants summary → need context first
  2. Call search_documents("chapter 3")
  3. Retrieved 5 chunks → call summarize_text(chunks)
  4. Return formatted response with citations
```

### Agent Executor Flow

```python
# Simplified agent loop (LangChain internals)
while not finished:
    # 1. Agent analyzes current state
    action = agent.plan(input, memory, tool_results)
    
    # 2. Agent selects tool or finishes
    if action.is_tool_call:
        tool_result = execute_tool(action.tool, action.args)
        memory.add(tool_result)
    else:
        return action.final_answer
```

### Agent Implementation

**File**: `src/core/agent.py`

```python
class AgentResponder:
    """LangChain-powered agent that orchestrates tool use for QA."""
    
    def __init__(self, processor, api_key=None):
        # 1. Initialize LLM with function-calling
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,  # Lower for consistency
            api_key=api_key
        )
        
        # 2. Build tools (search, list, summarize)
        self.tools = build_tools(processor, self.llm)
        
        # 3. Configure windowed memory
        self.memory = ConversationBufferWindowMemory(
            k=6,  # Keep 6 most recent turns
            return_messages=True,
            memory_key="chat_history"
        )
        
        # 4. Create agent with system prompt
        prompt = self._build_system_prompt()
        agent = create_openai_functions_agent(
            self.llm, self.tools, prompt
        )
        
        # 5. Wrap in executor
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=False,
            handle_parsing_errors=True
        )
```

### System Prompt Design

The system prompt **guides** agent behavior without hardcoding logic:

```
You are an educational assistant that must ground answers 
in the user's documents.

RULES:
1. Always call tools to retrieve context before answering
2. For summaries: search_documents → summarize_text
3. For follow-ups: use summarize_last_answer if referencing prior reply
4. Cite sources: [chunk_idx] (filename)
5. If no context found, state clearly rather than guessing
```

This allows the agent to **reason** about when and how to use tools.

---

## Tool Specifications

**File**: `src/core/tools.py`

The agent has access to four specialized tools, each with a clear responsibility.

### 1. `list_documents`

**Purpose**: Enumerate available documents for the current user

**Schema**:
- **Input**: None (or ignored string)
- **Output**: Formatted list of documents with upload timestamps

**Implementation**:
```python
def list_documents(_input: str = "") -> str:
    docs = processor.list_stored_documents()
    if not docs:
        return "No documents available."
    return "\n".join(
        f"- {doc['filename']} (uploaded: {doc['uploaded_at']})"
        for doc in docs
    )
```

**Agent Use Case**: When user asks "What documents do I have?"

---

### 2. `search_documents`

**Purpose**: Perform semantic search across user's document corpus

**Schema**:
- **Input**:
  - `query` (str, required): Search query
  - `document` (str, optional): Specific filename to search
  - `limit` (int, default=10): Max chunks to return
- **Output**: Formatted context chunks with citations

**Implementation**:
```python
def search_documents(query: str, document: Optional[str] = None, 
                    limit: int = 10) -> str:
    contexts = processor.get_context(
        question=query,
        specific_document=document,
        return_metadata=True
    )
    if not contexts:
        return "No relevant passages found."
    
    # Format with citations
    return _format_context_chunks(contexts[:limit])
```

**Context Formatting**:
```
[1] (chapter1.pdf) The mitochondria is the powerhouse of the cell...
[2] (chapter1.pdf) Cellular respiration occurs in three stages...
[3] (biology_notes.pdf) ATP synthesis involves...
```

**Agent Use Case**: 
- "What does chapter 3 say about X?"
- "Search my notes for Y"

---

### 3. `summarize_text`

**Purpose**: Condense retrieved passages into bullet points

**Schema**:
- **Input**: 
  - `text` (str, required): Text to summarize
  - `max_points` (int, default=5): Number of bullets
- **Output**: Bulleted summary

**Implementation**:
```python
def summarize_text(text: str, max_points: int = 5) -> str:
    if not text.strip():
        return "Nothing to summarize."
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Return concise bullet points (start with •)."),
        ("user", "Limit to {max_points} bullets. Text:\n{text}")
    ])
    
    chain = prompt | summarizer_llm | StrOutputParser()
    return chain.invoke({"text": text, "max_points": max_points})
```

**Agent Use Case**: After retrieving context, condense it for user

---

### 4. `summarize_last_answer`

**Purpose**: Recall and summarize the agent's most recent response

**Schema**:
- **Input**: `max_points` (int, default=5)
- **Output**: Bulleted summary of previous answer

**Why This Tool Exists**:
Enables natural follow-ups without re-retrieving context:
```
User: "Tell me about photosynthesis"
Agent: [Searches docs, provides detailed answer]

User: "Summarize that in 3 points"
Agent: [Calls summarize_last_answer instead of re-searching]
```

**Implementation**:
```python
def summarize_last_answer(max_points: int = 5) -> str:
    # get_last_answer is injected via closure
    last = get_last_answer()
    if not last:
        return "No previous answer to summarize."
    return _run_summarizer(last, max_points)
```

---

## RAG Pipeline

**RAG** = Retrieval-Augmented Generation: Combine document retrieval with LLM generation.

### Pipeline Stages

```
┌─────────────────────────────────────────────────────────────┐
│                    1. Document Ingestion                     │
├─────────────────────────────────────────────────────────────┤
│ PDF Upload → Text Extraction (PyPDF2) → Chunking (2000 chars│
│ with 500 char overlap) → SHA-256 Deduplication              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    2. Embedding Generation                   │
├─────────────────────────────────────────────────────────────┤
│ For each chunk → OpenAI text-embedding-ada-002               │
│ → 1536-dimensional vector                                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    3. Vector Storage                         │
├─────────────────────────────────────────────────────────────┤
│ Store in Pinecone with metadata:                             │
│   • text: original chunk                                     │
│   • filename: source document                                │
│   • document_hash: SHA-256 for dedup                         │
│   • user_id: for namespace isolation                         │
│   • chunk_index: position in document                        │
│   • timestamp: upload time                                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    4. Query Processing                       │
├─────────────────────────────────────────────────────────────┤
│ User query → Embed with ada-002 → Cosine similarity search  │
│ in user's namespace → Return top-k chunks (k=10-25)         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    5. Agent Processing                       │
├─────────────────────────────────────────────────────────────┤
│ Agent receives formatted context → Reasons about answer →    │
│ May call summarize_text → Generates response with citations │
└─────────────────────────────────────────────────────────────┘
```

### Document Processing Details

**File**: `src/core/document_processor.py`

#### Chunking Strategy

```python
chunk_size = 2000      # Large enough for complete paragraphs
overlap = 500          # Prevent splitting mid-concept

for i in range(0, len(text), chunk_size - overlap):
    chunk = text[i:i + chunk_size]
    if chunk.strip():
        chunks.append(chunk)
```

**Why Overlap?** Ensures continuity across chunk boundaries. A concept mentioned at the end of chunk N is still present at the start of chunk N+1.

#### Deduplication

```python
def _calculate_document_hash(self, file_content: bytes) -> str:
    return hashlib.sha256(file_content).hexdigest()

def _check_document_exists(self, doc_hash: str) -> bool:
    results = index.query(
        vector=[0.0] * 1536,  # Dummy vector
        filter={"document_hash": doc_hash, "user_id": self.user_id},
        top_k=1
    )
    return len(results.matches) > 0
```

Before processing, check if document with same hash exists. Prevents duplicate uploads.

#### Retrieval Optimization

```python
def get_context(self, question: str, specific_document: str = None):
    # 1. Generate query embedding
    question_embedding = self._get_embedding(question)
    
    # 2. Build user-specific filter
    filter_dict = {"user_id": self.user_id}
    if specific_document:
        filter_dict["filename"] = specific_document
    
    # 3. Semantic search
    results = index.query(
        vector=question_embedding,
        top_k=200,  # Over-retrieve, then re-rank
        filter=filter_dict,
        namespace=str(self.user_id),
        score_threshold=0.6  # Minimum similarity
    )
    
    # 4. Sort by relevance, deduplicate
    return process_and_format(results)
```

**Top-k Strategy**: Retrieve 200 candidates, then re-rank and deduplicate to top 10-25. Ensures diverse context.

---

## Multi-User Architecture

### Isolation Strategy

**Three-Layer Isolation**:

1. **Pinecone Namespace**: Each user gets a dedicated namespace
   ```python
   namespace = str(user_id)  # e.g., "42"
   index.query(..., namespace=namespace)
   ```

2. **Metadata Filtering**: Additional filter on `user_id` in metadata
   ```python
   filter = {"user_id": user_id}
   ```

3. **Database-Level**: User authentication enforced at DB layer

### User-Scoped Indexes

```python
# Each user gets their own Pinecone index
index_name = f"edu-assistant-user-{user_id}"

# Ensures complete data separation
# Downside: Scales cost linearly with users
# Alternative: Shared index with strict namespace filtering
```

**Trade-off**: 
- **Dedicated indexes** = Better isolation, higher cost
- **Shared index + namespaces** = Lower cost, requires careful filtering

Current implementation uses **dedicated indexes** for maximum security.

### API Key Management

**File**: `src/auth/user_settings.py`

User's API keys (OpenAI, Pinecone, ElevenLabs) are:
1. **Encrypted** at rest using Fernet (AES-256)
2. **Stored** in PostgreSQL user_settings table
3. **Decrypted** on-demand when initializing agent

```python
from cryptography.fernet import Fernet

def encrypt_key(key: str, encryption_key: bytes) -> str:
    f = Fernet(encryption_key)
    return f.encrypt(key.encode()).decode()

def decrypt_key(encrypted: str, encryption_key: bytes) -> str:
    f = Fernet(encryption_key)
    return f.decrypt(encrypted.encode()).decode()
```

**Master Key**: `APP_ENCRYPTION_KEY` environment variable (32-byte base64). **Never commit this to version control.**

---

## Data Flow

### End-to-End Query Flow

```
1. USER SUBMITS QUERY
   └─> Streamlit UI (app.py)

2. AUTHENTICATE & LOAD CONTEXT
   └─> auth_manager.get_current_user()
   └─> user_settings.get_api_keys(user_id)
   └─> Decrypt API keys

3. INITIALIZE AGENT
   └─> DocumentProcessor(user_id, api_keys)
       └─> Initialize Pinecone with user namespace
   └─> AgentResponder(processor, api_key)
       └─> Build tools with processor reference
       └─> Load conversation memory from session

4. AGENT REASONING LOOP
   └─> Agent receives: {input: query, chat_history: [...]}
   
   ITERATION 1:
   └─> Agent decision: "Need context, call search_documents"
   └─> Tool execution: search_documents(query)
       └─> DocumentProcessor.get_context(query)
           └─> Embed query with OpenAI
           └─> Pinecone.query(vector, namespace=user_id)
           └─> Return top 10 chunks with metadata
   └─> Agent receives: "[1] (doc.pdf) Text... [2] (doc.pdf) Text..."
   
   ITERATION 2:
   └─> Agent decision: "Context retrieved, now answer user"
   └─> Agent outputs: Final answer with citations
   
5. RESPONSE GENERATION
   └─> Format response with markdown
   └─> Optional: Generate TTS audio
   └─> Update conversation memory
   └─> Log interaction (audit.py)

6. DISPLAY TO USER
   └─> Streamlit renders response
   └─> User can rate response (feedback_manager)
```

### Document Upload Flow

```
1. USER UPLOADS PDF
   └─> Streamlit file_uploader widget

2. HASH & DEDUPLICATE
   └─> Calculate SHA-256 of file content
   └─> Check if hash exists for this user
   └─> If exists: Return "already_exists"

3. EXTRACT TEXT
   └─> PyPDF2.PdfReader(file)
   └─> Extract text from each page
   └─> Split into overlapping chunks

4. GENERATE EMBEDDINGS
   └─> For each chunk:
       └─> OpenAI embedding API (ada-002)
       └─> Get 1536-dim vector

5. STORE IN PINECONE
   └─> Batch upsert (10 chunks at a time)
   └─> Metadata: text, filename, user_id, chunk_index
   └─> Namespace: str(user_id)

6. STORE METADATA IN DB
   └─> database.save_document(user_id, filename, hash)
   └─> Links document to user account

7. OPTIONAL: ENCRYPT & UPLOAD TO S3
   └─> Encrypt PDF with AES-256
   └─> Upload to S3 with SSE
   └─> Store S3 key in metadata

8. LOG & CONFIRM
   └─> audit.log_action(user_id, "upload_document", filename)
   └─> Return success to UI
```

---

## Security Model

### Threat Model

**Assumptions**:
- User's machine may be compromised (protect API keys)
- Database may be breached (encrypt sensitive data)
- Multiple users should not see each other's data (isolation)

### Security Measures

#### 1. **Encryption at Rest**

**User API Keys**:
- Stored encrypted in `user_settings` table
- Decrypted only in memory during session
- Master key (`APP_ENCRYPTION_KEY`) must be secured

**PDF Storage (Optional S3)**:
- PDFs encrypted before upload with AES-256
- S3 server-side encryption (SSE) as additional layer
- Only authorized users can decrypt

#### 2. **Data Isolation**

**Pinecone**:
- Dedicated namespaces per user
- Metadata filters on `user_id`
- No cross-user queries possible

**PostgreSQL**:
- Foreign key constraints: `documents.user_id → users.id`
- Queries always filtered by authenticated user's ID

#### 3. **Access Control**

**Authentication**:
- Password hashing (bcrypt or similar)
- Session management via Streamlit session state
- No JWT/token auth (single-page app model)

**Authorization**:
- Users can only access their own documents
- Admin users (via `ADMIN_USERS` env) can view audit logs
- No privilege escalation paths

#### 4. **Audit Logging**

**File**: `src/utils/audit.py`

```python
def log_action(user_id: int, action: str, details: str = None):
    db.execute(
        "INSERT INTO audit_logs (user_id, action, details, timestamp) "
        "VALUES (?, ?, ?, ?)",
        (user_id, action, details, datetime.now())
    )
```

**Logged Actions**:
- `upload_document`
- `delete_document`
- `login`
- `logout`
- API key changes

**Admin View**: `src/ui/admin_audit.py` displays logs for compliance.

#### 5. **Input Validation**

- PDF file type validation before processing
- SQL injection prevention via parameterized queries
- API key format validation before storage

---

## Scalability Considerations

### Current Limitations

1. **Per-User Indexes**: Scales cost linearly (each user = new Pinecone index)
2. **Synchronous Processing**: Document upload blocks UI
3. **In-Memory Sessions**: Requires sticky sessions in load balancer

### Scaling Strategies

#### Short-Term (10-100 users)

**Current architecture is sufficient.**

- Streamlit Cloud automatic scaling
- Pinecone serverless handles query load
- PostgreSQL connection pooling (via PgBouncer if needed)

#### Medium-Term (100-1000 users)

**Optimization Needed**:

1. **Shared Pinecone Index**:
   ```python
   index_name = "edu-assistant-shared"
   # Use namespace per user instead of per-user index
   namespace = f"user_{user_id}"
   ```
   **Benefit**: Reduces index costs from O(n) to O(1)

2. **Async Document Processing**:
   ```python
   # Use Celery or AWS Lambda
   @celery.task
   def process_document_async(user_id, file_path):
       # Background processing
   ```
   **Benefit**: UI remains responsive during upload

3. **Redis for Sessions**:
   ```python
   # Replace Streamlit session_state
   session = Redis.get(session_id)
   ```
   **Benefit**: Stateless app servers, easier horizontal scaling

#### Long-Term (1000+ users)

**Architecture Changes**:

1. **Microservices**:
   - **API Gateway** (FastAPI/Flask)
   - **Agent Service** (stateless workers)
   - **Ingestion Service** (async queue)
   - **Auth Service** (OAuth2)

2. **Caching Layer**:
   ```python
   # Cache frequently accessed embeddings
   @cache(ttl=3600)
   def get_embedding(text: str) -> List[float]:
       return openai.embed(text)
   ```

3. **CDN for Static Assets**:
   - Serve UI from CDN (if detached from Streamlit)

4. **Multi-Region Deployment**:
   - Pinecone in multiple regions
   - PostgreSQL read replicas

---

## Future Enhancements

### Planned Features

1. **Multi-Modal Support**:
   - Image OCR (for scanned docs)
   - Video transcription (for lecture recordings)

2. **Advanced RAG**:
   - **Hypothetical Document Embeddings (HyDE)**: Generate hypothetical answer, then search
   - **Query Decomposition**: Break complex queries into sub-questions
   - **Re-ranking**: Use cross-encoder for better relevance

3. **Agent Capabilities**:
   - **Web Search Tool**: Supplement documents with live search
   - **Calculation Tool**: Handle math/stats questions
   - **Citation Verification**: Check if citations are accurate

4. **Collaborative Features**:
   - Share documents with other users
   - Group workspaces
   - Collaborative annotations

### Research Directions

- **Fine-Tuning**: Train custom embeddings on educational content
- **Active Learning**: Use feedback to improve retrieval
- **Explainability**: Why did agent choose specific tools?

---

## Conclusion

This architecture demonstrates modern AI engineering patterns:

✅ **Agentic Design**: Autonomous tool selection vs. fixed pipelines  
✅ **RAG Implementation**: Practical retrieval-augmented generation  
✅ **Production-Ready**: Multi-user, secure, scalable foundation  
✅ **Extensible**: New tools/features can be added modularly  

The system balances **sophistication** (agentic reasoning) with **pragmatism** (proven tools like LangChain, Pinecone). It's designed for a real-world use case while showcasing advanced AI patterns.

---

**For questions or deeper technical discussions, see:**
- [Main README](../README.md)
- [Usage Guide](USAGE.md)
- [Source Code](../src/)
