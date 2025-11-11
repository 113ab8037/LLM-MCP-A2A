# Router Agent

A system for routing requests between AI agents with support for dynamic management via the REST API.

## 🚀 Features

- **Unified server**: A2A protocol and agent management on a single port
- **Three operating modes**: A2A server, FastAPI REST API, or combined mode
- **Dynamic agent management**: add/remove agents without restarting
- **Detailed logging**: full tracking of requests with emoji markers
- **History limitation**: automatic dialog context management
- **Containerization**: ready-to-use Docker images and docker-compose
- **Modern stack**: Python 3.13, uv, FastAPI, Google ADK

## 📋 Requirements

- Python 3.13+
- uv (recommended) or pip
- Docker and Docker Compose (for containerized running)

## 🛠 Installation

### Local installation

```bash
# Cloning a repository
git clone <repository-url>
cd router

# Installing dependencies via uv
uv sync

# Or via pip
pip install -r requirements.txt
```

### Docker установка

```bash
# Image assembly
docker build -t router-agent .

# Or using docker-compose
docker-compose up --build
```

## 🎯 Quick Start

### 1. Combined Server (recommended)

```bash
# Easy Start
./run.sh unified

# With settings
./run.sh unified --host 0.0.0.0 --port 10000 --remote-agents "http://agent1:10001"

# Via Python
python start_server.py unified
```

**Available endpoints:**
- A2A protocol: http://localhost:10000/ (all standard paths)
- Agent management: http://localhost:10000/mgm/agents
- Agent list: `GET /mgm/agents`
- Add agent: `POST /mgm/agents`
- Delete agent: `DELETE /mgm/agents/{name}`

### 2. FastAPI server (legacy)

```bash
# With settings
./run.sh fastapi --host 0.0.0.0 --port 8000 --reload

# Через Python
python start_server.py fastapi
```

**Available endpoints:**
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Agent management: http://localhost:8000/agents

### 3. A2A server (legacy)

```bash
# Starting with agents
./run.sh a2a --remote-agents "http://localhost:10001,http://localhost:10002"

# Via Python
python start_server.py a2a --remote-agents "http://agent1:10001"
```

### 4. Both servers simultaneously (DEPRECATED)

```bash
./run.sh both
```

## 🔧 Managing agents

### Combined server (recommended)

#### Viewing the list of agents

```bash
curl http://localhost:10000/mgm/agents
```

#### Adding an agent

```bash
curl -X POST http://localhost:10000/mgm/agents \
  -H "Content-Type: application/json" \
  -d '{"address": "http://weather-service:10001"}'
```

#### Removing the agent

```bash
curl -X DELETE http://localhost:10000/mgm/agents/weather_agent
```

### Legacy FastAPI server

#### View list of agents

```bash
curl http://localhost:8000/agents
```

**Answer:**
```json
[
  {
    "name": "weather_agent",
    "description": "Provides weather information"
  }
]
```

#### Adding an agent

```bash
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{"address": "http://weather-service:10001"}'
```

**Answer:**
```json
{
  "message": "Agent added",
  "name": "weather_agent"
}
```

#### Removing an agent

```bash
curl -X DELETE http://localhost:8000/agents/weather_agent
```

**Answer:**
```json
{
  "message": "Agent removed",
  "name": "weather_agent"
}
```

## ⚙️ Configuration

### Environment variables

Создайте файл `.env`:

```env
# LLM настройки
LLM_MODEL=evolution_inference/model-run-8ivnt-fence
LLM_API_BASE=https://your-llm-endpoint.com/v1

# Управление историей диалога
HISTORY_LENGTH=3

# Сетевые настройки
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
A2A_HOST=localhost
A2A_PORT=10000

# Логирование
LOG_LEVEL=INFO

# REMOTE_AGENT
REMOTE_AGENT=http://localhost:10002,http://localhost:10003
```

### Configuration via docker-compose

```yaml
environment:
  - LLM_MODEL=your-model
  - LLM_API_BASE=https://your-endpoint.com/v1
  - HISTORY_LENGTH=5
```

## 🐳 Docker

### Dockerfile

The project uses multi-stage UV assembly to optimize image size:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.13-slim AS builder
# ... сборка зависимостей

FROM python:3.13-slim AS runtime
# ... финальный образ
```

### Docker Compose

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f router-agent

# Остановка
docker-compose down
```

**Доступные сервисы:**
- `router-agent`: FastAPI сервер на порту 8000
- `router-a2a`: A2A сервер на порту 10000

## 📊 Мониторинг и логирование

### Структура логов

Все компоненты используют emoji-маркеры для визуальной идентификации:

- 🚀 Запуск сервисов
- 🔄 HTTP запросы/ответы
- 📥📤 Входящие/исходящие данные
- 🤖 Операции с агентами
- 🔗 Сетевые соединения
- 📚 Управление историей
- ✅❌ Успех/ошибки

### Пример логов

```
2025-01-16 10:30:15 - INFO - 🚀 Starting FastAPI Server...
2025-01-16 10:30:16 - INFO - ✅ Added remote agent 'weather_agent' (http://weather:10001)
2025-01-16 10:30:20 - INFO - 🔄 INCOMING REQUEST - POST /agents
2025-01-16 10:30:21 - INFO - 📚 History management - Total turns: 5, Keep turns: 3
```

### Checking the status

```bash
# Via script
./run.sh status

# Via API
curl http://localhost:8000/agents

# Via Docker
docker-compose ps
```

## 🏗 Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   A2A Server    │
│   Server        │    │   (Original)    │
│   :8000         │    │   :10000        │
└─────────────────┘    └─────────────────┘
         │                       │
         └───────────┬───────────┘
                     │
         ┌─────────────────┐
         │   HostAgent     │
         │   (Shared)      │
         └─────────────────┘
                     │
         ┌─────────────────┐
         │ Remote Agents   │
         │ :10001, :10002  │
         └─────────────────┘
```

### Components

- **FastAPI Server**: REST API for agent management
- **A2A Server**: Compatibility with the A2A protocol
- **HostAgent**: Central router with a shared agent registry
- **RouterAgent**: Request processing via Google ADK
- **RemoteAgentConnection**: Clients for communicating with remote agents

## 🔍 Debugging

### Common Issues

1. **Agent not found**
   ```
   ValueError: Agent weather_agent not found
   ```
   - Check the list of agents: `curl http://localhost:8000/agents`
   - Make sure the agent was added via the API

2. **Connection timeout**
```
HTTP Error 503: Network communication error
```
- Check the remote agent's availability
- Increase the timeout in `remote_agent_connection.py`

3. **Port busy**
```
OSError: [Errno 48] Address already in use
```
- Check: `lsof -i :8000`
- Change the port: `--port 8001`

### Debug logs

```bash
# Detailed logs
export LOG_LEVEL=DEBUG
./run.sh fastapi

# Container-specific logs
docker-compose logs -f router-agent

# Real-time logs
tail -f server.log
```

## 🧪 Testing

### Manual Testing

```bash
# Adding a Test Agent
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{"address": "http://localhost:10001"}'

# Sending a test request
curl -X POST http://localhost:10000/send-message \
  -H "Content-Type: application/json" \
  -d '{"message": "Привет, как дела?"}'
```

### Automated tests

```bash
# Run tests (if any)
python -m pytest tests/

# Check the linter
flake8 *.py

# Type checking
mypy *.py
```

## 📚 API Reference

### FastAPI Endpoints

#### GET /agents
Get a list of registered agents.

**Ответ:**
```json
[
  {
    "name": "string",
    "description": "string"
  }
]
```

#### POST /agents
Add a new agent.
**Request:**
```json
{
  "address": "http://agent-url:port"
}
```

**Answer:**
```json
{
  "message": "Agent added",
  "name": "agent_name"
}
```

#### DELETE /agents/{agent_name}
Remove agent by name.

**Answer:**
```json
{
  "message": "Agent removed",
  "name": "agent_name"
}
```

## 🤝 Development

### Project Structure

```
router/
├── agent_executor.py      # Agent executor
├── host_agent.py         # Central router
├── router_agent.py       # Request handler
├── remote_agent_connection.py  # Remote agent clients
├── fastapi_host_server.py # FastAPI server
├── main.py              # A2A server
├── start_server.py      # Unified launch
├── run.sh              # Quickstart script
├── Dockerfile          # Docker image
├── docker-compose.yml  # Container orchestration
├── pyproject.toml      # UV configuration
└── requirements.txt    # pip dependencies
```

### Adding new features

1. Create a branch: `git checkout -b feature/new-feature`
2. Make changes
3. Add tests
4. Update documentation
5. Create a pull request

## 📄 License

MIT License - see the LICENSE file for details.

## 🆘 Support

- Create a GitHub Issue for bugs
- Contact the developers with questions
- Check the logs with emoji markers for diagnostics

## Environment Variables

### REMOTE_AGENT
You can specify remote agent addresses using the `REMOTE_AGENT` environment variable. Addresses must be separated by commas:

```bash
export REMOTE_AGENT="http://localhost:10002,http://localhost:10003"
```

Or in a file `.env`:
```
REMOTE_AGENT=http://localhost:10002,http://localhost:10003
```

This variable will be used automatically if agents are not specified via the `--remote-agents` command-line options in the `a2a` and `unified` commands.

### Usage example

```bash
# Set environment variable
export REMOTE_AGENT="http://localhost:10002,http://localhost:10003"

# Start the unified server (will automatically load agents from the environment variable)
python -m app.start_server unified --host 0.0.0.0 --port 10000

# Or start an A2A server
python -m app.start_server a2a --host localhost --port 10000
```
