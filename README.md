# AI Agent Project with Google ADK, A2A Protocol, and MCP Integration

This project is an implementation of an AI agent with Google ADK (Agent Development Kit) integration, supporting the A2A (Agent-to-Agent) protocol for interacting with other agents and extensible via MCP (Model Context Protocol) servers. The project includes a ready-to-use infrastructure for developing, testing, and deploying AI agents with monitoring and tracing.

Detailed documentation on the A2A protocol: [documentation](./documentation-a2a-russian.md) and [Postman-collection](./postman-collection-a2a-spec.json)

## 🎯 Features

- **Google ADK Integration** - Uses an industry-leading SDK for agent development
- **MCP Tools Support** - Integration with the Model Context Protocol for extensible tools
- **LiteLLM** - Support for various LLM models through a single interface
- **Phoenix Monitoring** - Optional monitoring and execution tracing
- **Docker Ready** - Full containerization with automatic configuration
- **A2A Protocol** - Agent-to-Agent communication
- **Flexible Configuration** - Configuration via environment variables

## 📁 Structure Project

```
a2a-adk-mcp-example/
├── agent/ # Agent directory
│ ├── app/ # Main application code
│ │ ├── __main__.py # Click CLI entry point
│ │ ├── agent.py # AgentEvolution class
│ │ └── agent_executor.py # Agent executor
│ ├── .env.example # Sample configuration file
│ ├── pyproject.toml # Project configuration and dependencies
│ └── README.md # Agent documentation
├── mcp-weather/ # MCP Weather Server
│ ├── server.py # Main server
│ ├── Dockerfile # Docker configuration
│ └── README.md # MCP Server Documentation
├── nginx/ # Nginx configuration
├── docker-compose.phoenix.yml # Phoenix configuration
├── docker-compose.yml # Main Docker Compose configuration
├── Makefile # Command automation
└── .gitignore # Ignored files
```

## 🛠 Installation and Quick Start

### Docker Quick Start (recommended)

```bash
# Building images
make build

# Starting basic services
make up

# The agent will be available at http://localhost:10002
# The MCP server will be available at http://localhost:8001
```

### Using Makefile

```bash
# Viewing all available commands
make help

# Starting basic services
make up

# Running with Phoenix monitoring
make phoenix

# Development mode
make dev

# Viewing logs
make logs

# Stopping all services
make down
```

## ⚙️ Configuration

### Creating an environment file

```bash
# Creating a .env file from the example
make env

# Or manually
cp agent/.env.example .env
```

### Basic environment variables

The following parameters can be configured in the `.env` file:

```bash
# Basic settings Agent
AGENT_NAME=jira_mcp_agent
AGENT_DESCRIPTION="Jira MCP agent for managing projects, tasks, sprints, and agile processes"
AGENT_VERSION=1.0.0

# Model Configuration
LLM_MODEL="evolution_inference/model-for-agent-space-test"
LLM_API_BASE="https://your-model-api-base-url/v1"

# MCP Configuration
MCP_URL=http://mcp-weather:8001/sse

# Phoenix Monitoring (optional)
PHOENIX_PROJECT_NAME="ip_agent_adk"
PHOENIX_ENDPOINT="http://phoenix:6006/v1/traces"

# Server Settings
HOST="0.0.0.0"
PORT="10002"

# Monitoring
ENABLE_PHOENIX="false"
ENABLE_MONITORING="true"
```

## 🚀 Usage

### Starting the agent

```bash
# Starting the main services
make up

# The agent will be available at http://localhost:10002
```

### Development mode

```bash
# Running in development mode with live reload
make dev

# Running with Phoenix monitoring for debugging
make dev-phoenix
```

### Checking status

```bash
# Status of all services
make status

# Health check
make health

# Viewing logs
make logs
```
## 🧩 Project Components

### Agent (agent/)

The main component of the project is an AI agent based on Google ADK with support for MCP tools. The agent implements the A2A Protocol for interacting with other agents.

#### API Endpoints

- `GET /` - Agent Information (Agent Card)
- `POST /tasks` - Create a new task
- `GET /tasks/{task_id}` - Get task status
- `GET /tasks/{task_id}/stream` - SSE task execution stream

### MCP Weather Server (mcp-weather/)

The server provides tools for retrieving weather data via the MCP protocol. It uses the free Open-Meteo API.

#### Tools

- `get_today_weather(city: str)` - Gets today's current weather for the specified city
- `get_weekly_forecast(city: str)` - Gets the weekly weather forecast for the specified city

#### Endpoints

- **SSE**: `http://localhost:8001/sse`
- **Messages**: `http://localhost:8001/messages/`

## 📊 Monitoring

### Phoenix Tracing

To enable Phoenix monitoring, set the environment variable:

```bash
ENABLE_PHOENIX=true
```

Run with Phoenix:

```bash
make phoenix
```

Phoenix Dashboard will be available at http://localhost:6006

## 🐳 Docker Commands

```bash
# Basic Commands
make build # Build images
make up # Start services
make down # Stop services
make restart # Restart
make logs # View logs

# Phoenix Monitoring
make phoenix # Start with monitoring
make phoenix-down # Stop Phoenix

# Utilities
make shell # Enter the agent container
make clean # Clean up Docker resources
```

## 📋 Requirements

- **Docker**: For containerization
- **Make**: For command automation
- **MCP Server**: For tools (optional)

## 📄 License

This project is distributed under the MIT license. See the `LICENSE` file for details (if present).

## 🔗 Useful links

- [Google ADK Documentation](https://developers.google.com/adk)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [LiteLLM Documentation](https://docs.litellm.ai/)
- [Phoenix Tracing](https://phoenix.arize.com/)