import os
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime
from typing import Optional, List, Dict, Any

class DatabaseManager:
    def __init__(self):
        self.conn_params = {
            'dbname': os.environ.get('PGDATABASE'),
            'user': os.environ.get('PGUSER'),
            'password': os.environ.get('PGPASSWORD'),
            'host': os.environ.get('PGHOST'),
            'port': os.environ.get('PGPORT')
        }

    def get_connection(self):
        """Create a new database connection"""
        return psycopg2.connect(**self.conn_params)

    def add_document(self, filename: str, document_hash: str, chunk_count: int) -> int:
        """Add a new document to the database"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents (filename, document_hash, chunk_count)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (filename, document_hash, chunk_count)
                )
                return cur.fetchone()[0]

    def log_question(self, question_text: str) -> int:
        """Log a user question"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_questions (question_text)
                    VALUES (%s)
                    RETURNING id
                    """,
                    (question_text,)
                )
                return cur.fetchone()[0]

    def store_response(self, question_id: int, response_text: str, sources_used: List[str]) -> int:
        """Store an AI response"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ai_responses (question_id, response_text, sources_used)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (question_id, response_text, sources_used)
                )
                return cur.fetchone()[0]

    def save_feedback(self, response_id: int, rating: int, category: str, feedback_text: Optional[str] = None):
        """Save user feedback"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_feedback (response_id, rating, feedback_category, feedback_text)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (response_id, rating, category, feedback_text)
                )

    def get_document_stats(self) -> List[Dict[str, Any]]:
        """Get statistics about stored documents"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    """
                    SELECT 
                        filename,
                        upload_timestamp,
                        chunk_count,
                        is_active
                    FROM documents
                    ORDER BY upload_timestamp DESC
                    """
                )
                return [dict(row) for row in cur.fetchall()]

    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get feedback statistics"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    """
                    SELECT 
                        COUNT(*) as total_feedback,
                        AVG(rating) as average_rating,
                        COUNT(CASE WHEN rating >= 4 THEN 1 END) as positive_feedback,
                        COUNT(CASE WHEN rating <= 2 THEN 1 END) as negative_feedback
                    FROM user_feedback
                    """
                )
                stats = dict(cur.fetchone())
                
                # Get feedback categories distribution
                cur.execute(
                    """
                    SELECT 
                        feedback_category,
                        COUNT(*) as count
                    FROM user_feedback
                    GROUP BY feedback_category
                    """
                )
                stats['categories'] = {row['feedback_category']: row['count'] for row in cur.fetchall()}
                
                return stats
