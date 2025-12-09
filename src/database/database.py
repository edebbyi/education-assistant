import os
import sqlite3
import socket
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import DictCursor

class Database:
    def __init__(self, db_path: str = None):
        # Prefer Postgres when PG* env vars are set; otherwise fall back to local SQLite.
        self.postgres_available = all(
            os.environ.get(env)
            for env in ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD")
        )
        self.use_postgres = False  # Will be set to True if connection succeeds
        
        if self.postgres_available:
            # Resolve hostname to IPv4 address to avoid IPv6 issues
            host = os.environ.get("PGHOST")
            hostaddr = None
            
            try:
                # Force IPv4 resolution - get the IPv4 address
                ipv4_addr = socket.getaddrinfo(host, None, socket.AF_INET)[0][4][0]
                hostaddr = ipv4_addr
            except (socket.gaierror, IndexError):
                # If resolution fails, hostaddr will be None
                pass
            
            self.conn_params = {
                "dbname": os.environ.get("PGDATABASE"),
                "user": os.environ.get("PGUSER"),
                "password": os.environ.get("PGPASSWORD"),
                "host": host,  # Keep hostname for SSL cert validation
                "port": os.environ.get("PGPORT"),
                "sslmode": os.environ.get("PGSSLMODE", "require"),
                "connect_timeout": 10,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            }
            
            # If we successfully resolved IPv4, use hostaddr to force it
            if hostaddr:
                self.conn_params["hostaddr"] = hostaddr
        
        # Always set up SQLite as fallback
        if not db_path:
            os.makedirs('.data', exist_ok=True)
            db_path = '.data/feedback.db'
        self.db_path = db_path

    def initialize(self) -> None:
        """Initialize database and create tables if they don't exist"""
        # Try PostgreSQL first if credentials are available
        if self.postgres_available:
            try:
                with psycopg2.connect(**self.conn_params) as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS feedback (
                                id SERIAL PRIMARY KEY,
                                user_id INTEGER,
                                user_query TEXT NOT NULL,
                                ai_response TEXT NOT NULL,
                                feedback_category TEXT CHECK(
                                    feedback_category IN ('Helpful', 'Not Quite Right', 'Suggest an Improvement')
                                ),
                                rating INTEGER CHECK(rating BETWEEN 1 AND 5),
                                feedback_text TEXT,
                                timestamp TIMESTAMPTZ DEFAULT NOW()
                            )
                        """)
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS chat_history (
                                id SERIAL PRIMARY KEY,
                                user_id INTEGER,
                                is_user BOOLEAN NOT NULL,
                                content TEXT NOT NULL,
                                timestamp TIMESTAMPTZ DEFAULT NOW()
                            )
                        """)
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS audit_logs (
                                id SERIAL PRIMARY KEY,
                                user_id INTEGER,
                                action TEXT NOT NULL,
                                metadata TEXT,
                                created_at TIMESTAMPTZ DEFAULT NOW()
                            )
                        """)
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS documents (
                                id SERIAL PRIMARY KEY,
                                user_id INTEGER,
                                filename TEXT NOT NULL,
                                document_hash TEXT NOT NULL,
                                upload_timestamp TIMESTAMPTZ DEFAULT NOW(),
                                metadata TEXT,
                                UNIQUE(user_id, document_hash)
                            )
                        """)
                        conn.commit()
                self.use_postgres = True
                print("✓ Connected to PostgreSQL database")
                return
            except Exception as e:
                # Do not silently fall back when Postgres is configured
                raise Exception(f"PostgreSQL connection failed: {str(e)}")
        
        # Fall back to SQLite
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
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
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        action TEXT NOT NULL,
                        metadata TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
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
            self.use_postgres = False
            print(f"✓ Connected to SQLite database: {self.db_path}")
        except Exception as e:
            raise Exception(f"Error initializing database: {str(e)}")

    def execute(self, query: str, params: tuple = ()) -> None:
        """Execute SQL query"""
        try:
            if self.use_postgres:
                with psycopg2.connect(**self.conn_params) as conn:
                    with conn.cursor() as cur:
                        cur.execute(self._format_query(query), params)
                        conn.commit()
            else:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    conn.commit()
        except Exception as e:
            raise Exception(f"Error executing query: {str(e)}")

    def query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute query and return results"""
        try:
            if self.use_postgres:
                with psycopg2.connect(**self.conn_params) as conn:
                    with conn.cursor(cursor_factory=DictCursor) as cur:
                        cur.execute(self._format_query(query), params)
                        return [dict(row) for row in cur.fetchall()]
            else:
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

    def _format_query(self, query: str) -> str:
        """Convert SQLite-style '?' placeholders to '%s' for psycopg2."""
        if not self.use_postgres:
            return query
        return query.replace("?", "%s")
