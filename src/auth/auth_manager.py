import streamlit as st
import hashlib
import secrets
from ..database.database import Database
from typing import Optional, Dict, Any
import re

class AuthManager:
    def __init__(self):
        self.db = Database()
        self.db.initialize()
        self._create_auth_tables()
    
    def _create_auth_tables(self):
        """Create authentication-related tables"""
        try:
            # Create users table
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Create user_api_keys table for secure key storage
            self.db.execute("""
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
            """)
            
            # Create user_sessions table
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    expires_at DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
        except Exception as e:
            st.error(f"Error creating auth tables: {str(e)}")
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt"""
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    
    def _generate_salt(self) -> str:
        """Generate random salt"""
        return secrets.token_hex(16)
    
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
            # Validate inputs
            if not username or len(username) < 3:
                return False, "Username must be at least 3 characters long"
            
            if not self._validate_email(email):
                return False, "Invalid email format"
            
            is_valid_password, password_message = self._validate_password(password)
            if not is_valid_password:
                return False, password_message
            
            # Check if user already exists
            existing_user = self.db.query(
                "SELECT id FROM users WHERE username = ? OR email = ?",
                (username, email)
            )
            if existing_user:
                return False, "Username or email already exists"
            
            # Create user
            salt = self._generate_salt()
            password_hash = self._hash_password(password, salt)
            
            self.db.execute(
                "INSERT INTO users (username, email, password_hash, salt) VALUES (?, ?, ?, ?)",
                (username, email, password_hash, salt)
            )
            
            return True, "User registered successfully"
            
        except Exception as e:
            return False, f"Registration failed: {str(e)}"
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and return user info"""
        try:
            user_data = self.db.query(
                "SELECT id, username, email, password_hash, salt FROM users WHERE username = ? AND is_active = 1",
                (username,)
            )
            
            if not user_data:
                return None
            
            user = user_data[0]
            password_hash = self._hash_password(password, user['salt'])
            
            if password_hash == user['password_hash']:
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email']
                }
            
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
                    'openai_key': keys.get('openai_key'),
                    'pinecone_key': keys.get('pinecone_key'),
                    'pinecone_environment': keys.get('pinecone_environment'),  # Deprecated but kept for backward compatibility
                    'elevenlabs_key': keys.get('elevenlabs_key')
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
                """, (openai_key, pinecone_key, pinecone_environment, elevenlabs_key, user_id))
            else:
                # Insert new keys (ignoring pinecone_environment as it's deprecated)
                self.db.execute("""
                    INSERT INTO user_api_keys (user_id, openai_key, pinecone_key, pinecone_environment, elevenlabs_key)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, openai_key, pinecone_key, pinecone_environment, elevenlabs_key))
            
            return True
            
        except Exception as e:
            st.error(f"Error saving API keys: {str(e)}")
            return False

