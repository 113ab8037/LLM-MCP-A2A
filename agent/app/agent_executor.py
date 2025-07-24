import json
import logging
import warnings
import asyncio
import time
from contextlib import suppress

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    DataPart,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import new_agent_parts_message, new_agent_text_message
from a2a.utils.errors import ServerError
from .agent import AgentEvolution
from opentelemetry import trace
from openinference.semconv.trace import SpanAttributes
import os

# Suppress OpenTelemetry context warnings to prevent crashes
warnings.filterwarnings("ignore", message=".*Failed to detach context.*")
warnings.filterwarnings(
    "ignore", message=".*was created in a different Context.*"
)

logger = logging.getLogger(__name__)


# Also suppress via logging filter
class OTelContextFilter(logging.Filter):
    def filter(self, record):
        msg = str(record.getMessage())
        return not (
            'Failed to detach context' in msg
            or 'was created in a different Context' in msg
        )


# Apply filter to relevant loggers
for logger_name in ['opentelemetry.context', 'opentelemetry.trace']:
    otel_logger = logging.getLogger(logger_name)
    otel_logger.addFilter(OTelContextFilter())
    otel_logger.setLevel(logging.WARNING)  # Set to WARNING to avoid logs


class EvolutionAgentExecutor(AgentExecutor):
    """
    Evolution AgentExecutor - A cutting-edge AI agent.
    """

    def __init__(self):
        self.agent = AgentEvolution()
        self.tracer = trace.get_tracer(__name__)

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        query = context.get_user_input()
        session_id = context.context_id
        task_id = context.task_id

        # Enhanced logging for request tracking
        logger.info(f"Starting task execution - Task ID: {task_id}, Session: {session_id}")
        logger.info(f"User query length: {len(query)} characters")
        logger.debug(f"Full user query: {query[:200]}..." if len(query) > 200 else f"Full user query: {query}")

        # Start a span for session tracking in Phoenix
        with self.tracer.start_as_current_span(
            "evolution_agent_execution",
            attributes={
                SpanAttributes.SESSION_ID: session_id,
                SpanAttributes.INPUT_VALUE: query,
                SpanAttributes.LLM_MODEL_NAME: os.getenv(
                    "LLM_MODEL", "not_set"
                ),
                "agent.name": "evolution_agent",
                "task.id": task_id,
                "query.length": len(query),
                "user.context_id": session_id,
            },
        ) as span:
            try:
                # Track execution start time
                execution_start_time = time.time()
                span.set_attribute("execution.start_time", execution_start_time)
                logger.info(f"Starting agent execution for task {task_id} at {execution_start_time}")
                
                updater = TaskUpdater(event_queue, task_id, session_id)
                logger.info(f"Task updater initialized for task {task_id}")
                span.set_attribute("updater.initialized", True)
                
                if not context.current_task:
                    await updater.submit()

                await updater.start_work()

                final_response_received = False

                # Use suppress to gracefully handle context errors
                with suppress(
                    GeneratorExit,
                    ValueError,
                    RuntimeError,
                    asyncio.CancelledError,
                ):
                    stream_item_count = 0
                    logger.info(f"Starting agent stream for task {task_id}")
                    
                    async for item in self.agent.stream(query, session_id):
                        stream_item_count += 1
                        logger.debug(f"Received stream item #{stream_item_count} for task {task_id}")
                        
                        # Add stream metrics to span
                        span.set_attribute("stream.item_count", stream_item_count)
                        
                        if item.get('is_task_complete', False):
                            final_response_received = True
                            logger.info(f"Final response received for task {task_id} after {stream_item_count} items")
                            await self._handle_final_response(
                                item, updater, span
                            )
                            break
                        else:
                            update_text = item.get('updates', '')
                            logger.debug(f"Sending status update for task {task_id}: {len(update_text)} chars")
                            await updater.update_status(
                                TaskState.working,
                                new_agent_text_message(
                                    update_text,
                                    session_id,
                                    task_id,
                                ),
                            )
                    
                    # Track execution completion
                    execution_end_time = time.time()
                    execution_duration = execution_end_time - execution_start_time
                    
                    logger.info(f"Agent stream completed for task {task_id} with {stream_item_count} total items")
                    logger.info(f"Task {task_id} execution completed in {execution_duration:.2f} seconds")
                    
                    span.set_attribute("execution.end_time", execution_end_time)
                    span.set_attribute("execution.duration_seconds", execution_duration)
                    span.set_attribute("execution.completed", True)

                if not final_response_received:
                    await self._handle_agent_failure(
                        updater, span, "No final response from agent."
                    )

            except asyncio.CancelledError:
                logger.warning(f"Task {task_id} was cancelled.")
                span.set_attribute("execution.cancelled", True)
                await self._handle_agent_failure(
                    updater,
                    span,
                    "Task cancelled by client.",
                    is_cancellation=True,
                )
            except Exception as e:
                error_type = type(e).__name__
                logger.error(
                    f"An unexpected error in task {task_id}: {error_type} - {e}",
                    exc_info=True,
                )
                span.set_attribute("execution.error", True)
                span.set_attribute("execution.error_type", error_type)
                await self._handle_agent_failure(updater, span, f"Execution error ({error_type}): {str(e)}")

    async def _handle_final_response(self, item, updater, span):
        """Handle the final response from the agent."""
        logger.info(f"Processing final response for task {updater.task_id}")
        
        content = item.get('content')
        content_type = type(content).__name__
        logger.debug(f"Final response content type: {content_type}")
        
        # Add response metadata to span
        span.set_attribute("response.content_type", content_type)
        
        if (
            isinstance(content, dict)
            and 'response' in content
            and 'result' in content['response']
        ):
            try:
                logger.debug(f"Processing JSON response for task {updater.task_id}")
                data = json.loads(content['response']['result'])
                
                # Log response size and structure
                response_size = len(json.dumps(data))
                logger.info(f"JSON response size: {response_size} characters for task {updater.task_id}")
                span.set_attribute("response.size_chars", response_size)
                span.set_attribute("response.format", "json")
                
                await updater.update_status(
                    TaskState.input_required,
                    new_agent_parts_message(
                        [Part(root=DataPart(data=data))],
                        updater.context_id,
                        updater.task_id,
                    ),
                    final=True,
                )
                span.set_attribute(
                    SpanAttributes.OUTPUT_VALUE, json.dumps(data)
                )
                logger.info(f"Successfully processed JSON response for task {updater.task_id}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for task {updater.task_id}: {e}")
                await self._handle_agent_failure(
                    updater, span, f"Invalid JSON in final response: {e}"
                )
        elif isinstance(content, str):
            logger.debug(f"Processing text response for task {updater.task_id}")
            response_size = len(content)
            logger.info(f"Text response size: {response_size} characters for task {updater.task_id}")
            
            span.set_attribute("response.size_chars", response_size)
            span.set_attribute("response.format", "text")
            
            await updater.add_artifact(
                [Part(root=TextPart(text=content))], name='result'
            )
            await updater.complete()
            span.set_attribute(SpanAttributes.OUTPUT_VALUE, content)
            logger.info(f"Successfully processed text response for task {updater.task_id}")
        else:
            logger.error(f"Unexpected content type {content_type} for task {updater.task_id}")
            await self._handle_agent_failure(
                updater, span, f"Unexpected content type: {content_type}"
            )

        span.set_attribute("response.success", True)

    async def _handle_agent_failure(
        self, updater, span, error_message, is_cancellation=False
    ):
        """Centralized handler for agent failures."""
        failure_type = "cancellation" if is_cancellation else "error"
        msg = f"Agent failed for task {updater.task_id}: {error_message}"
        logger.error(msg)
        
        # Enhanced error tracking
        span.set_attribute("response.success", False)
        span.set_attribute("error.message", error_message)
        span.set_attribute("failure.type", failure_type)
        
        if is_cancellation:
            span.set_attribute("error.type", "CancelledError")
            logger.warning(f"Task {updater.task_id} was cancelled by user or timeout")
        else:
            logger.error(f"Task {updater.task_id} failed with error: {error_message}")
            
        try:
            logger.debug(f"Updating task {updater.task_id} status to failed")
            await updater.update_status(TaskState.failed)
            logger.info(f"Successfully marked task {updater.task_id} as failed")
        except Exception as update_error:
            logger.error(
                f"Failed to update task status to failed for task {updater.task_id}: {update_error}"
            )
            span.set_attribute("error.status_update_failed", True)
            span.set_attribute("error.status_update_message", str(update_error))

    async def cancel(self, request: RequestContext, event_queue: EventQueue):
        raise ServerError(error=UnsupportedOperationError())
