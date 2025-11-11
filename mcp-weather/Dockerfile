# We use the official Python 3.13 slim image for minimal size.
FROM python:3.13-slim

# Set the working directory
WORKDIR /app

# We install system dependencies and UV in one layer for optimization
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Copy uv configuration files first for better caching of Docker layers
COPY pyproject.toml ./

# Create a virtual environment and install dependencies
# Use the same approach as locally
RUN uv sync --no-editable

# Copy the application's source code
COPY server.py README.md ./
COPY test/ ./test/

# Create an unprivileged user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 mcp && \
    chown -R mcp:mcp /app

# Switch to an unprivileged user
USER mcp

# Open the port for the MCP server
EXPOSE 8001

# Set environment variables for optimal Python operation
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    UV_SYSTEM_PYTHON=1

# Health check to monitor server status
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/sse/ || exit 1

# Server startup command - exactly the same as locally
CMD ["uv", "run", "python", "server.py"] 