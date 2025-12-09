from .database import Database
from datetime import datetime

class FeedbackManager:
    def __init__(self):
        self.db = Database()
        self.db.initialize()

    def save_feedback(self, user_id: int, user_question: str, ai_response: str, feedback_category: str, rating: int, feedback_text: str = None) -> None:
        """Save user feedback to database"""
        try:
            self.db.execute(
                """
                INSERT INTO feedback (
                    user_id,
                    user_query,
                    ai_response,
                    feedback_category,
                    rating,
                    feedback_text
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, user_question, ai_response, feedback_category, rating, feedback_text)
            )
        except Exception as e:
            raise Exception(f"Error saving feedback: {str(e)}")

    def get_feedback_stats(self, user_id: int = None):
        """Get feedback statistics for a specific user or all users"""
        try:
            if user_id:
                return self.db.query(
                    """
                    SELECT 
                        AVG(rating) as avg_rating,
                        COUNT(*) as total_feedback,
                        COUNT(CASE WHEN feedback_category = 'Helpful' THEN 1 END) as helpful_count,
                        COUNT(CASE WHEN feedback_category = 'Not Quite Right' THEN 1 END) as not_right_count,
                        COUNT(CASE WHEN feedback_category = 'Suggest an Improvement' THEN 1 END) as improvement_count
                    FROM feedback WHERE user_id = ?
                    """,
                    (user_id,)
                )
            else:
                return self.db.query(
                    """
                    SELECT 
                        AVG(rating) as avg_rating,
                        COUNT(*) as total_feedback,
                        COUNT(CASE WHEN feedback_category = 'Helpful' THEN 1 END) as helpful_count,
                        COUNT(CASE WHEN feedback_category = 'Not Quite Right' THEN 1 END) as not_right_count,
                        COUNT(CASE WHEN feedback_category = 'Suggest an Improvement' THEN 1 END) as improvement_count
                    FROM feedback
                    """
                )
        except Exception as e:
            raise Exception(f"Error getting feedback stats: {str(e)}")
