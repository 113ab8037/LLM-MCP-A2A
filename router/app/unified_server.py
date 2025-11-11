import asyncio
import logging

import httpx
import json
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from httpx import Timeout

from .agent_executor import MyAgentExecutor
from .host_agent import HostAgent, A2ACardResolver
from dotenv import load_dotenv
import os

load_dotenv()


# Setting up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Global variables for state management
http_client_instance: httpx.AsyncClient | None = None
host_agent_instance: HostAgent | None = None
_agent_lock = asyncio.Lock()  # protects modifications of remote agents


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования всех HTTP запросов и ответов"""
    
    async def dispatch(self, request: Request, call_next):
        # Логируем входящий запрос
        start_time = datetime.now()
        
        logger.info(
            f"🔄 INCOMING REQUEST - {request.method} {request.url}"
        )
        logger.info(f"📥 Request Headers: {dict(request.headers)}")
        
        try:
            content_type = request.headers.get("content-type", "")
            if content_type.startswith("application/json"):
                # Save the body for reuse
                body = await request.body()
                if body:
                    try:
                        request_data = json.loads(body.decode())
                        body_json = json.dumps(request_data, indent=2)
                        logger.info(f"📥 Request Body: {body_json}")
                    except Exception:
                        body_raw = body.decode()[:500]
                        logger.info(f"📥 Request Body (raw): {body_raw}...")
        except Exception as e:
            logger.warning(f"Could not read request body: {e}")
        
        # Processing your request
        response = await call_next(request)
        
        # Logging the response
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(
            f"📤 OUTGOING RESPONSE - Status: {response.status_code}, "
            f"Duration: {duration:.3f}s"
        )
        
        return response


# We remove the unused model since we are using JSON directly


async def init_global_state():
    """Инициализация глобального состояния"""
    global http_client_instance, host_agent_instance
    
    # Initializing the HTTP client
    http_client_instance = httpx.AsyncClient(timeout=Timeout(timeout=60.0))
    
    # Initializing HostAgent
    host_agent_instance = HostAgent(
        remote_agent_addresses=[], 
        http_client=http_client_instance
    )
    
    logger.info(
        "🚀 Unified server initialized with A2A and management capabilities"
    )


async def cleanup_global_state():
    """Очистка глобального состояния"""
    global http_client_instance
    
    if http_client_instance:
        await http_client_instance.aclose()
    logger.info("👋 Unified server cleanup completed")


# Management API endpoints
async def list_agents(request: Request):
    """Return list of currently registered remote agents."""
    if host_agent_instance is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "HostAgent not initialised"}
        )
    agents = host_agent_instance.list_remote_agents()
    return JSONResponse(content=agents)


async def add_agent(request: Request):
    """Add a new remote agent by URL."""
    if host_agent_instance is None or http_client_instance is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "HostAgent not initialised"}
        )

    try:
        body = await request.body()
        data = json.loads(body.decode())
        agent_address = data.get("address")
        
        if not agent_address:
            return JSONResponse(
                status_code=400,
                content={"detail": "Missing address field"}
            )

        async with _agent_lock:
            if agent_address in host_agent_instance.remote_agent_addresses:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Agent address already registered"}
                )

            try:
                # Fetch the agent card from the remote agent
                resolver = A2ACardResolver(http_client_instance, agent_address)
                card = await resolver.get_agent_card()
            except Exception as exc:
                logger.exception(
                    "❌ Failed to resolve agent card from %s", agent_address
                )
                return JSONResponse(
                    status_code=502,
                    content={"detail": str(exc)}
                )

            # Register within HostAgent internal structures
            host_agent_instance.remote_agent_addresses.append(agent_address)
            host_agent_instance.register_agent_card(card)
            logger.info(
                "✅ Added remote agent '%s' (%s)",
                card.name,
                agent_address,
            )

        return JSONResponse(
            status_code=201,
            content={"message": "Agent added", "name": card.name}
        )
    except Exception as exc:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Invalid request: {exc}"}
        )


async def remove_agent(request: Request):
    """Remove a remote agent by its name."""
    if host_agent_instance is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "HostAgent not initialised"}
        )

    # Extract agent name from path
    path_segments = request.url.path.split('/')
    if len(path_segments) < 4:  # /mgm/agents/{agent_name}
        return JSONResponse(
            status_code=400,
            content={"detail": "Agent name required"}
        )
    
    agent_name = path_segments[3]

    async with _agent_lock:
        try:
            host_agent_instance.remove_agent_card(agent_name)
        except ValueError as exc:
            return JSONResponse(
                status_code=404,
                content={"detail": str(exc)}
            )

        logger.info("🗑️ Removed remote agent '%s'", agent_name)
    
    return JSONResponse(
        content={"message": "Agent removed", "name": agent_name}
    )


async def create_unified_app(
    host: str, port: int, remote_agent_addresses: list[str]
) -> Starlette:
    """Building a unified application with A2A and agent management"""
    
    # Инициализируем глобальное состояние
    await init_global_state()
    
    # Создаем A2A приложение
    capabilities = AgentCapabilities(streaming=True)
    skill = AgentSkill(
        id='answer_about_cloud_ru_products',
        name='Ответить с перенаправлением вопроса',
        description='Helps with cloud.ru products',
        tags=['cloud.ru'],
        examples=[
            'What is a database?',
            'What is a virtual machine?',
            'How do I create a virtual machine?'
        ],
    )
    
    my_agent_executor = MyAgentExecutor(
        http_client_instance, remote_agent_addresses
    )
    url_agent = os.getenv("URL_AGENT", "http://localhost:8000")
    agent_card = AgentCard(
        name='Router',
        description='перенаправляет запросы на других агентов',
        url=url_agent,
        version='1.0.0',
        defaultInputModes=my_agent_executor.agent.SUPPORTED_CONTENT_TYPES,
        defaultOutputModes=my_agent_executor.agent.SUPPORTED_CONTENT_TYPES,
        capabilities=capabilities,
        skills=[skill],
    )
    
    request_handler = DefaultRequestHandler(
        agent_executor=my_agent_executor,
        task_store=InMemoryTaskStore(),
    )
    
    a2a_server = A2AStarletteApplication(
        agent_card=agent_card, 
        http_handler=request_handler
    )
    
    a2a_app = a2a_server.build()
    
    # Creating routes to manage agents
    mgm_routes = [
        Route('/mgm/agents', list_agents, methods=['GET']),
        Route('/mgm/agents', add_agent, methods=['POST']),
        Route('/mgm/agents/{agent_name}', remove_agent, methods=['DELETE']),
    ]
    
    # Let's create the main application
    routes = mgm_routes + [
        Mount('/', a2a_app)  # A2A application handles all other paths
    ]
    
    app = Starlette(routes=routes)
    
    # Adding CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Adding middleware for logging
    app.add_middleware(RequestLoggingMiddleware)
    
    return app


async def run_unified_server(
    host: str, port: int, remote_agent_addresses: list[str]
):
    """Запускаем объединенный сервер"""
    
    # If remote_agent_addresses is empty, we try to read from the variable
    # environment
    if not remote_agent_addresses:
        remote_agent_env = os.getenv("REMOTE_AGENTS", "")
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
    
    try:
        app = await create_unified_app(host, port, remote_agent_addresses)
        
        import uvicorn
        config = uvicorn.Config(app, host=host, port=port)
        server = uvicorn.Server(config)
        await server.serve()
    finally:
        await cleanup_global_state() 