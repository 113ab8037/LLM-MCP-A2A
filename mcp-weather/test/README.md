# MCP Weather Server Tests

This folder contains all tests for the MCP weather server with Open-Meteo API integration.

## Test Structure

```
test/
├── test_weather_api.py     # Unit tests with mocks (fast)
├── test_integration.py     # Integration tests (with a real API)
├── test_tools.py          # Demo tests
├── run_tests.py           # Script for running tests
├── TESTING.md             # Detailed documentation
└── README.md              # This file
```

## Quick Start

### Via Makefile (recommended)
```bash
# Install dependencies
make install

# Run main tests
make test

# Run all tests with coverage
make test-cov

# Show all commands
make help
```

### Via uv directly
```bash
# Unit tests (fast)
uv run pytest test/test_weather_api.py -v

# Integration tests (slow, require internet)
uv run pytest test/test_integration.py -v -m integration

# All tests
uv run pytest test/ -v
```

## Test Types

- **Unit Tests** (`test_weather_api.py`) - quick tests with mocks, for development
- **Integration Tests** (`test_integration.py`) - with a real API, for testing
- **Demo Tests** (`test_tools.py`) - interactive, for demonstration

Detailed documentation in the `TESTING.md` file. 