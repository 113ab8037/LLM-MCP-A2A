# AI Agent Template Makefile
# Команды для управления Docker Compose конфигурациями

.PHONY: help build up down restart logs clean test dev phoenix phoenix-up phoenix-down agent-up agent-down network

# Цвета для вывода
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
BLUE := \033[34m
RESET := \033[0m

# Переменные
COMPOSE_FILE := docker-compose.yml
PHOENIX_COMPOSE_FILE := docker-compose.phoenix.yml
PROJECT_NAME := ai-agent-template
NETWORK_NAME := agent-network

# Помощь
help: ## Показать это сообщение помощи
	@echo "$(GREEN)AI Agent Template - Makefile команды$(RESET)"
	@echo ""
	@echo "$(BLUE)Основные команды:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Примеры использования:$(RESET)"
	@echo "  make up          # Запустить основные сервисы"
	@echo "  make phoenix     # Запустить с Phoenix мониторингом"
	@echo "  make dev         # Режим разработки"
	@echo "  make logs        # Посмотреть логи"
	@echo "  make clean       # Очистить все"

# Создание сети Docker
network: ## Создать Docker сеть
	@echo "$(BLUE)Создание Docker сети...$(RESET)"
	@docker network create $(NETWORK_NAME) 2>/dev/null || echo "$(YELLOW)Сеть $(NETWORK_NAME) уже существует$(RESET)"

# Основные команды
build: network ## Собрать Docker образы
	@echo "$(BLUE)Сборка Docker образов...$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) build

up: network ## Запустить основные сервисы
	@echo "$(GREEN)Запуск основных сервисов...$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN)✅ Сервисы запущены!$(RESET)"
	@echo "$(YELLOW)Агент доступен на: http://localhost:10002$(RESET)"

down: ## Остановить все сервисы
	@echo "$(RED)Остановка сервисов...$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) down 2>/dev/null || true
	@docker-compose -f $(PHOENIX_COMPOSE_FILE) down 2>/dev/null || true
	@echo "$(GREEN)✅ Сервисы остановлены$(RESET)"

restart: down up ## Перезапустить сервисы

# Phoenix мониторинг
phoenix: phoenix-up ## Запустить с Phoenix мониторингом (алиас)

phoenix-up: network ## Запустить сервисы с Phoenix мониторингом
	@echo "$(GREEN)Запуск сервисов с Phoenix мониторингом...$(RESET)"
	@docker-compose -f $(PHOENIX_COMPOSE_FILE) up -d
	@echo "$(GREEN)✅ Сервисы с Phoenix запущены!$(RESET)"
	@echo "$(YELLOW)Агент доступен на: http://localhost:10002$(RESET)"
	@echo "$(YELLOW)Phoenix Dashboard: http://localhost:6006$(RESET)"

phoenix-down: ## Остановить Phoenix сервисы
	@echo "$(RED)Остановка Phoenix сервисов...$(RESET)"
	@docker-compose -f $(PHOENIX_COMPOSE_FILE) down
	@echo "$(GREEN)✅ Phoenix сервисы остановлены$(RESET)"

phoenix-restart: phoenix-down phoenix-up ## Перезапустить Phoenix сервисы

# Отдельный запуск агента
agent-up: network ## Запустить только агент
	@echo "$(GREEN)Запуск агента...$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) up -d evolution-agent
	@echo "$(GREEN)✅ Агент запущен на http://localhost:10002$(RESET)"

agent-down: ## Остановить только агент
	@echo "$(RED)Остановка агента...$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) stop evolution-agent
	@echo "$(GREEN)✅ Агент остановлен$(RESET)"

# Логи и мониторинг
logs: ## Показать логи всех сервисов
	@echo "$(BLUE)Логи сервисов:$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) logs -f --tail=100

logs-agent: ## Показать логи только агента
	@echo "$(BLUE)Логи агента:$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) logs -f --tail=100 evolution-agent

logs-phoenix: ## Показать логи Phoenix сервисов
	@echo "$(BLUE)Логи Phoenix:$(RESET)"
	@docker-compose -f $(PHOENIX_COMPOSE_FILE) logs -f --tail=100

status: ## Показать статус сервисов
	@echo "$(BLUE)Статус основных сервисов:$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) ps
	@echo ""
	@echo "$(BLUE)Статус Phoenix сервисов:$(RESET)"
	@docker-compose -f $(PHOENIX_COMPOSE_FILE) ps 2>/dev/null || echo "$(YELLOW)Phoenix сервисы не запущены$(RESET)"

# Разработка
dev: network ## Режим разработки (с автоперезагрузкой)
	@echo "$(GREEN)Запуск в режиме разработки...$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) up --build
	@echo "$(YELLOW)Для выхода нажмите Ctrl+C$(RESET)"

dev-phoenix: network ## Режим разработки с Phoenix
	@echo "$(GREEN)Запуск в режиме разработки с Phoenix...$(RESET)"
	@docker-compose -f $(PHOENIX_COMPOSE_FILE) up --build
	@echo "$(YELLOW)Phoenix Dashboard: http://localhost:6006$(RESET)"
	@echo "$(YELLOW)Для выхода нажмите Ctrl+C$(RESET)"

# Тестирование
test: ## Запустить тесты
	@echo "$(BLUE)Запуск тестов...$(RESET)"
	@docker run --rm -v $(PWD):/app -w /app python:3.12 bash -c "\
		pip install -r requirements.txt && \
		python -m pytest tests/ -v"

test-mcp: phoenix-up ## Тестировать MCP трейсинг
	@echo "$(BLUE)Тестирование MCP трейсинга...$(RESET)"
	@sleep 5  # Ждем запуска сервисов
	@python test_mcp_tracing.py
	@echo "$(YELLOW)Проверьте Phoenix Dashboard: http://localhost:6006$(RESET)"

# Очистка
clean: down ## Очистить контейнеры и образы
	@echo "$(RED)Очистка Docker ресурсов...$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) down --rmi all --volumes --remove-orphans 2>/dev/null || true
	@docker-compose -f $(PHOENIX_COMPOSE_FILE) down --rmi all --volumes --remove-orphans 2>/dev/null || true
	@echo "$(GREEN)✅ Очистка завершена$(RESET)"

clean-volumes: ## Удалить все volumes
	@echo "$(RED)Удаление volumes...$(RESET)"
	@docker volume prune -f
	@echo "$(GREEN)✅ Volumes удалены$(RESET)"

clean-all: clean clean-volumes ## Полная очистка
	@echo "$(RED)Полная очистка Docker системы...$(RESET)"
	@docker system prune -af
	@echo "$(GREEN)✅ Полная очистка завершена$(RESET)"

# Утилиты
shell: ## Войти в shell контейнера агента
	@echo "$(BLUE)Вход в shell агента...$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) exec evolution-agent /bin/bash

shell-phoenix: ## Войти в shell Phoenix контейнера
	@echo "$(BLUE)Вход в shell Phoenix...$(RESET)"
	@docker-compose -f $(PHOENIX_COMPOSE_FILE) exec phoenix /bin/bash

install: ## Установить зависимости локально
	@echo "$(BLUE)Установка зависимостей...$(RESET)"
	@pip install -r requirements.txt
	@echo "$(GREEN)✅ Зависимости установлены$(RESET)"

env: ## Создать файл окружения из примера
	@echo "$(BLUE)Создание .env файла...$(RESET)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✅ .env файл создан из .env.example$(RESET)"; \
		echo "$(YELLOW)⚠️  Отредактируйте .env файл с вашими настройками$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️  .env файл уже существует$(RESET)"; \
	fi

# Информация
info: ## Показать информацию о проекте
	@echo "$(GREEN)🤖 AI Agent Template$(RESET)"
	@echo "$(BLUE)════════════════════════════════════════$(RESET)"
	@echo "$(YELLOW)Проект:$(RESET) AI Agent с Phoenix мониторингом"
	@echo "$(YELLOW)Версия:$(RESET) 0.1.0"
	@echo "$(YELLOW)Основные порты:$(RESET)"
	@echo "  • Агент: http://localhost:10002"
	@echo "  • Phoenix: http://localhost:6006"
	@echo "$(YELLOW)Docker Compose файлы:$(RESET)"
	@echo "  • $(COMPOSE_FILE) - основные сервисы"
	@echo "  • $(PHOENIX_COMPOSE_FILE) - с Phoenix мониторингом"
	@echo "$(BLUE)════════════════════════════════════════$(RESET)"

# Проверка здоровья
health: ## Проверить здоровье сервисов
	@echo "$(BLUE)Проверка здоровья сервисов...$(RESET)"
	@echo "$(YELLOW)Агент:$(RESET)"
	@curl -s http://localhost:10002/health 2>/dev/null || echo "$(RED)❌ Агент недоступен$(RESET)"
	@echo "$(YELLOW)Phoenix:$(RESET)"
	@curl -s http://localhost:6006/health 2>/dev/null || echo "$(RED)❌ Phoenix недоступен$(RESET)"

# Резервное копирование
backup: ## Создать резервную копию данных
	@echo "$(BLUE)Создание резервной копии...$(RESET)"
	@mkdir -p backups
	@docker run --rm -v $(PROJECT_NAME)_phoenix_data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/phoenix_data_$(shell date +%Y%m%d_%H%M%S).tar.gz -C /data .
	@echo "$(GREEN)✅ Резервная копия создана в папке backups/$(RESET)" 