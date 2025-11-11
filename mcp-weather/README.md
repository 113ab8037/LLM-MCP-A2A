# 🌤️ MCP Weather Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.0-green.svg)](https://github.com/jlowin/fastmcp)
[![Free API](https://img.shields.io/badge/API-Free-brightgreen.svg)](https://open-meteo.com/)

An MCP server for receiving weather data using the Open-Meteo API. **Completely free, no API keys required!** 🎉

## 🚀 Features

- **🌍 Today's Weather** - current weather for any city in the world
- **📅 Weekly Forecast** - detailed weekly forecast
- **🔄 Real Data** - Open-Meteo API without API keys
- **🌐 Multilingual** - supports cities with any name
- **⚡ Fast and Reliable** - FastMCP 2.0 framework

## 📦 Installation

```bash
# Clone the repository
cd mcp-weather

# Install dependencies
uv sync

# Start the server
uv run python server.py
```

## 🛠️ Available tools

### `get_today_weather(city: str)`
Gets the current weather for today for the specified city.

```python
# Usage examples
await get_today_weather("Москва")
await get_today_weather("Paris") 
await get_today_weather("New York")
await get_today_weather("東京")
```

### `get_weekly_forecast(city: str)`
Gets the weekly weather forecast for the specified city.

```python
# Usage examples
await get_weekly_forecast("London")
await get_weekly_forecast("Berlin")
await get_weekly_forecast("São Paulo")
```

## 🧪 Testing

The project includes a full set of tests:

```bash
# All tests
make test-all

# Unit tests (fast, with mocks)
make test-unit

# Integration tests (with real API)
make test-integration

# Demo tests
make test-demo

# Code coverage tests
make test-cov
```

## 🐳 Docker

```bash
# Assembly and launch
docker-compose up --build

# Assembly only
docker build -t mcp-weather .

# Launch container
docker run -p 8001:8001 mcp-weather
```

## 🌐 Endpoints

- **SSE**: `http://localhost:8001/sse`
- **Messages**: `http://localhost:8001/messages/`

## 📊 Test Coverage

- **Unit Tests**: 17 tests
- **Integration Tests**: 7 tests
- **Demo Tests**: 6 functions
- **Overall Coverage**: 87%

## 🏗️ Architecture

- **FastMCP 2.0** - MCP framework
- **httpx** - HTTP client
- **Open-Meteo API** - weather data
- **pytest** - testing
- **uv** - dependency management

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributions

We welcome any improvements!

1. **Fork** the project
2. Create a **feature branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit** the changes (`git commit -m 'Add some AmazingFeature'`)
4. **Push** to the branch (`git push origin feature/AmazingFeature`)
5. Open a **Pull Request**

## 🆘 Support

- 📫 **Issues**: [GitHub Issues](https://github.com/your-username/simple_mcp_server/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/your-username/simple_mcp_server/discussions)

## 🎉 Thanks

- [FastMCP](https://github.com/jlowin/fastmcp) - excellent MCP framework
- [Open-Meteo](https://open-meteo.com/) - Free weather API

---

⭐ **Did you like the project? Give it a star!** ⭐