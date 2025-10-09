# Educational AI Assistant 🎓

A multi-user Educational AI Assistant that allows users to upload their own documents and receive AI-powered answers with direct quotes. Built with Streamlit, using vector search with Pinecone and OpenAI embeddings for contextually accurate responses.

## 🌟 Features

- **🔐 Secure Multi-User System**: Each user has their own isolated account with secure authentication
- **🔑 Personal API Key Management**: Users configure their own OpenAI, Pinecone, and ElevenLabs API keys
- **📚 Isolated Document Storage**: Each user gets their own Pinecone index and document database
- **🤖 Context-Aware Q&A**: Get detailed answers with direct quotes from your uploaded documents
- **🎤 Voice Synthesis**: Optional text-to-speech using ElevenLabs (user-configured)
- **📊 Feedback System**: Rate responses and provide feedback for continuous improvement
- **💾 Chat History**: Export chat transcripts as PDF files
- **📱 Responsive UI**: Clean, modern interface built with Streamlit

## 🏗️ Architecture

```
education-assistant/
├── app.py                      # Application entry point
├── src/                        # Source code modules
│   ├── auth/                   # Authentication system
│   │   ├── auth_manager.py     # User authentication logic
│   │   └── user_settings.py    # API key management
│   ├── core/                   # Core business logic
│   │   ├── document_processor.py # PDF processing & vector storage
│   │   ├── response_generator.py # AI response generation
│   │   └── voice_synthesizer.py  # Text-to-speech synthesis
│   ├── database/               # Database operations
│   │   ├── database.py         # SQLite operations
│   │   ├── database_manager.py # PostgreSQL operations (optional)
│   │   └── feedback_manager.py # User feedback management
│   ├── ui/                     # User interface components
│   │   ├── auth_interface.py   # Login/signup interface
│   │   └── database_viewer.py  # Feedback analysis interface
│   └── utils/                  # Utility functions
├── config/                     # Configuration files
│   └── pyproject.toml         # Python project configuration
├── data/                      # Data storage
│   └── .data/                # SQLite databases
└── scripts/                   # Utility scripts
    └── content_processor.py  # Content processing utility
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- API Keys:
  - OpenAI API key (required)
  - Pinecone API key (required)
  - ElevenLabs API key (optional, for voice synthesis)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd education-assistant
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   # or using the pyproject.toml:
   pip install -e .
   ```

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

5. **First-time setup**
   - Create an account via the signup interface
   - Configure your API keys in the Settings page
   - Upload your first document and start chatting!

## 🔧 Configuration

### User Setup (via Web Interface)
Users configure their own API keys through the application:

1. **Create Account**: Sign up with username, email, and password
2. **API Keys**: Navigate to Settings → API Keys
   - Add your OpenAI API key
   - Add your Pinecone API key (environment no longer needed)
   - Optionally add ElevenLabs API key for voice features

### Environment Variables (Optional Fallbacks)
```bash
# Optional fallback keys
OPENAI_API_KEY=your_openai_key
PINECONE_API_KEY=your_pinecone_key
ELEVENLABS_API_KEY=your_elevenlabs_key

# DEPRECATED: No longer needed with latest Pinecone SDK
# PINECONE_ENVIRONMENT=your_pinecone_environment

# Database configuration (optional)
PGDATABASE=your_postgres_db
PGUSER=your_postgres_user
PGPASSWORD=your_postgres_password
PGHOST=your_postgres_host
PGPORT=your_postgres_port
```

## 📖 Usage

### For End Users

1. **Account Creation**
   - Visit the application URL
   - Click "Sign Up" and create your account
   - Login with your credentials

2. **API Key Configuration**
   - Go to Settings → API Keys
   - Enter your OpenAI API key (required)
   - Enter your Pinecone API key (required)
   - Optionally add ElevenLabs key for voice features

3. **Document Upload**
   - Upload PDF documents via the sidebar
   - Wait for processing (documents are embedded and stored)
   - View your uploaded documents in the sidebar

4. **Chat with AI**
   - Ask questions about your uploaded documents
   - Receive detailed answers with direct quotes
   - Rate responses and provide feedback
   - Download chat transcripts as PDF

### For Developers

The codebase follows a modular architecture with clear separation of concerns:
- Authentication and user management in `src/auth/`
- Core AI logic in `src/core/`
- Database operations in `src/database/`
- UI components in `src/ui/`

## 🔒 Security & Privacy

- **Password Security**: Uses PBKDF2 with SHA-256 and random salts
- **Data Isolation**: Each user's documents and data are completely isolated
- **API Key Security**: User API keys are encrypted and stored securely
- **Session Management**: Secure session handling with Streamlit

## 🛠️ Development

### Project Structure
- **src/auth/**: Authentication and user management
- **src/core/**: Core business logic (document processing, AI responses)
- **src/database/**: Database operations and data management
- **src/ui/**: User interface components
- **config/**: Configuration files and deployment settings

### Key Technologies
- **Frontend**: Streamlit
- **AI**: OpenAI GPT-4, LangChain
- **Vector Storage**: Pinecone
- **Database**: SQLite (default) or PostgreSQL
- **Voice**: ElevenLabs Text-to-Speech
- **PDF Processing**: PyPDF2

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Review the code documentation and architecture overview above
- Open an issue for bug reports or feature requests
- Check existing issues for common problems and solutions

---

Built with ❤️ for education and learning