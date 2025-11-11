# AI Agent Template

A modern template for creating AI agents based on Google ADK (Agent Development Kit) with support for MCP (Model Context Protocol) tools and Phoenix monitoring.

## 🚀 Peculiarities

- **Google ADK Integration** - Leverages the industry-leading SDK for agent development
- **MCP Tools Support** - Integration with the Model Context Protocol for extensible tools
- **LiteLLM** - Support for various LLM models through a single interface
- **Phoenix Monitoring** - Optional monitoring and execution tracing
- **Docker Ready** - Full containerization with automatic configuration
- **A2A Protocol** - Agent-to-Agent communication
- **CORS Support** - Ready for web integration
- **Flexible Configuration** - Configuration via environment variables

## 📁 Project structure

```
ai-agent-template/
├── app/                     # Main application code
│   ├── __main__.py         # Entry point with Click CLI
│   ├── agent.py            # AgentEvolution class
│   └── agent_executor.py   # Agent executor
├── docker-compose.yml      # Docker configuration
├── docker-compose.phoenix.yml  # Phoenix configuration
├── Dockerfile              # Container image
├── Makefile               # Command automation
├── scripts/               # Helper scripts
│   └── docker-setup.sh    # Automatic setup
├── nginx/                 # Nginx configuration
├── pyproject.toml         # Project configuration and dependencies
└── litellm-1.72.3-py3-none-any.whl  # LiteLLM wheel
```

## 🛠 Installation

### Getting Started with Docker (Recommended)

#### Optimized build for instant start

The image is configured to start as quickly as possible without package synchronization:

```bash
# Building an optimized image
docker-compose build

# Instant agent launch (< 1 second)
docker-compose up -d
```

#### Key optimizations:

1. **Pre-installed dependencies** - all dependencies are installed during the build process
2. **Frozen lockfile** - use `uv sync --frozen` to accurately replicate the environment
3. **Optimized layers** - correct order of COPY commands for maximum caching of Docker layers
4. **Direct Python execution** - run via `python -m app` instead of `uv run`

### Using Makefile

```bash
# View all available commands
make help

# Launching core services
make up

# Running with Phoenix monitoring
make phoenix

# Development mode
make dev

# View logs
make logs

# Stop all services
make down
```

### Manual installation

```bash
# Installing dependencies (requires uv)
uv sync

# Creating an environment file
cp .env.example .env

# Setting environment variables (see section below)
nano .env

# Launching the agent
uv run .
```

## ⚙️ Configuration

### Basic environment variables

```bash
# Basic agent settings
AGENT_NAME=ai-agent-template
AGENT_DESCRIPTION=AI Agent на базе Google ADK и MCP tools
AGENT_VERSION=0.1.0

# Configuration models
MODEL_NAME=your-model-name
MODEL_API_BASE=https://your-api-endpoint/v1

# MCP Tools
MCP_URL=http://localhost:8001/sse

# Server settings
HOST=0.0.0.0
PORT=10002

# Phoenix monitoring (optional)
ENABLE_PHOENIX=false
PHOENIX_PROJECT_NAME=ai-agent-template
PHOENIX_ENDPOINT=http://localhost:6006/v1/traces

# System prompt
AGENT_SYSTEM_PROMPT=You are a modern AI agent with advanced capabilities. Use the available tools to effectively complete user tasks.

# Message during processing
PROCESSING_MESSAGE=🤖 Processing your request...
```

### Example of minimal configuration

```bash
AGENT_NAME=my-ai-agent
MODEL_NAME=gpt-4
MODEL_API_BASE=https://api.openai.com/v1
MCP_URL=http://localhost:8001/sse
```

## 🚀 Usage

### Via Docker

```bash
# Launching core services
make up

# The agent will be available on http://localhost:10002
```

### Development Mode

```bash
# Run in development mode with live reload
make dev

# Run with Phoenix monitoring for debugging
make dev-phoenix
```

### Checking Status

```bash
# Status of all services
make status

# Health Check
make health

# Viewing Logs
make logs
```

## 🔧 Architecture

### Main Components

- **AgentEvolution** - Main agent class with LLM integration
- **EvolutionAgentExecutor** - Agent request executor
- **A2AStarletteApplication** - Starlette-based HTTP server
- **MCPToolset** - MCP toolkit
- **LiteLLM** - Abstraction for working with various LLMs

### Supported Formats

- **Input Data**: `text`, `text/plain`
- **Output Data**: `text`, `text/plain`
- **Protocols**: A2A (Agent-to-Agent), HTTP REST, SSE (Server-Sent Events)

## 📊 Monitoring

### Phoenix Tracing

To enable Phoenix monitoring:

```bash
# Set the environment variable
ENABLE_PHOENIX=true

# Run with Phoenix
make phoenix

# Phoenix Dashboard will be available at http://localhost:6006
```

### Logging

Logs are saved to:
- Standard output (Docker logs)
- `agent_monitoring.log` (for simple monitoring)

## 🧪 Testing

```bash
# Running tests
make test

# Testing MCP tracing
make test-mcp
```

## 🛠 Development

### Local Development

```bash
# Installing Dependencies
uv sync

# Creating a .env file
make env

# Running in Development Mode
uv run . --host localhost --port 10002
```

### Adding New Tools

1. Configure the MCP server with the required tools
2. Update `MCP_URL` in the configuration
3. The tools will be automatically connected via MCPToolset

### Customizing the Agent

The main agent logic is located in `app/agent.py`. You can:
- Change the system prompt
- Add additional tools
- Configure the LLM model
- Change the request processing logic

## 🐳 Docker teams

```bash
# Basic commands
make build          # Build images
make up            # Start services
make down          # Stop services
make restart       # Restart
make logs          # View logs

# Phoenix monitoring
make phoenix       # Start with monitoring
make phoenix-down  # Stop Phoenix

# Утилиты
make shell         # Log into the agent container
make clean         # Clean up Docker resources
make backup        # Back up data
```

## 🌐 API Endpoints

- `GET /` - Agent Card information
- `POST /tasks` - Create a new task
- `GET /tasks/{task_id}` - Get task status
- `GET /tasks/{task_id}/stream` - SSE task execution stream

## 📋 Требования

- **Python**: 3.12+
- **Docker**: For containerization
- **uv**: For dependency management
- **MCP Server**: For tools (optional)

## 🤝 Contribute to Development

1. Fork the repository
2. Create a branch for the feature (`git checkout -b feature/AmazingFeature`)
3. Commit the changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is distributed under the MIT license. See the `LICENSE` file for details.

## 🆘 Support

- Create an Issue to report bugs
- See the Google ADK documentation
- Check the service status with `make status`
- View logs with `make logs`

## 🔗 Полезные ссылки

- [Google ADK Documentation](https://developers.google.com/adk)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [LiteLLM Documentation](https://docs.litellm.ai/)
- [Phoenix Tracing](https://phoenix.arize.com/)

## 🛠 Technical details

### Dockerfile optimizations:

```dockerfile
# Install ALL dependencies during the build process
RUN uv sync --frozen --no-dev && \
    uv add ./litellm-1.72.3-py3-none-any.whl

# Copy the code AFTER installing the dependencies
COPY app ./app

# Direct launch without UV run
CMD ["python", "-m", app"]
```

### Fixed issues:

✅ **Queue is closed** - Improved event queue processing logic
✅ **RuntimeWarning: coroutine 'wait_for' was never awaited** - Fixed asyncio.timeout usage
✅ **No final response from agent** - Added content validation before task completion
✅ **Import errors** - Fixed relative imports in modules

### Startup time:

- **Before optimization**: 30-60 seconds (with package synchronization)
- **After optimization**: < 1 second (built image)

## 📦 Usage

### Starting the agent:

```bash
# Running
docker-compose up -d

# Viewing logs
docker-compose logs -f

# Stopping
docker-compose down
```

### Checking operation:

```bash
# Checking status
curl http://localhost:10002/health

# Viewing startup logs
docker logs evolution-agent
```

## 🐛 Debugging

If you have problems starting:

```bash
# Checking the image
docker run --rm -it --entrypoint /bin/bash ai-agent-template-evolution-agent

# Testing imports
docker run --rm ai-agent-template-evolution-agent python -c "from app import AgentEvolution; print('✅ OK')"

# Viewing detailed logs
docker-compose logs evolution-agent --details
``` 