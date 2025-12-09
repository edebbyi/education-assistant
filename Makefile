# Educational AI Assistant - Makefile
# A comprehensive build system for development, testing, and deployment

# Variables
PYTHON := python3
PIP := pip3
STREAMLIT := streamlit
VENV_DIR := .venv
REQUIREMENTS := requirements.txt
SRC_DIR := src
CONFIG_DIR := config
DATA_DIR := data
ENV_FILE := .env

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
	@env_file="$(ENV_FILE)"; \
	if [ -f "$$env_file" ]; then \
		echo "$(CYAN)Loading environment from $$env_file$(RESET)"; \
		set -a; . "$$env_file"; set +a; \
	fi; \
	. $(VENV_DIR)/bin/activate && .venv/bin/streamlit run app.py

.PHONY: dev
dev: ## Run in development mode with auto-reload
	@echo "$(BLUE)Starting in development mode...$(RESET)"
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "$(RED)Virtual environment not found. Run 'make setup' first.$(RESET)"; \
		exit 1; \
	fi
	@echo "$(CYAN)🔧 Development mode - files will auto-reload$(RESET)"
	@env_file="$(ENV_FILE)"; \
	if [ -f "$$env_file" ]; then \
		echo "$(CYAN)Loading environment from $$env_file$(RESET)"; \
		set -a; . "$$env_file"; set +a; \
	fi; \
	. $(VENV_DIR)/bin/activate && .venv/bin/streamlit run app.py --server.runOnSave=true

.PHONY: test
test: ## Run basic application tests
	@echo "$(BLUE)Running application tests...$(RESET)"
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "$(RED)Virtual environment not found. Run 'make setup' first.$(RESET)"; \
		exit 1; \
	fi
	@env_file="$(ENV_FILE)"; \
	if [ -f "$$env_file" ]; then \
		echo "$(CYAN)Loading environment from $$env_file$(RESET)"; \
		set -a; . "$$env_file"; set +a; \
	fi; \
	. $(VENV_DIR)/bin/activate && .venv/bin/pytest -q
	@echo "$(GREEN)✅ Tests completed!$(RESET)"

.PHONY: test-db
test-db: ## Test database connectivity and setup
	@echo "$(BLUE)Testing database setup...$(RESET)"
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "$(RED)Virtual environment not found. Run 'make setup' first.$(RESET)"; \
		exit 1; \
	fi
	@env_file="$(ENV_FILE)"; \
	if [ -f "$$env_file" ]; then \
		echo "$(CYAN)Loading environment from $$env_file$(RESET)"; \
		set -a; . "$$env_file"; set +a; \
	fi; \
	. $(VENV_DIR)/bin/activate && .venv/bin/pytest -q tests/test_database_connection.py

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

# Default target when no arguments provided
.DEFAULT_GOAL := help
