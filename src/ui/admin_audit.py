import streamlit as st

from src.utils.audit import is_admin
from src.database.database import Database


def view_audit_logs():
    user = st.session_state.get("user")
    if not user or not is_admin(user):
        st.error("Access denied.")
        return

    st.subheader("Audit Logs")
    limit = st.number_input("Rows", min_value=10, max_value=500, value=100, step=10)

    db = Database()
    db.initialize()
    rows = db.query(
        """
        SELECT id, user_id, action, metadata, created_at
        FROM audit_logs
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    if not rows:
        st.info("No audit events recorded yet.")
        return

    st.dataframe(rows, hide_index=True)
