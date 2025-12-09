import hashlib
import os
import re
import secrets
from typing import Any, Dict, Optional

import streamlit as st

from ..database.database import Database
from ..utils.audit import log_action
from ..utils.crypto import decrypt_str, encrypt_str

class AuthManager:
    def __init__(self):
        self.db = Database()
        self.db.initialize()
        self._create_auth_tables()
        self._migrate_emails_to_encrypted()
    
    def _create_auth_tables(self):
        """Create authentication-related tables"""
        try:
            if self.db.use_postgres:
                users_ddl = """
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        email_hash TEXT,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        is_active BOOLEAN DEFAULT TRUE
                    )
                """
                api_keys_ddl = """
                    CREATE TABLE IF NOT EXISTS user_api_keys (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        openai_key TEXT,
                        pinecone_key TEXT,
                        pinecone_environment TEXT,
                        elevenlabs_key TEXT,
                        updated_at TIMESTAMPTZ DEFAULT NOW(),
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """
                sessions_ddl = """
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        session_token TEXT UNIQUE NOT NULL,
                        expires_at TIMESTAMPTZ NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """
                audit_ddl = """
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        action TEXT NOT NULL,
                        metadata TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """
            else:
                users_ddl = """
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        email_hash TEXT,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                """
                api_keys_ddl = """
                    CREATE TABLE IF NOT EXISTS user_api_keys (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        openai_key TEXT,
                        pinecone_key TEXT,
                        pinecone_environment TEXT,
                        elevenlabs_key TEXT,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """
                sessions_ddl = """
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        session_token TEXT UNIQUE NOT NULL,
                        expires_at DATETIME NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """
                audit_ddl = """
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        action TEXT NOT NULL,
                        metadata TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """

            # Create tables
            self.db.execute(users_ddl)
            self._ensure_email_hash_column()
            self.db.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_email_hash_idx ON users(email_hash)")
            self.db.execute(api_keys_ddl)
            self.db.execute(sessions_ddl)
            self.db.execute(audit_ddl)
            
        except Exception as e:
            st.error(f"Error creating auth tables: {str(e)}")
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt"""
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

    def _generate_salt(self) -> str:
        """Generate random salt"""
        return secrets.token_hex(16)

    def _normalize_email(self, email: str) -> str:
        return email.strip().lower()

    def _email_hash(self, email: str) -> str:
        return hashlib.sha256(self._normalize_email(email).encode()).hexdigest()


    def _ensure_email_hash_column(self):
        """Ensure email_hash column exists; best-effort."""
        try:
            self.db.execute("ALTER TABLE users ADD COLUMN email_hash TEXT")
        except Exception:
            pass

    def _migrate_emails_to_encrypted(self):
        """Encrypt plaintext emails and populate email_hash where missing."""
        if not os.environ.get("APP_ENCRYPTION_KEY"):
            return
        try:
            rows = self.db.query("SELECT id, email, email_hash FROM users")
        except Exception:
            return
        for row in rows:
            user_id = row.get("id")
            email_val = row.get("email")
            email_hash = row.get("email_hash")
            if not email_val:
                continue
            plain_email = None
            if "@" in email_val:
                plain_email = email_val
            else:
                try:
                    plain_email = decrypt_str(email_val)
                except Exception:
                    continue
            if not plain_email:
                continue
            new_hash = self._email_hash(plain_email)
            if email_hash == new_hash and "@" not in email_val:
                continue
            try:
                encrypted_email = encrypt_str(plain_email)
                self.db.execute(
                    "UPDATE users SET email = ?, email_hash = ? WHERE id = ?",
                    (encrypted_email, new_hash, user_id)
                )
            except Exception:
                continue

    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _validate_password(self, password: str) -> tuple[bool, str]:
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        return True, "Password is valid"
    
    def register_user(self, username: str, email: str, password: str) -> tuple[bool, str]:
        """Register a new user"""
        try:
            if not username or len(username) < 3:
                return False, "Username must be at least 3 characters long"

            if not self._validate_email(email):
                return False, "Invalid email format"

            is_valid_password, password_message = self._validate_password(password)
            if not is_valid_password:
                return False, password_message

            normalized_email = self._normalize_email(email)
            email_hash = self._email_hash(email)
            encrypted_email = encrypt_str(email)

            # Check if user already exists
            existing_user = self.db.query(
                "SELECT id FROM users WHERE username = ? OR email_hash = ?",
                (username, email_hash)
            )
            if existing_user:
                return False, "Username or email already exists"
            
            # Create user
            salt = self._generate_salt()
            password_hash = self._hash_password(password, salt)
            
            self.db.execute(
                "INSERT INTO users (username, email, email_hash, password_hash, salt) VALUES (?, ?, ?, ?, ?)",
                (username, encrypted_email, email_hash, password_hash, salt)
            )
            
            log_action(None, "register", f"username={username}")
            return True, "User registered successfully"
            
        except Exception as e:
            return False, f"Registration failed: {str(e)}"
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and return user info"""
        try:
            active_clause = "COALESCE(is_active, TRUE) = TRUE" if self.db.use_postgres else "COALESCE(is_active, 1) = 1"
            user_data = self.db.query(
                f"SELECT id, username, email, password_hash, salt FROM users WHERE username = ? AND {active_clause}",
                (username,)
            )
            
            if not user_data:
                log_action(None, "login_failure", f"username={username}")
                return None
            
            user = user_data[0]
            password_hash = self._hash_password(password, user['salt'])
            
            if password_hash == user['password_hash']:
                try:
                    decrypted_email = decrypt_str(user['email'])
                except Exception:
                    decrypted_email = None
                log_action(user['id'], "login_success", f"username={username}")
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'email': decrypted_email
                }
            
            log_action(user.get('id'), "login_failure", f"username={username}")
            return None
            
        except Exception as e:
            st.error(f"Authentication error: {str(e)}")
            return None
    
    def get_user_api_keys(self, user_id: int) -> Dict[str, Optional[str]]:
        """Get user's API keys"""
        try:
            keys_data = self.db.query(
                "SELECT openai_key, pinecone_key, pinecone_environment, elevenlabs_key FROM user_api_keys WHERE user_id = ?",
                (user_id,)
            )
            
            if keys_data:
                keys = keys_data[0]
                return {
                    'openai_key': decrypt_str(keys.get('openai_key')),
                    'pinecone_key': decrypt_str(keys.get('pinecone_key')),
                    'pinecone_environment': keys.get('pinecone_environment'),  # Deprecated but kept for backward compatibility
                    'elevenlabs_key': decrypt_str(keys.get('elevenlabs_key'))
                }
            
            return {
                'openai_key': None,
                'pinecone_key': None,
                'pinecone_environment': None,  # Deprecated but kept for backward compatibility
                'elevenlabs_key': None
            }
            
        except Exception as e:
            st.error(f"Error fetching API keys: {str(e)}")
            return {}
    
    def save_user_api_keys(self, user_id: int, openai_key: str = None, 
                          pinecone_key: str = None, pinecone_environment: str = None,
                          elevenlabs_key: str = None) -> bool:
        """Save user's API keys
        
        Note: pinecone_environment is deprecated and no longer used by Pinecone SDK,
        but kept for backward compatibility.
        """
        try:
            # Check if keys already exist
            existing = self.db.query(
                "SELECT id FROM user_api_keys WHERE user_id = ?",
                (user_id,)
            )
            
            if existing:
                # Update existing keys (ignoring pinecone_environment as it's deprecated)
                self.db.execute("""
                    UPDATE user_api_keys 
                    SET openai_key = ?, pinecone_key = ?, pinecone_environment = ?, 
                        elevenlabs_key = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (
                    encrypt_str(openai_key),
                    encrypt_str(pinecone_key),
                    pinecone_environment,
                    encrypt_str(elevenlabs_key),
                    user_id
                ))
            else:
                # Insert new keys (ignoring pinecone_environment as it's deprecated)
                self.db.execute("""
                    INSERT INTO user_api_keys (user_id, openai_key, pinecone_key, pinecone_environment, elevenlabs_key)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user_id,
                    encrypt_str(openai_key),
                    encrypt_str(pinecone_key),
                    pinecone_environment,
                    encrypt_str(elevenlabs_key)
                ))
            
            return True
            
        except Exception as e:
            st.error(f"Error saving API keys: {str(e)}")
            return False
