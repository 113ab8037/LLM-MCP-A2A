# Dockerfile for Router Agent - Optimized for size
# Multi-stage build using uv for efficient dependency management

# Stage 1: Build dependencies with uv
FROM python:3.13-slim AS builder

# Install uv and set cache directory
ENV UV_CACHE_DIR=/tmp/uv-cache
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock litellm-1.72.3-py3-none-any.whl ./

# Install dependencies and clean up in single layer
RUN uv sync --frozen --no-cache && \
    find /app/.venv -name "*.pyc" -delete && \
    find /app/.venv -name "__pycache__" -type d -exec rm -rf {} + && \
    rm -rf /tmp/uv-cache

# Stage 2: Runtime image
FROM python:3.13-slim AS runtime

# Install minimal system dependencies in single layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates && \
    pip install --no-cache-dir uv && \
    apt-get purge -y --auto-remove && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    apt-get clean

# Create user and directories in single layer
RUN groupadd -r router && \
    useradd -r -g router router -m && \
    mkdir -p /app/logs /home/router/.cache && \
    chown -R router:router /app /home/router

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv ./.venv

# Copy application code efficiently
COPY --chown=router:router app/ ./app/

# Switch to non-root user
USER router

# Environment variables
ENV PYTHONPATH="/app" \
    PYTHONUNBUFFERED="1" \
    UV_PROJECT_ENVIRONMENT="/app/.venv" \
    UV_CACHE_DIR="/home/router/.cache/uv" \
    UV_NO_SYNC="1" \
    PYTHONDONTWRITEBYTECODE="1"

# Expose ports
EXPOSE 8000 10000

# Health check 
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/agents || curl -f http://localhost:10000/agents || exit 1

# Default command
CMD ["uv", "run", "python", "-m", "app.start_server", "unified"]

# Labels for metadata
LABEL maintainer="Router Agent Team" \
      version="1.2.0" \
      description="AI Agent Router - Optimized" 