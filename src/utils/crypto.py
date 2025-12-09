import base64
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


def _get_cipher() -> Fernet:
    """Return a Fernet cipher from APP_ENCRYPTION_KEY (base64 urlsafe 32 bytes)."""
    key = os.environ.get("APP_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("APP_ENCRYPTION_KEY is not set")
    # Allow raw 32-byte key or already base64-encoded key
    try:
        if len(key) == 32:
            key = base64.urlsafe_b64encode(key.encode())
        return Fernet(key)
    except Exception as exc:
        raise RuntimeError("Invalid APP_ENCRYPTION_KEY format") from exc


def encrypt_str(value: Optional[str]) -> Optional[str]:
    """Encrypt a string; returns None if input is falsy."""
    if not value:
        return None
    cipher = _get_cipher()
    return cipher.encrypt(value.encode()).decode()


def decrypt_str(value: Optional[str]) -> Optional[str]:
    """Decrypt a string; returns None if input is falsy."""
    if not value:
        return None
    cipher = _get_cipher()
    try:
        return cipher.decrypt(value.encode()).decode()
    except InvalidToken:
        raise RuntimeError("Failed to decrypt value; check APP_ENCRYPTION_KEY")
