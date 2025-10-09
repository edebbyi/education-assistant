import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

class Database:
    def __init__(self, db_path: str = None):
        # Use default data directory for persistent storage
        if not db_path:
            # Create .data directory if it doesn't exist
            os.makedirs('.data', exist_ok=True)
            db_path = '.data/feedback.db'
        self.db_path = db_path

    def initialize(self) -> None:
        """Initialize database and create tables if they don't exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create feedback table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        user_query TEXT NOT NULL,
                        ai_response TEXT NOT NULL,
                        feedback_category TEXT CHECK(
                            feedback_category IN ('Helpful', 'Not Quite Right', 'Suggest an Improvement')
                        ),
                        rating INTEGER CHECK(rating BETWEEN 1 AND 5),
                        feedback_text TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)

                # Create chat_history table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        is_user BOOLEAN NOT NULL,
                        content TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)

                # Create documents table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        filename TEXT NOT NULL,
                        document_hash TEXT NOT NULL,
                        upload_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        UNIQUE(user_id, document_hash)
                    )
                """)

                conn.commit()

        except Exception as e:
            raise Exception(f"Error initializing database: {str(e)}")

    def execute(self, query: str, params: tuple = ()) -> None:
        """Execute SQL query"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
        except Exception as e:
            raise Exception(f"Error executing query: {str(e)}")

    def query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute query and return results"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            raise Exception(f"Error querying database: {str(e)}")

    def save_chat_message(self, user_id: int, is_user: bool, content: str) -> None:
        """Save a chat message to the database"""
        query = """
        INSERT INTO chat_history (user_id, is_user, content)
        VALUES (?, ?, ?)
        """
        self.execute(query, (user_id, is_user, content))

    def get_chat_history(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve chat history for a user"""
        query = """
        SELECT * FROM chat_history 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
        """
        return self.query(query, (user_id, limit))

    def save_document(self, user_id: int, filename: str, document_hash: str, metadata: str = None) -> None:
        """Save document metadata to the database"""
        query = """
        INSERT INTO documents (user_id, filename, document_hash, metadata)
        VALUES (?, ?, ?, ?)
        """
        self.execute(query, (user_id, filename, document_hash, metadata))

    def get_document_by_hash(self, user_id: int, document_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve document by its hash for a specific user"""
        query = """
        SELECT * FROM documents WHERE user_id = ? AND document_hash = ?
        """
        results = self.query(query, (user_id, document_hash))
        return results[0] if results else None
    
    def get_user_documents(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all documents for a specific user"""
        query = """
        SELECT * FROM documents WHERE user_id = ? ORDER BY upload_timestamp DESC
        """
        return self.query(query, (user_id,))
