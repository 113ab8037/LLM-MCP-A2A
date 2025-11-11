# Makefile for the MCP weather server
# Uses uv to manage dependencies and run tests

.PHONY: help install test test-unit test-integration test-demo test-all test-cov \
        clean lint format server run-server docker-build docker-run

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show help
	@echo "$(GREEN)MCP Weather Server - Makefile teams:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

install: ## Install dependencies via uv
	@echo "$(GREEN)Installing dependencies...$(NC)"
	uv sync --dev

test: test-unit ## Run main tests (alias for test-unit)

test-unit: ## Run quick unit tests with mocks
	@echo "$(GREEN)Running unit tests...$(NC)"
	uv run pytest test/test_weather_api.py -v --tb=short

test-integration: ## Run integration tests against a real API
	@echo "$(YELLOW)Running integration tests (requires internet)...$(NC)"
	uv run pytest test/test_integration.py -v --tb=short -m integration

test-demo: ## Run demo tests
	@echo "$(GREEN)Running demo tests...$(NC)"
	cd test && uv run python test_tools.py

test-all: ## Run all tests
	@echo "$(GREEN)Run all tests...$(NC)"
	uv run pytest test/ -v --tb=short

test-cov: ## Run tests with code coverage
	@echo "$(GREEN)Running tests with code coverage...$(NC)"
	uv run pytest test/ -v --cov=server --cov-report=term-missing --cov-report=html

test-fast: ## Run only fast tests (exclude slow ones)
	@echo "$(GREEN)Running quick tests...$(NC)"
	uv run pytest test/ -v -m "not slow"

test-ci: ## Run tests for CI/CD (unit tests only)
	@echo "$(GREEN)Running tests for CI...$(NC)"
	uv run pytest test/test_weather_api.py -v --tb=short --junitxml=test-results.xml

lint: ## Check the code with a linter
	@echo "$(GREEN)Checking code with a linter...$(NC)"
	uv run ruff check server.py test/

format: ## Format code
	@echo "$(GREEN)Code formatting...$(NC)"
	uv run ruff format server.py test/

server: run-server ## Start the server (alias)

run-server: ## Run MCP server locally
	@echo "$(GREEN)Launching the MCP weather server...$(NC)"
	uv run python server.py

dev-server: ## Run the server in development mode
	@echo "$(GREEN)Running the server in dev mode...$(NC)"
	uv run python server.py --reload

docker-build: ## Build a Docker image
	@echo "$(GREEN)Building a Docker image...$(NC)"
	docker build -t weather-mcp-server .

docker-run: ## Run the server in Docker
	@echo "$(GREEN)Running a server in Docker...$(NC)"
	docker run -p 8001:8001 weather-mcp-server

clean: ## Clear temporary files
	@echo "$(GREEN)Cleaning temporary files...$(NC)"
	rm -rf __pycache__ test/__pycache__ .pytest_cache htmlcov .coverage
	rm -f test-results.xml
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

deps-update: ## Update dependencies
	@echo "$(GREEN)Updating dependencies...$(NC)"
	uv sync --upgrade

deps-add: ## Add a new dependency (usage: make deps-add PACKAGE=package_name)
	@if [ -z "$(PACKAGE)" ]; then \
		echo "$(RED)Error: Please specify PACKAGE=package_name$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Adding a dependency $(PACKAGE)...$(NC)"
	uv add $(PACKAGE)

deps-add-dev: ## Add dev dependency (usage: make deps-add-dev PACKAGE=package_name)
	@if [ -z "$(PACKAGE)" ]; then \
		echo "$(RED)Error: Please specify PACKAGE=package_name$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Adding a dev dependency $(PACKAGE)...$(NC)"
	uv add --dev $(PACKAGE)

check: lint test-unit ## Full code review (linter + unit tests)

all: clean install lint test-cov ## Full cycle: cleaning, installation, linter, coating tests

# Examples of use in comments:
# make install          # Install dependencies
# make test            # Quick tests
# make test-all        # All tests
# make test-cov        # Tests + coverage
# make run-server      # Start the server
# make docker-build    # Build the Docker image
# make clean           # Clean up temporary files