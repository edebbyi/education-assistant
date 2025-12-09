import streamlit as st
from .auth_manager import AuthManager
from typing import Dict, Optional
import re
import os


def _ensure_encryption_key():
    if not os.environ.get("APP_ENCRYPTION_KEY"):
        st.error("APP_ENCRYPTION_KEY is not set. Please configure it to store API keys securely.")
        return False
    return True

def api_key_settings_interface():
    """Interface for managing API keys"""
    if not st.session_state.get('authenticated', False):
        st.error("Please login to access settings")
        return

    if not _ensure_encryption_key():
        return
    
    auth = AuthManager()
    user_id = st.session_state.user['id']
    
    st.title("⚙️ Settings")
    st.markdown("---")
    
    # Get current API keys
    current_keys = auth.get_user_api_keys(user_id)
    
    # API Keys Section
    st.subheader("🔑 API Keys")
    st.markdown("Configure your API keys to use the Educational AI Assistant. Your keys are encrypted and stored securely.")
    
    # Show current key status
    st.markdown("### Current API Key Status")
    if current_keys.get('openai_key'):
        st.success("✅ OpenAI API Key: Configured")
    else:
        st.error("❌ OpenAI API Key: Not configured")
        
    if current_keys.get('pinecone_key'):
        st.success("✅ Pinecone API Key: Configured")
    else:
        st.error("❌ Pinecone API Key: Not configured")
        
    if current_keys.get('elevenlabs_key'):
        st.success("✅ ElevenLabs API Key: Configured (Voice synthesis available)")
    else:
        st.info("ℹ️ ElevenLabs API Key: Not configured (Voice synthesis unavailable)")
    
    st.markdown("---")
    
    # API Key Form
    with st.form("api_keys_form", clear_on_submit=False):
        st.markdown("### Enter API Keys")
        st.info("📝 Leave fields empty to keep existing keys unchanged")
        
        # OpenAI API Key
        st.markdown("**Required Keys**")
        openai_key = st.text_input(
            "OpenAI API Key",
            type="password",
            placeholder="Enter new OpenAI API key (or leave empty to keep current)",
            help="Required for AI-powered responses. Get yours at https://platform.openai.com/api-keys"
        )
        
        # Pinecone Key
        pinecone_key = st.text_input(
            "Pinecone API Key",
            type="password",
            placeholder="Enter new Pinecone API key (or leave empty to keep current)",
            help="Required for document storage and search. Get yours at https://app.pinecone.io"
        )
        
        # ElevenLabs Key (Optional)
        st.markdown("**Optional Keys**")
        elevenlabs_key = st.text_input(
            "ElevenLabs API Key (Optional)",
            type="password",
            placeholder="Enter ElevenLabs API key for voice features (optional)",
            help="Optional: For text-to-speech functionality. Get yours at https://elevenlabs.io"
        )
        
        # Submit button
        submitted = st.form_submit_button("💾 Save API Keys", type="primary")
        
        if submitted:
            # Determine final keys (use new if provided, otherwise keep existing)
            final_openai_key = openai_key.strip() if openai_key.strip() else current_keys.get('openai_key')
            final_pinecone_key = pinecone_key.strip() if pinecone_key.strip() else current_keys.get('pinecone_key')
            final_elevenlabs_key = elevenlabs_key.strip() if elevenlabs_key.strip() else current_keys.get('elevenlabs_key')
            
            # Validation
            errors = []
            if not final_openai_key:
                errors.append("OpenAI API key is required")
            elif not final_openai_key.startswith('sk-'):
                errors.append("OpenAI API key must start with 'sk-'")
                
            if not final_pinecone_key:
                errors.append("Pinecone API key is required")
            elif len(final_pinecone_key) < 10:
                errors.append("Pinecone API key appears too short")
            
            if errors:
                for error in errors:
                    st.error(f"⚠️ {error}")
            else:
                # Save the keys
                with st.spinner("Saving API keys..."):
                    try:
                        success = auth.save_user_api_keys(
                            user_id=user_id,
                            openai_key=final_openai_key,
                            pinecone_key=final_pinecone_key,
                            pinecone_environment=None,
                            elevenlabs_key=final_elevenlabs_key
                        )
                        
                        if success:
                            st.success("✅ API keys saved successfully!")
                            st.info("🔄 Your API keys are now stored. The page will refresh to apply changes.")
                            try:
                                from ..utils.audit import log_action
                                log_action(user_id, "update_api_keys", "openai,pinecone,elevenlabs")
                            except Exception:
                                pass
                            # Clear cached instances
                            for key in ['processor', 'generator', 'synthesizer']:
                                if key in st.session_state:
                                    del st.session_state[key]
                            
                            # Add small delay before rerun so user can see the message
                            import time
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("❌ Failed to save API keys. Please try again.")
                    except Exception as e:
                        st.error(f"❌ Error saving API keys: {str(e)}")
    
    # Instructions
    st.markdown("---")
    st.subheader("📝 How to Get API Keys")
    
    with st.expander("OpenAI API Key"):
        st.markdown("""
        1. Go to [OpenAI Platform](https://platform.openai.com/)
        2. Sign in or create an account
        3. Navigate to API Keys section
        4. Click "Create new secret key"
        5. Copy the key and paste it above
        
        **Note**: You'll need credits in your OpenAI account to use the API.
        """)
    
    with st.expander("Pinecone API Key"):
        st.markdown("""
        1. Go to [Pinecone](https://app.pinecone.io/)
        2. Sign in or create an account
        3. Create a new project if needed
        4. Go to "API Keys" in your project dashboard
        5. Copy the API key and paste it above
        
        **Note**: Pinecone offers a free tier for getting started.
        **Note**: Environment is no longer required with the latest Pinecone SDK.
        """)
    
    with st.expander("ElevenLabs API Key (Optional)"):
        st.markdown("""
        1. Go to [ElevenLabs](https://elevenlabs.io/)
        2. Sign in or create an account
        3. Go to your Profile settings
        4. Find the API key section
        5. Copy the key and paste it above
        
        **Note**: This is optional and only needed for text-to-speech features.
        """)

def profile_settings_interface():
    """Interface for managing user profile"""
    if not st.session_state.get('authenticated', False):
        st.error("Please login to access profile settings")
        return
    
    user = st.session_state.user
    
    st.subheader("👤 Profile Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"**Username:** {user['username']}")
    
    with col2:
        st.info(f"**Email:** {user['email']}")
    
    # Future: Add functionality to update profile information
    st.markdown("*Profile editing will be available in a future update.*")

def check_api_keys_configured() -> Dict[str, bool]:
    """Check if user has configured the required API keys"""
    if not st.session_state.get('authenticated', False):
        return {'openai': False, 'pinecone': False, 'elevenlabs': False}
    
    auth = AuthManager()
    user_id = st.session_state.user['id']
    keys = auth.get_user_api_keys(user_id)
    
    return {
        'openai': bool(keys.get('openai_key')),
        'pinecone': bool(keys.get('pinecone_key')),
        'elevenlabs': bool(keys.get('elevenlabs_key'))
    }

def get_user_api_keys() -> Dict[str, Optional[str]]:
    """Get the current user's API keys"""
    if not st.session_state.get('authenticated', False):
        return {}
    
    auth = AuthManager()
    user_id = st.session_state.user['id']
    return auth.get_user_api_keys(user_id)
