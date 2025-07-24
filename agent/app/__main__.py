import logging
import os

import click

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from app.agent import AgentEvolution
from app.agent_executor import EvolutionAgentExecutor
from dotenv import load_dotenv

from starlette.middleware.cors import CORSMiddleware  # Import CORSMiddleware

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.starlette import StarletteInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from openinference.semconv.resource import ResourceAttributes

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""

    pass


@click.command()
@click.option('--host', default=os.getenv('HOST', '0.0.0.0'))
@click.option('--port', default=int(os.getenv('PORT', '10002')))
def main(host, port):
    try:
        # Main Evolution Skill
        main_skill = AgentSkill(
            id='evolution_main_skill',
            name='Эволюционный ИИ',
            description=(
                'Передовой искусственный интеллект с эволюционными '
                'возможностями для решения сложных задач'
            ),
            tags=[
                'evolution', 'ai', 'intelligence', 
                'problem-solving', 'optimization'
            ],
            examples=[
                'Реши эту задачу эволюционным способом',
                'Оптимизируй процесс',
                'Найди лучшее решение',
                'Адаптируйся к новым условиям',
                'Эволюционируй алгоритм'
            ],
        )
        
        # URL для контейнера должен использовать имя контейнера для Docker сети
        url_agent = "http://a2a-agent:10002"
        agent_card = AgentCard(
            name=os.getenv('AGENT_NAME', 'evolution_agent'),
            description=os.getenv(
                'AGENT_DESCRIPTION',
                'Эволюционный агент с передовыми возможностями ИИ'
            ),
            url=url_agent,
            version=os.getenv('AGENT_VERSION', '1.0.0'),
            defaultInputModes=AgentEvolution.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=AgentEvolution.SUPPORTED_CONTENT_TYPES,
            capabilities=AgentCapabilities(streaming=False),
            skills=[main_skill],
        )
        request_handler = DefaultRequestHandler(
            agent_executor=EvolutionAgentExecutor(),
            task_store=InMemoryTaskStore(),
        )

        if os.getenv('ENABLE_PHOENIX', 'false').lower() == 'true':
            logger.debug('Telemetry Configuration')
            resource = Resource(
                attributes={
                    ResourceAttributes.PROJECT_NAME: agent_card.name,
                    "service.name": os.getenv('AGENT_NAME'),
                    "service.version": os.getenv(
                        'AGENT_VERSION'
                    ),
                }
            )
            tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(tracer_provider)
            tracer_provider = trace.get_tracer_provider()

            jaeger_exporter = OTLPSpanExporter(
                endpoint=os.getenv('PHOENIX_ENDPOINT'),
            )
            tracer_provider.add_span_processor(
                BatchSpanProcessor(jaeger_exporter)
            )

        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )
        starlette_app = server.build()
        
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
        
        if os.getenv('ENABLE_PHOENIX', 'false').lower() == 'true':
            StarletteInstrumentor().instrument_app(starlette_app)

        uvicorn.run(starlette_app, host=host, port=port)
        
    except MissingAPIKeyError as e:
        logger.error(f'Error: {e}')
        exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        exit(1)


if __name__ == '__main__':
    main()
