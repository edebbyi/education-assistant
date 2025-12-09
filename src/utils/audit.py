import os
from typing import Optional

from src.database.database import Database


def log_action(user_id: Optional[int], action: str, metadata: str = "") -> None:
    """Best-effort audit logging."""
    try:
        db = Database()
        db.initialize()
        db.execute(
            "INSERT INTO audit_logs (user_id, action, metadata) VALUES (?, ?, ?)",
            (user_id, action, metadata),
        )
    except Exception:
        # Non-blocking
        pass


def is_admin(user: dict) -> bool:
    admins = os.environ.get("ADMIN_USERS", "")
    admin_list = [a.strip().lower() for a in admins.split(",") if a.strip()]
    if not user:
        return False
    username = str(user.get("username", "")).lower()
    email = str(user.get("email", "")).lower()
    return username in admin_list or email in admin_list
