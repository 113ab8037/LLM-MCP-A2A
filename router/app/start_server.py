#!/usr/bin/env python3
"""
Unified startup script for Router Agent servers.

This script can start either:
1. A2A Server (original) - Compatible with A2A protocol
2. FastAPI Server (new) - With dynamic agent management via REST API
"""

import asyncio
import logging
import os

import click
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Router Agent Server Management"""
    pass


@cli.command()
@click.option('--host', default='localhost', help='Host to bind to')
@click.option('--port', default=10000, type=int, help='Port to bind to')
@click.option('--phoenix', default='http://localhost:6006/v1/traces', 
              help='Phoenix tracing endpoint')
@click.option('--remote-agents', default='', 
              help='Comma-separated list of remote agent URLs')
def a2a(host: str, port: int, phoenix: str, remote_agents: str):
    """Start the A2A-compatible server (original implementation)"""
    
    logger.info("🚀 Starting A2A Server...")
    logger.info(f"📍 Host: {host}:{port}")
    logger.info(f"🔍 Phoenix: {phoenix}")
    
    remote_agents = os.getenv("REMOTE_AGENTS")
    remote_agent_addresses = []
    if remote_agents:
        remote_agent_addresses = [addr.strip() for addr in remote_agents.split(',')]
        logger.info(f"🤖 Remote agents: {remote_agent_addresses}")
    elif not remote_agents:
        # Если не указаны в командной строке, пытаемся прочитать из переменной 
        # окружения
        remote_agent_env = os.getenv("REMOTE_AGENT", "")
        if remote_agent_env:
            remote_agent_addresses = [
                addr.strip() 
                for addr in remote_agent_env.split(',') 
                if addr.strip()
            ]
            logger.info(
                f"🌍 Loaded remote agents from environment: "
                f"{remote_agent_addresses}"
            )
    
    # Import and run the original main
    from .main import async_main
    asyncio.run(async_main(host, port, phoenix, remote_agent_addresses))


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8000, type=int, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
def fastapi(host: str, port: int, reload: bool):
    """Start the FastAPI server with dynamic agent management"""
    
    logger.info("🚀 Starting FastAPI Server...")
    logger.info(f"📍 Host: {host}:{port}")
    logger.info("🔧 Dynamic agent management enabled")
    logger.info(f"📚 API Documentation: http://{host}:{port}/docs")
    
    # Start FastAPI server
    uvicorn.run(
        "app.fastapi_host_server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=10000, type=int, help='Port to bind to')
@click.option('--remote-agents', default='', 
              help='Comma-separated list of remote agent URLs')
def unified(host: str, port: int, remote_agents: str):
    """Start unified server with A2A protocol and agent management on single port"""
    
    logger.info("🚀 Starting Unified Server...")
    logger.info(f"📍 Host: {host}:{port}")
    logger.info("🔧 A2A protocol + agent management (/mgm routes)")
    logger.info(f"📚 Management API: http://{host}:{port}/mgm/agents")
    
    remote_agents = os.getenv("REMOTE_AGENTS")
    remote_agent_addresses = []
    if remote_agents:
        remote_agent_addresses = [addr.strip() for addr in remote_agents.split(',')]
        logger.info(f"🤖 Initial remote agents: {remote_agent_addresses}")
    elif not remote_agents:
        # Если не указаны в командной строке, пытаемся прочитать из переменной
        # окружения
        remote_agent_env = os.getenv("REMOTE_AGENT", "")
        if remote_agent_env:
            remote_agent_addresses = [
                addr.strip() 
                for addr in remote_agent_env.split(',') 
                if addr.strip()
            ]
            logger.info(
                f"🌍 Loaded remote agents from environment: "
                f"{remote_agent_addresses}"
            )
    
    # Import and run the unified server
    from .unified_server import run_unified_server
    asyncio.run(run_unified_server(host, port, remote_agent_addresses))


@cli.command()
@click.option('--a2a-host', default='0.0.0.0', help='A2A server host')
@click.option('--a2a-port', default=10000, type=int, help='A2A server port')
@click.option('--fastapi-host', default='0.0.0.0', help='FastAPI server host')
@click.option('--fastapi-port', default=8000, type=int, help='FastAPI server port')
@click.option('--remote-agents', default='', 
              help='Initial remote agents for A2A server')
def both(a2a_host: str, a2a_port: int, fastapi_host: str, fastapi_port: int, 
         remote_agents: str):
    """Start both A2A and FastAPI servers simultaneously (DEPRECATED - use unified)"""
    
    logger.info("🚀 Starting BOTH servers...")
    logger.info(f"📍 A2A Server: {a2a_host}:{a2a_port}")
    logger.info(f"📍 FastAPI Server: {fastapi_host}:{fastapi_port}")
    logger.warning("⚠️  This command is deprecated. Use 'unified' instead.")
    
    async def run_both():
        # Start FastAPI server in background
        fastapi_config = uvicorn.Config(
            "app.fastapi_host_server:app", 
            host=fastapi_host, 
            port=fastapi_port,
            log_level="info"
        )
        fastapi_server = uvicorn.Server(fastapi_config)
        
        # Start A2A server
        remote_agents = os.getenv("REMOTE_AGENTS")
        remote_agent_addresses = []
        if remote_agents:
            remote_agent_addresses = [addr.strip() for addr in remote_agents.split(',')]
        
        from .main import async_main
        
        # Run both servers concurrently
        await asyncio.gather(
            fastapi_server.serve(),
            async_main(
                a2a_host, a2a_port, "http://localhost:6006/v1/traces",
                remote_agent_addresses
            )
        )
    
    asyncio.run(run_both())


@cli.command()
def status():
    """Check the status of running servers"""
    
    import requests
    
    servers = [
        ("Unified Server (A2A)", "http://localhost:10000/health", "A2A protocol"),
        ("Unified Server (Mgmt)", "http://localhost:10000/mgm/agents", "Agent management"),
        ("Legacy A2A Server", "http://localhost:10000/health", "A2A protocol server"),
        ("Legacy FastAPI Server", "http://localhost:8000/agents", "Dynamic agent management")
    ]
    
    logger.info("🔍 Checking server status...")
    
    for name, url, description in servers:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                logger.info(f"✅ {name}: Running - {description}")
            else:
                logger.warning(f"⚠️ {name}: Responding but status {response.status_code}")
        except requests.exceptions.RequestException:
            logger.error(f"❌ {name}: Not running - {description}")


if __name__ == '__main__':
    cli() 