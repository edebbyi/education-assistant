import streamlit as st
from ..auth.auth_manager import AuthManager

def login_signup_interface():
    """Streamlit interface for login and signup"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user = None
    
    if st.session_state.authenticated:
        return True
    
    auth = AuthManager()
    
    st.title("🎓 Educational AI Assistant")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login to Your Account")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if username and password:
                    user = auth.authenticate_user(username, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.error("Please fill in all fields")
    
    with tab2:
        st.subheader("Create New Account")
        with st.form("signup_form"):
            new_username = st.text_input("Choose Username")
            new_email = st.text_input("Email Address")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit_signup = st.form_submit_button("Sign Up")
            
            if submit_signup:
                if new_username and new_email and new_password and confirm_password:
                    if new_password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        success, message = auth.register_user(new_username, new_email, new_password)
                        if success:
                            st.success(message)
                            st.info("Please switch to the Login tab to sign in")
                        else:
                            st.error(message)
                else:
                    st.error("Please fill in all fields")
    
    return False

def logout():
    """Logout current user"""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.clear()
    st.rerun()

def require_auth():
    """Decorator/function to require authentication"""
    if not st.session_state.get('authenticated', False):
        return False
    return True