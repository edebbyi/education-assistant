# Educational AI Assistant - Makefile
# A comprehensive build system for development, testing, and deployment

# Variables
PYTHON := python3
PIP := pip3
STREAMLIT := streamlit
VENV_DIR := .venv
REQUIREMENTS := requirements.txt
SRC_DIR := src
SCRIPTS_DIR := scripts
CONFIG_DIR := config
DATA_DIR := data

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
PURPLE := \033[0;35m
CYAN := \033[0;36m
WHITE := \033[0;37m
RESET := \033[0m

# Default target
.PHONY: help
help: ## Show this help message
	@echo "$(CYAN)Educational AI Assistant - Development Commands$(RESET)"
	@echo "================================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Quick Start:$(RESET)"
	@echo "  make setup    # Set up environment and install dependencies"
	@echo "  make run      # Run the application"
	@echo ""

.PHONY: setup
setup: ## Set up the development environment
	@echo "$(BLUE)Setting up Educational AI Assistant...$(RESET)"
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "$(YELLOW)Creating virtual environment...$(RESET)"; \
		$(PYTHON) -m venv $(VENV_DIR); \
	fi
	@echo "$(YELLOW)Activating virtual environment and installing dependencies...$(RESET)"
	@. $(VENV_DIR)/bin/activate && .venv/bin/python -m pip install --upgrade pip
	@. $(VENV_DIR)/bin/activate && .venv/bin/python -m pip install -r $(REQUIREMENTS)
	@echo "$(GREEN)✅ Setup complete!$(RESET)"
	@echo "$(CYAN)Next steps:$(RESET)"
	@echo "  1. Run 'make run' to start the application"
	@echo "  2. Open your browser to http://localhost:8501"
	@echo "  3. Create an account and configure your API keys"

.PHONY: install
install: setup ## Alias for setup

.PHONY: deps
deps: ## Install/update dependencies only
	@echo "$(BLUE)Installing/updating dependencies...$(RESET)"
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "$(RED)Virtual environment not found. Run 'make setup' first.$(RESET)"; \
		exit 1; \
	fi
	@. $(VENV_DIR)/bin/activate && .venv/bin/python -m pip install --upgrade pip
	@. $(VENV_DIR)/bin/activate && .venv/bin/python -m pip install -r $(REQUIREMENTS)
	@echo "$(GREEN)✅ Dependencies updated!$(RESET)"

.PHONY: run
run: ## Run the Streamlit application
	@echo "$(BLUE)Starting Educational AI Assistant...$(RESET)"
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "$(RED)Virtual environment not found. Run 'make setup' first.$(RESET)"; \
		exit 1; \
	fi
	@echo "$(CYAN)🚀 Application will be available at: http://localhost:8501$(RESET)"
	@. $(VENV_DIR)/bin/activate && .venv/bin/streamlit run app.py

.PHONY: dev
dev: ## Run in development mode with auto-reload
	@echo "$(BLUE)Starting in development mode...$(RESET)"
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "$(RED)Virtual environment not found. Run 'make setup' first.$(RESET)"; \
		exit 1; \
	fi
	@echo "$(CYAN)🔧 Development mode - files will auto-reload$(RESET)"
	@. $(VENV_DIR)/bin/activate && .venv/bin/streamlit run app.py --server.runOnSave=true

.PHONY: test
test: ## Run basic application tests
	@echo "$(BLUE)Running application tests...$(RESET)"
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "$(RED)Virtual environment not found. Run 'make setup' first.$(RESET)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Testing imports and basic functionality...$(RESET)"
	@. $(VENV_DIR)/bin/activate && .venv/bin/python -c "import sys; sys.path.append('.'); \
from src.auth.auth_manager import AuthManager; print('✅ Auth manager import: OK'); \
from src.core.document_processor import DocumentProcessor; print('✅ Document processor import: OK'); \
from src.core.response_generator import ResponseGenerator; print('✅ Response generator import: OK'); \
from src.database.database import Database; db = Database(); db.initialize(); print('✅ Database initialization: OK'); \
print('🎉 All tests passed!')"
	@echo "$(GREEN)✅ Basic tests completed successfully!$(RESET)"

.PHONY: test-db
test-db: ## Test database connectivity and setup
	@echo "$(BLUE)Testing database setup...$(RESET)"
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "$(RED)Virtual environment not found. Run 'make setup' first.$(RESET)"; \
		exit 1; \
	fi
	@. $(VENV_DIR)/bin/activate && .venv/bin/python -c "from src.database.database import Database; from src.auth.auth_manager import AuthManager; print('🔍 Testing database setup...'); db = Database(); db.initialize(); print('✅ Database initialization: OK'); auth = AuthManager(); print('✅ Auth manager setup: OK'); print('✅ Authentication system: READY'); print('🎉 Database tests passed!')"

.PHONY: clean
clean: ## Clean up cache files and temporary data
	@echo "$(BLUE)Cleaning up cache and temporary files...$(RESET)"
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name "*.pyd" -delete 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.log" -delete 2>/dev/null || true
	@rm -rf .pytest_cache/ 2>/dev/null || true
	@rm -rf .tox/ 2>/dev/null || true
	@rm -rf .coverage 2>/dev/null || true
	@rm -rf htmlcov/ 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup complete!$(RESET)"

.PHONY: clean-all
clean-all: clean ## Clean everything including virtual environment
	@echo "$(YELLOW)⚠️  This will remove the virtual environment. Continue? [y/N]$(RESET)"
	@read -r response; \
	if [ "$$response" = "y" ] || [ "$$response" = "Y" ]; then \
		echo "$(BLUE)Removing virtual environment...$(RESET)"; \
		rm -rf $(VENV_DIR); \
		echo "$(GREEN)✅ Complete cleanup finished!$(RESET)"; \
		echo "$(CYAN)Run 'make setup' to recreate the environment$(RESET)"; \
	else \
		echo "$(CYAN)Cleanup cancelled.$(RESET)"; \
	fi

.PHONY: reset-db
reset-db: ## Reset the database (removes all user data)
	@echo "$(YELLOW)⚠️  This will delete all user data, accounts, and documents. Continue? [y/N]$(RESET)"
	@read -r response; \
	if [ "$$response" = "y" ] || [ "$$response" = "Y" ]; then \
		echo "$(BLUE)Resetting database...$(RESET)"; \
		rm -f $(DATA_DIR)/.data/*.db 2>/dev/null || true; \
		mkdir -p $(DATA_DIR)/.data; \
		echo "$(GREEN)✅ Database reset complete!$(RESET)"; \
		echo "$(CYAN)All users will need to create new accounts$(RESET)"; \
	else \
		echo "$(CYAN)Database reset cancelled.$(RESET)"; \
	fi

.PHONY: backup-db
backup-db: ## Backup the current database
	@echo "$(BLUE)Creating database backup...$(RESET)"
	@mkdir -p backups
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	if [ -f "$(DATA_DIR)/.data/feedback.db" ]; then \
		cp "$(DATA_DIR)/.data/feedback.db" "backups/feedback_$$timestamp.db"; \
		echo "$(GREEN)✅ Database backed up to: backups/feedback_$$timestamp.db$(RESET)"; \
	else \
		echo "$(YELLOW)No database file found to backup$(RESET)"; \
	fi

.PHONY: requirements
requirements: ## Generate/update requirements.txt from current environment
	@echo "$(BLUE)Updating requirements.txt...$(RESET)"
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "$(RED)Virtual environment not found. Run 'make setup' first.$(RESET)"; \
		exit 1; \
	fi
	@. $(VENV_DIR)/bin/activate && .venv/bin/python -m pip freeze > $(REQUIREMENTS)
	@echo "$(GREEN)✅ Requirements updated!$(RESET)"

.PHONY: lint
lint: ## Run code linting (if flake8 is installed)
	@echo "$(BLUE)Running code linting...$(RESET)"
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "$(RED)Virtual environment not found. Run 'make setup' first.$(RESET)"; \
		exit 1; \
	fi
	@. $(VENV_DIR)/bin/activate && \
	if $(PYTHON) -c "import flake8" 2>/dev/null; then \
		flake8 $(SRC_DIR) main.py --max-line-length=120 --ignore=E501,W503; \
		echo "$(GREEN)✅ Linting complete!$(RESET)"; \
	else \
		echo "$(YELLOW)flake8 not installed. Install with: pip install flake8$(RESET)"; \
	fi

.PHONY: format
format: ## Format code with black (if installed)
	@echo "$(BLUE)Formatting code...$(RESET)"
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "$(RED)Virtual environment not found. Run 'make setup' first.$(RESET)"; \
		exit 1; \
	fi
	@. $(VENV_DIR)/bin/activate && \
	if $(PYTHON) -c "import black" 2>/dev/null; then \
		black $(SRC_DIR) main.py --line-length=120; \
		echo "$(GREEN)✅ Code formatting complete!$(RESET)"; \
	else \
		echo "$(YELLOW)black not installed. Install with: pip install black$(RESET)"; \
	fi

.PHONY: check
check: test lint ## Run all checks (tests + linting)
	@echo "$(GREEN)✅ All checks completed!$(RESET)"

.PHONY: demo-user
demo-user: ## Create a demo user for testing (requires running app)
	@echo "$(BLUE)Demo user creation instructions:$(RESET)"
	@echo "$(CYAN)1. Start the app with 'make run'$(RESET)"
	@echo "$(CYAN)2. Go to http://localhost:8501$(RESET)"
	@echo "$(CYAN)3. Click 'Sign Up' and create account:$(RESET)"
	@echo "   Username: demo"
	@echo "   Email: demo@example.com"
	@echo "   Password: DemoPassword123"
	@echo "$(CYAN)4. Configure API keys in Settings$(RESET)"
	@echo "$(CYAN)5. Upload a sample PDF and start chatting!$(RESET)"

.PHONY: process-content
process-content: ## Process content from URL or file (interactive)
	@echo "$(BLUE)Content Processing Utility$(RESET)"
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "$(RED)Virtual environment not found. Run 'make setup' first.$(RESET)"; \
		exit 1; \
	fi
	@echo "$(CYAN)Usage examples:$(RESET)"
	@echo "  $(SCRIPTS_DIR)/content_processor.py --help"
	@echo "  $(SCRIPTS_DIR)/content_processor.py --url 'https://example.com' --user-id 1 --openai-key KEY --pinecone-key KEY"
	@echo "  $(SCRIPTS_DIR)/content_processor.py --file 'document.txt' --user-id 1 --openai-key KEY --pinecone-key KEY"

.PHONY: status
status: ## Show application status and configuration
	@echo "$(CYAN)Educational AI Assistant - Status$(RESET)"
	@echo "=================================="
	@echo ""
	@echo "$(BLUE)Environment:$(RESET)"
	@if [ -d "$(VENV_DIR)" ]; then \
		echo "  Virtual Environment: $(GREEN)✅ Ready$(RESET)"; \
		. $(VENV_DIR)/bin/activate && $(PYTHON) --version | sed 's/^/  Python Version: /'; \
	else \
		echo "  Virtual Environment: $(RED)❌ Not found$(RESET)"; \
	fi
	@echo ""
	@echo "$(BLUE)Project Structure:$(RESET)"
	@echo "  Source Code: $(GREEN)$(SRC_DIR)/$(RESET)"
	@echo "  Scripts: $(GREEN)$(SCRIPTS_DIR)/$(RESET)"
	@echo "  Config: $(GREEN)$(CONFIG_DIR)/$(RESET)"
	@echo "  Data: $(GREEN)$(DATA_DIR)/$(RESET)"
	@echo ""
	@echo "$(BLUE)Database:$(RESET)"
	@if [ -f "$(DATA_DIR)/.data/feedback.db" ]; then \
		echo "  Database File: $(GREEN)✅ Found$(RESET)"; \
		echo "  Location: $(DATA_DIR)/.data/feedback.db"; \
	else \
		echo "  Database File: $(YELLOW)⚠️  Not initialized$(RESET)"; \
		echo "  Run the app once to create database"; \
	fi

.PHONY: logs
logs: ## Show application logs (if any)
	@echo "$(BLUE)Application Logs$(RESET)"
	@echo "================"
	@if [ -d "logs/" ]; then \
		find logs/ -name "*.log" -exec echo "$(CYAN){}:$(RESET)" \; -exec tail -20 {} \; 2>/dev/null; \
	else \
		echo "$(YELLOW)No log directory found$(RESET)"; \
	fi
	@echo ""
	@echo "$(CYAN)To see real-time logs, run the app with 'make dev'$(RESET)"

.PHONY: info
info: status ## Show detailed system information
	@echo ""
	@echo "$(BLUE)System Information:$(RESET)"
	@echo "  OS: $$(uname -s)"
	@echo "  Architecture: $$(uname -m)"
	@echo "  Shell: $$SHELL"
	@echo "  Working Directory: $$(pwd)"
	@echo ""
	@echo "$(BLUE)Quick Commands:$(RESET)"
	@echo "  Start App: $(GREEN)make run$(RESET)"
	@echo "  Run Tests: $(GREEN)make test$(RESET)"
	@echo "  Clean Up: $(GREEN)make clean$(RESET)"
	@echo "  Get Help: $(GREEN)make help$(RESET)"

# Default target when no arguments provided
.DEFAULT_GOAL := help