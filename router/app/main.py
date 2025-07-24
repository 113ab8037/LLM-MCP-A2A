import logging
import click
import httpx
import asyncio
import json
from datetime import datetime
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
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import os
load_dotenv()

# Настройка детального логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования всех HTTP запросов и ответов"""
    
    async def dispatch(self, request: Request, call_next):
        # Логируем входящий запрос
        start_time = datetime.now()
        
        logger.info(f"🔄 INCOMING REQUEST - {request.method} {request.url}")
        logger.info(f"📥 Request Headers: {dict(request.headers)}")
        
        try:
            if request.headers.get("content-type", "").startswith("application/json"):
                # Сохраняем body для повторного использования
                body = await request.body()
                if body:
                    try:
                        request_data = json.loads(body.decode())
                        logger.info(f"📥 Request Body: {json.dumps(request_data, indent=2)}")
                    except:
                        logger.info(f"📥 Request Body (raw): {body.decode()[:500]}...")
        except Exception as e:
            logger.warning(f"Could not read request body: {e}")
        
        # Обрабатываем запрос
        response = await call_next(request)
        
        # Логируем ответ
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"📤 OUTGOING RESPONSE - Status: {response.status_code}, Duration: {duration:.3f}s")
        
        return response


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""
    pass


async def async_main(host, port, phoenix, remote_agent_addresses):
    try:
        print(phoenix)
        async with httpx.AsyncClient(timeout=Timeout(timeout=60.0)) as httpx_client:
            capabilities = AgentCapabilities(streaming=True)
            skill = AgentSkill(
                id='answer_about_cloud_ru_products',
                name='Ответить с перенаправлением вопроса',
                description='Помогает с продуктами компании cloud.ru',
                tags=['cloud.ru'],
                examples=[
                    'Что такое база данных?',
                    'Что такое виртуальная машина?',
                    'Как создать виртуальную машину?'
                ],
            )
            my_agent_executor = MyAgentExecutor(httpx_client, remote_agent_addresses)
            url_agent=os.getenv("URL_AGENT")
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
            server = A2AStarletteApplication(
                agent_card=agent_card, http_handler=request_handler
            )
            
            starlette_app = server.build()
            
            # Add logging middleware (first to catch all requests)
            starlette_app.add_middleware(RequestLoggingMiddleware)
            
            # Build the application and add CORS middleware
            starlette_app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],  # Allows all origins
                allow_credentials=True,
                allow_methods=["*"],  # Allows all methods
                allow_headers=["*"],  # Allows all headers
            )

            # Instrument the starlette app for tracing

            import uvicorn
            config = uvicorn.Config(starlette_app, host=host, port=port)
            server = uvicorn.Server(config)
            await server.serve()
    except MissingAPIKeyError as e:
        logger.error(f'Error: {e}')
        exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        exit(1)


@click.command()
@click.option('--host', default='localhost')
@click.option('--port', default=10000)
@click.option('--phoenix', default='http://localhost:6006/v1/traces')
@click.option('--remote-agent-addresses', default='http://localhost:10001,http://localhost:10002')
def main(host, port, phoenix, remote_agent_addresses):
    asyncio.run(async_main(host, port, phoenix, remote_agent_addresses.split(',')))


if __name__ == '__main__':
    main()