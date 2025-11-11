# AI Agent Template Makefile
# Commands for managing Docker Compose configurations

.PHONY: help build up down restart logs clean test dev phoenix phoenix-up phoenix-down agent-up agent-down network

# Colors for output
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
BLUE := \033[34m
RESET := \033[0m

# Variables
COMPOSE_FILE := docker-compose.yml
PHOENIX_COMPOSE_FILE := docker-compose.phoenix.yml
PROJECT_NAME := ai-agent-template
NETWORK_NAME := agent-network

# Help
help: ## Show this help message
	@echo "$(GREEN)AI Agent Template - Makefile teams$(RESET)"
	@echo ""
	@echo "$(BLUE)Main teams:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Examples of use:$(RESET)"
	@echo "  make up          # Start core services"
	@echo "  make phoenix     # Run with Phoenix monitoring"
	@echo "  make dev         # Development mode"
	@echo "  make logs        # View logs"
	@echo "  make clean       # Clear all"

# Создание сети Docker
network: ## Создать Docker сеть
	@echo "$(BLUE)Creating a Docker network...$(RESET)"
	@docker network create $(NETWORK_NAME) 2>/dev/null || echo "$(YELLOW)Сеть $(NETWORK_NAME) уже существует$(RESET)"

# Основные команды
build: network ## Собрать Docker образы
	@echo "$(BLUE)Building Docker images...$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) build

up: network ## Start core services
	@echo "$(GREEN)Launching core services...$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN)✅ Services are running!$(RESET)"
	@echo "$(YELLOW)Agent available at: http://localhost:10002$(RESET)"

down: ## Stop all services
	@echo "$(RED)Stopping services...$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) down 2>/dev/null || true
	@docker-compose -f $(PHOENIX_COMPOSE_FILE) down 2>/dev/null || true
	@echo "$(GREEN)✅ Services have been stopped$(RESET)"

restart: down up ## Restart services

# Phoenix monitoring
phoenix: phoenix-up ## Run with Phoenix monitoring (alias)

phoenix-up: network ## Запустить сервисы с Phoenix мониторингом
	@echo "$(GREEN)Launching services with Phoenix monitoring...$(RESET)"
	@docker-compose -f $(PHOENIX_COMPOSE_FILE) up -d
	@echo "$(GREEN)✅ Phoenix services launched!$(RESET)"
	@echo "$(YELLOW)Agent available at: http://localhost:10002$(RESET)"
	@echo "$(YELLOW)Phoenix Dashboard: http://localhost:6006$(RESET)"

phoenix-down: ## Stop Phoenix services
	@echo "$(RED)Phoenix services shutdown...$(RESET)"
	@docker-compose -f $(PHOENIX_COMPOSE_FILE) down
	@echo "$(GREEN)✅ Phoenix services have been stopped$(RESET)"

phoenix-restart: phoenix-down phoenix-up ## Restart Phoenix services

# Separate agent launch
agent-up: network ## Run agent only
	@echo "$(GREEN)Launching the agent...$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) up -d evolution-agent
	@echo "$(GREEN)✅ The agent is running on http://localhost:10002$(RESET)"

agent-down: ## Stop agent only
	@echo "$(RED)Stopping an agent...$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) stop evolution-agent
	@echo "$(GREEN)✅ Agent stopped$(RESET)"

# Logs and monitoring
logs: ## Show logs of all services
	@echo "$(BLUE)Service logs:$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) logs -f --tail=100

logs-agent: ## Show agent logs only
	@echo "$(BLUE)Agent logs:$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) logs -f --tail=100 evolution-agent

logs-phoenix: ## Show Phoenix service logs
	@echo "$(BLUE)Phoenix Logs:$(RESET)"
	@docker-compose -f $(PHOENIX_COMPOSE_FILE) logs -f --tail=100

status: ## Show service status
	@echo "$(BLUE)Status of core services:$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) ps
	@echo ""
	@echo "$(BLUE)Phoenix Services Status:$(RESET)"
	@docker-compose -f $(PHOENIX_COMPOSE_FILE) ps 2>/dev/null || echo "$(YELLOW)Phoenix сервисы не запущены$(RESET)"

# Development
dev: network ## Development mode (with auto-reboot)
	@echo "$(GREEN)Launch in development mode...$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) up --build
	@echo "$(YELLOW)To exit, press Ctrl+C$(RESET)"

dev-phoenix: network ## Development mode with Phoenix
	@echo "$(GREEN)Running in development mode with Phoenix...$(RESET)"
	@docker-compose -f $(PHOENIX_COMPOSE_FILE) up --build
	@echo "$(YELLOW)Phoenix Dashboard: http://localhost:6006$(RESET)"
	@echo "$(YELLOW)To exit, press Ctrl+C$(RESET)"

# Testing
test: ## Run tests
	@echo "$(BLUE)Running tests...$(RESET)"
	@docker run --rm -v $(PWD):/app -w /app python:3.12 bash -c "\
		pip install -r requirements.txt && \
		python -m pytest tests/ -v"

test-mcp: phoenix-up ## Test MCP tracing
	@echo "$(BLUE)Testing MCP tracing...$(RESET)"
	@sleep 5  # We are waiting for the launch of services
	@python test_mcp_tracing.py
	@echo "$(YELLOW)Check it out Phoenix Dashboard: http://localhost:6006$(RESET)"

# Очистка
clean: down ## Clean containers and images
	@echo "$(RED)Cleaning up Docker resources...$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) down --rmi all --volumes --remove-orphans 2>/dev/null || true
	@docker-compose -f $(PHOENIX_COMPOSE_FILE) down --rmi all --volumes --remove-orphans 2>/dev/null || true
	@echo "$(GREEN)✅ Cleaning is complete$(RESET)"

clean-volumes: ## Delete all volumes
	@echo "$(RED)Deleting volumes...$(RESET)"
	@docker volume prune -f
	@echo "$(GREEN)✅ Volumes удалены$(RESET)"

clean-all: clean clean-volumes ## Complete cleaning
	@echo "$(RED)Complete cleaning of the Docker system...$(RESET)"
	@docker system prune -af
	@echo "$(GREEN)✅ Полная очистка завершена$(RESET)"

# Utilities
shell: ## Login to the agent container shell
	@echo "$(BLUE)Login to the shell agent...$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) exec evolution-agent /bin/bash

shell-phoenix: ## Login to the Phoenix container shell
	@echo "$(BLUE)Login to Shell Phoenix...$(RESET)"
	@docker-compose -f $(PHOENIX_COMPOSE_FILE) exec phoenix /bin/bash

install: ## Install dependencies locally
	@echo "$(BLUE)Installing dependencies...$(RESET)"
	@pip install -r requirements.txt
	@echo "$(GREEN)✅ Dependencies are installed$(RESET)"

env: ## Create an environment file from the example
	@echo "$(BLUE)Creating an .env file...$(RESET)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✅ .env file created from .env.example$(RESET)"; \
		echo "$(YELLOW)⚠️  Edit .env file with your settings$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️  .env the file already exists$(RESET)"; \
	fi

# Information
info: ## Show project information
	@echo "$(GREEN)🤖 AI Agent Template$(RESET)"
	@echo "$(BLUE)════════════════════════════════════════$(RESET)"
	@echo "$(YELLOW)Project:$(RESET) AI Agent with Phoenix monitoring"
	@echo "$(YELLOW)Version:$(RESET) 0.1.0"
	@echo "$(YELLOW)Main ports:$(RESET)"
	@echo "  • Agent: http://localhost:10002"
	@echo "  • Phoenix: http://localhost:6006"
	@echo "$(YELLOW)Docker Compose files:$(RESET)"
	@echo "  • $(COMPOSE_FILE) - basic services"
	@echo "  • $(PHOENIX_COMPOSE_FILE) - with Phoenix monitoring"
	@echo "$(BLUE)════════════════════════════════════════$(RESET)"

# Health check
health: ## Check the health of services
	@echo "$(BLUE)Checking the health of services...$(RESET)"
	@echo "$(YELLOW)Agent:$(RESET)"
	@curl -s http://localhost:10002/health 2>/dev/null || echo "$(RED)❌ Agent unavailable$(RESET)"
	@echo "$(YELLOW)Phoenix:$(RESET)"
	@curl -s http://localhost:6006/health 2>/dev/null || echo "$(RED)❌ Phoenix unavailable$(RESET)"

# Backup
backup: ## Create a backup copy of your data
	@echo "$(BLUE)Creating a backup copy...$(RESET)"
	@mkdir -p backups
	@docker run --rm -v $(PROJECT_NAME)_phoenix_data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/phoenix_data_$(shell date +%Y%m%d_%H%M%S).tar.gz -C /data .
	@echo "$(GREEN)✅ The backup copy was created in the folder backups/$(RESET)" 