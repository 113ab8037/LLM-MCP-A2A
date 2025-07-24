#!/bin/bash

# Router Agent Quick Start Script

set -e

echo "🚀 Router Agent Quick Start"
echo "=========================="

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run 'uv sync' first."
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check command line argument
case "${1:-unified}" in
    "unified")
        echo "🔧 Starting Unified Server (A2A + Management on single port)..."
        echo "📍 A2A Protocol: http://localhost:10000/"
        echo "📚 Management API: http://localhost:10000/mgm/agents"
        python -m app.start_server unified --host 0.0.0.0 --port 10000
        ;;
    "fastapi")
        echo "🔧 [LEGACY] Starting FastAPI Server with dynamic agent management..."
        echo "📚 API Documentation will be available at: http://0.0.0.0:8000/docs"
        python -m app.start_server fastapi --host 0.0.0.0 --port 8000
        ;;
    "a2a")
        echo "🌐 [LEGACY] Starting A2A Server (original implementation)..."
        python -m app.start_server a2a --host localhost --port 10000
        ;;
    "both")
        echo "🚀 [DEPRECATED] Starting BOTH servers..."
        echo "📍 A2A Server: http://localhost:10000"
        echo "📍 FastAPI Server: http://0.0.0.0:8000"
        python -m app.start_server both
        ;;
    "status")
        echo "🔍 Checking server status..."
        python -m app.start_server status
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [unified|fastapi|a2a|both|status]"
        echo ""
        echo "Commands:"
        echo "  unified  - Start unified server (default, recommended)"
        echo "  fastapi  - Start FastAPI server (legacy)"
        echo "  a2a      - Start A2A server (legacy)"
        echo "  both     - Start both servers (deprecated)"
        echo "  status   - Check server status"
        echo "  help     - Show this help"
        echo ""
        echo "Examples:"
        echo "  $0                # Start unified server"
        echo "  $0 unified        # Start unified server"
        echo "  $0 fastapi        # Start FastAPI server (legacy)"
        echo "  $0 a2a            # Start A2A server (legacy)"
        echo "  $0 both           # Start both servers (deprecated)"
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac 