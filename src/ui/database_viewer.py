import sqlite3
from typing import List, Dict, Any
import pandas as pd
import streamlit as st
import os

def get_database_connection():
    """Create a connection to the SQLite database in persistent storage"""
    db_path = '.data/feedback.db'
    return sqlite3.connect(db_path)

def view_feedback_data():
    """Display feedback data in a Streamlit interface"""
    st.title("📊 Feedback Data Analysis")
    
    # Check if user is authenticated
    if not st.session_state.get('authenticated', False):
        st.error("Please log in to view your feedback data")
        return
    
    user_id = st.session_state.user['id']
    username = st.session_state.user['username']
    
    st.markdown(f"**Viewing feedback for:** {username}")

    conn = get_database_connection()

    # Overall statistics - USER SPECIFIC
    st.header("Your Feedback Statistics")
    stats_query = """
    SELECT 
        COUNT(*) as total_feedback,
        ROUND(AVG(rating), 2) as avg_rating,
        COUNT(CASE WHEN feedback_category = 'Helpful' THEN 1 END) as helpful_count,
        COUNT(CASE WHEN feedback_category = 'Not Quite Right' THEN 1 END) as not_right_count,
        COUNT(CASE WHEN feedback_category = 'Suggest an Improvement' THEN 1 END) as improvement_count
    FROM feedback
    WHERE user_id = ?
    """
    stats = pd.read_sql_query(stats_query, conn, params=(user_id,))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Feedback", stats['total_feedback'].iloc[0])
    with col2:
        st.metric("Average Rating", stats['avg_rating'].iloc[0])
    with col3:
        st.metric("Helpful Responses", stats['helpful_count'].iloc[0])

    # Raw data view - USER SPECIFIC
    st.header("Your Feedback History")
    query = """
    SELECT 
        id,
        user_query,
        ai_response,
        feedback_category,
        rating,
        feedback_text,
        timestamp
    FROM feedback
    WHERE user_id = ?
    ORDER BY timestamp DESC
    """
    df = pd.read_sql_query(query, conn, params=(user_id,))

    # Show message if no feedback
    if len(df) == 0:
        st.info("📝 You haven't provided any feedback yet. Try chatting with your documents and rating the responses!")
    else:
        st.dataframe(df)
    
    # Export option - only for user's own data
    if len(df) > 0 and st.button("Export My Feedback to CSV"):
        # Save to persistent storage with user-specific filename
        export_path = f'.data/feedback_export_user_{user_id}.csv'
        df.to_csv(export_path, index=False)
        st.success(f"Your feedback data exported to {export_path}!")

    conn.close()

if __name__ == "__main__":
    view_feedback_data()