import streamlit as st
import os
from datetime import datetime
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
import time

# Import custom modules
from src.ui.auth_interface import login_signup_interface, logout, require_auth
from src.auth.user_settings import api_key_settings_interface, profile_settings_interface, check_api_keys_configured, get_user_api_keys
from src.core.document_processor import DocumentProcessor
from src.core.agent import AgentResponder
from src.core.voice_synthesizer import VoiceSynthesizer
from src.database.feedback_manager import FeedbackManager
from src.ui.database_viewer import view_feedback_data
from src.ui.admin_audit import view_audit_logs
from src.utils.audit import is_admin

st.set_page_config(
    page_title="Educational AI Assistant",
    page_icon="🎓",
    layout="wide"
)

def init_session_state():
    """Initialize session state variables"""
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'Chat Interface'
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'last_response' not in st.session_state:
        st.session_state.last_response = None
    if 'last_question' not in st.session_state:
        st.session_state.last_question = None

def init_user_specific_components():
    """Initialize user-specific components with their API keys"""
    if not st.session_state.get('authenticated', False):
        return False
    
    user_api_keys = get_user_api_keys()
    user_id = st.session_state.user['id']
    
    # Check if required API keys are configured
    if not user_api_keys.get('openai_key') or not user_api_keys.get('pinecone_key'):
        return False
    
    # Initialize components with user's API keys
    if 'processor' not in st.session_state or st.session_state.get('current_user_id') != user_id:
        st.session_state.processor = DocumentProcessor(
            user_id=user_id,
            api_keys=user_api_keys
        )
        st.session_state.current_user_id = user_id
    
    if 'agent' not in st.session_state or st.session_state.get('current_user_id') != user_id:
        st.session_state.agent = AgentResponder(
            processor=st.session_state.processor,
            api_key=user_api_keys.get('openai_key'),
            last_answer_getter=lambda: st.session_state.get('last_response')
        )
        
    if 'synthesizer' not in st.session_state or st.session_state.get('current_user_id') != user_id:
        st.session_state.synthesizer = VoiceSynthesizer(
            api_key=user_api_keys.get('elevenlabs_key')
        )
    
    if 'feedback' not in st.session_state:
        st.session_state.feedback = FeedbackManager()
    
    return True

def format_message(is_user: bool, content: str, timestamp: str = None):
    """Format a message with custom CSS styling"""
    if is_user:
        st.markdown(f"""
        <div style="display: flex; justify-content: flex-end; margin-bottom: 1rem;">
            <div style="background-color: #2b313e; padding: 1rem; border-radius: 0.5rem; max-width: 80%;">
                <p style="margin: 0; color: white;">👤 You: {content}</p>
                <p style="margin: 0; color: #666; font-size: 0.8rem;">{timestamp if timestamp else datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="display: flex; margin-bottom: 1rem;">
            <div style="background-color: #0e1117; padding: 1rem; border-radius: 0.5rem; max-width: 100%;">
                <p style="margin: 0; color: white; white-space: pre-wrap;">{content}</p>
                <p style="margin: 0; color: #666; font-size: 0.8rem;">{timestamp if timestamp else datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

def download_transcript():
    """Generate and download chat transcript as PDF"""
    if not st.session_state.chat_history:
        return

    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    # Create custom style for messages
    styles.add(ParagraphStyle(
        name='Message',
        parent=styles['Normal'],
        spaceBefore=6,
        spaceAfter=6,
        leftIndent=20,
    ))

    # Prepare story (content) for PDF
    story = [
        Paragraph("Chat Transcript", styles['Title']),
        Spacer(1, 12),
        Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']),
        Spacer(1, 12)
    ]

    # Add messages to story
    for msg in st.session_state.chat_history:
        speaker = "👤 You" if msg["is_user"] else "🤖 Assistant"
        timestamp = msg["timestamp"]
        content = msg["content"]

        # Format message with speaker and timestamp
        message_text = f"{speaker} ({timestamp}):\\n{content}"
        story.append(Paragraph(message_text, styles['Message']))
        story.append(Spacer(1, 6))

    # Build PDF
    doc.build(story)

    # Create download button
    st.download_button(
        label="📥 Download Chat Transcript (PDF)",
        data=buffer.getvalue(),
        file_name=f"chat_transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        mime="application/pdf"
    )

def display_chat_history():
    """Display all messages in the chat history"""
    for message in st.session_state.chat_history:
        format_message(
            message["is_user"],
            message["content"],
            message["timestamp"]
        )

def generate_response(user_question: str):
    """Generate response using all available context"""
    try:
        if 'agent' in st.session_state:
            return st.session_state.agent.run(user_question)
        # Fallback if agent is unavailable
        return "Assistant is not initialized. Please reload the app."
    except Exception as e:
        return f"Error generating response: {str(e)}"

def chat_interface():
    """Main chat interface"""
    if not require_auth():
        st.error("Please log in to access the chat interface")
        return
    
    # Check API keys are configured
    if not init_user_specific_components():
        st.warning("⚠️ Please configure your API keys in the Settings page before using the chat interface.")
        if st.button("Go to Settings"):
            # Set the redirect flag instead of directly modifying the page state
            st.session_state.redirect_to_settings = True
            st.rerun()
        return

    st.title("🤖 AI Chat Assistant")
    st.markdown("Ask questions about your uploaded documents and get detailed, source-backed answers.")
    
    # Document management in sidebar
    with st.sidebar:
        st.header("📚 Document Management")
        
        # Show stored documents
        st.subheader("Your Documents")
        stored_docs = st.session_state.processor.list_stored_documents()
        if stored_docs:
            for doc in stored_docs:
                st.info(f"📄 {doc['filename']}\\nUploaded: {doc['uploaded_at']}")
        else:
            st.write("No documents uploaded yet.")
        
        # Document deletion
        if stored_docs:
            st.divider()
            st.subheader("Delete Document")
            doc_to_delete = st.selectbox(
                "Select document to delete",
                options=[doc['filename'] for doc in stored_docs],
                key="delete_doc_select"
            )
            if st.button("Delete Selected Document", type="secondary"):
                with st.spinner("Deleting document..."):
                    result = st.session_state.processor.delete_document(doc_to_delete)
                    if result["status"] == "success":
                        st.success(result["message"])
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(result["message"])

        st.divider()
        st.subheader("Upload New Document")
        uploaded_file = st.file_uploader("Upload PDF", type=['pdf'])

        if uploaded_file:
            if st.button("Process Document"):
                with st.spinner("Processing PDF..."):
                    try:
                        result = st.session_state.processor.process_pdf(uploaded_file)
                        
                        if result == "already_exists":
                            st.warning("📋 This document has already been uploaded and processed.")
                        elif result == "stored_in_pinecone":
                            st.success("✅ Document successfully processed and stored!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Failed to process document.")
                            st.warning("⚠️ Possible issues:")
                            st.markdown("""
                            - **Pinecone API Key**: Your Pinecone API key may be incorrect or expired
                            - **Network**: Check your internet connection
                            - **Quota**: You may have exceeded your Pinecone free tier limits
                            
                            **To fix**:
                            1. Go to [Pinecone Console](https://app.pinecone.io/) and verify your API key
                            2. Create a new API key if needed
                            3. Update the key in Settings > API Keys
                            """)
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        if "401" in str(e) or "Unauthorized" in str(e):
                            st.warning("⚠️ Your Pinecone API key appears to be invalid. Please check it in Settings.")

    # Chat interface
    chat_container = st.container()
    
    # User input
    with st.container():
        user_question = st.chat_input("Ask a question about your documents...")
        
        if user_question:
            try:
                # Add user message to history
                st.session_state.chat_history.append({
                    "is_user": True,
                    "content": user_question,
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

                # Generate response
                with st.spinner("Generating response..."):
                    response = generate_response(user_question)
                    st.session_state.last_response = response
                    st.session_state.last_question = user_question

                # Add assistant response to history
                st.session_state.chat_history.append({
                    "is_user": False,
                    "content": response,
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

                # Force a rerun to update the display immediately
                st.rerun()

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

    # Display chat history
    with chat_container:
        display_chat_history()

        # Download transcript button
        if len(st.session_state.chat_history) > 0:
            download_transcript()

        # Generate audio (if ElevenLabs key is configured)
        if (st.session_state.chat_history and 
            not st.session_state.chat_history[-1]["is_user"] and
            get_user_api_keys().get('elevenlabs_key')):
            with st.spinner("Converting to speech..."):
                try:
                    audio_path = st.session_state.synthesizer.generate_speech(
                        st.session_state.chat_history[-1]["content"]
                    )
                    if audio_path:
                        st.audio(audio_path)
                    else:
                        st.warning("Audio generation temporarily unavailable.")
                except Exception as e:
                    st.warning("Audio generation unavailable at the moment")

        # Feedback section
        if st.session_state.last_response and st.session_state.last_question:
            with st.expander("📝 Provide Feedback"):
                feedback_category = st.selectbox(
                    "How would you rate this response?",
                    ["Helpful", "Not Quite Right", "Suggest an Improvement"]
                )
                rating = st.slider("Rating (1-5 stars)", 1, 5, 3)
                feedback_text = st.text_area(
                    "Additional comments or suggestions (optional)",
                    help="Please provide any specific feedback that could help improve the response."
                )

                if st.button("Submit Feedback"):
                    try:
                        st.session_state.feedback.save_feedback(
                            user_id=st.session_state.user['id'],
                            user_question=st.session_state.last_question,
                            ai_response=st.session_state.last_response,
                            feedback_category=feedback_category,
                            rating=rating,
                            feedback_text=feedback_text
                        )
                        st.success("Thank you for your feedback! It helps us improve the assistant.")
                    except Exception as e:
                        st.error(f"Error saving feedback: {str(e)}")

def main():
    """Main application function"""
    init_session_state()
    
    # Check if user is authenticated
    if not login_signup_interface():
        return  # Show login/signup page
    
    # User is authenticated, show main interface
    user = st.session_state.user
    
    # Top navigation bar
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.title(f"👋 Welcome back, {user['username']}!")
    
    with col2:
        api_status = check_api_keys_configured()
        if api_status['openai'] and api_status['pinecone']:
            st.success("✅ API Keys Configured")
        else:
            st.error("❌ API Keys Missing")
    
    with col3:
        if st.button("🚪 Logout"):
            logout()
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("---")
        
        # Handle redirect to settings
        if st.session_state.get('redirect_to_settings', False):
            st.session_state.current_page = "Settings"
            del st.session_state.redirect_to_settings
        
        # Get current page index
        pages = ["Chat Interface", "Settings", "Feedback Analysis"]
        if is_admin(st.session_state.get("user")):
            pages.append("Audit Logs")
        try:
            current_index = pages.index(st.session_state.current_page)
        except (ValueError, AttributeError):
            current_index = 0
            st.session_state.current_page = pages[0]
        
        # Radio button for navigation
        selected_page = st.radio(
            "Navigate",
            pages,
            index=current_index,
            key="navigation_radio"
        )
        
        # Update current page if user clicked a different option
        if selected_page != st.session_state.current_page:
            st.session_state.current_page = selected_page
        
        page = st.session_state.current_page
    
    # Page routing
    if page == "Chat Interface":
        chat_interface()
    elif page == "Settings":
        st.markdown("---")
        tab1, tab2 = st.tabs(["API Keys", "Profile"])
        with tab1:
            api_key_settings_interface()
        with tab2:
            profile_settings_interface()
    elif page == "Feedback Analysis":
        if st.session_state.get('authenticated'):
            view_feedback_data()
        else:
            st.error("Please log in to view feedback data")
    elif page == "Audit Logs":
        if st.session_state.get('authenticated') and is_admin(st.session_state.get("user")):
            view_audit_logs()
        else:
            st.error("Access denied.")

if __name__ == "__main__":
    main()
