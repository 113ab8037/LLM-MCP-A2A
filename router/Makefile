# Makefile for the Router Agent Project

# Use .PHONY to ensure these targets run even if files with the same name exist.
.PHONY: help install test run stop clean

# Set the default goal to 'help'
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
NONE := \033[0m

help:
	@echo "Available commands:"
	@echo ""
	@echo "  $(GREEN)install$(NONE) - Install all dependencies for development"
	@echo "  $(GREEN)test$(NONE)    - Run all tests"
	@echo "  $(GREEN)run$(NONE)     - Start the A2A and FastAPI servers"
	@echo "  $(GREEN)stop$(NONE)    - Stop any running servers"
	@echo "  $(GREEN)clean$(NONE)   - Clean up generated Python files and caches"
	@echo ""

install:
	@echo "$(BLUE)Installing development dependencies...$(NONE)"
	@uv pip install -e '.[dev]'

test:
	@echo "$(BLUE)Running tests with coverage report...$(NONE)"
	@uv run pytest --cov=app --cov-report=term-missing

run: stop
	@echo "$(BLUE)Starting A2A and FastAPI servers...$(NONE)"
	@uv run python -m app.start_server both

stop:
	@echo "$(BLUE)Stopping servers on ports 8000 and 10000...$(NONE)"
	@kill -9 $$(lsof -t -i:8000) 2>/dev/null || true
	@kill -9 $$(lsof -t -i:10000) 2>/dev/null || true

clean:
	@echo "$(BLUE)Cleaning up...$(NONE)"
	@find . -type f -name '*.py[co]' -delete
	@find . -type d -name '__pycache__' -exec rm -rf {} +
	@rm -rf .pytest_cache
	@rm -rf .mypy_cache
	@rm -rf .ruff_cache
	@rm -f server.log 