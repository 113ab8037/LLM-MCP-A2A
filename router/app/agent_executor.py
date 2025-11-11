import json
import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    DataPart,
    Part,
    Task,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import (
    new_agent_parts_message,
    new_agent_text_message,
    new_task,
)
from a2a.utils.errors import ServerError
from .router_agent import RouterAgent
from typing_extensions import override


class MyAgentExecutor(AgentExecutor):
    """AgentExecutor Example."""

    def __init__(self, httpx_client, remote_agent_addresses):
        self.agent = RouterAgent(httpx_client, remote_agent_addresses)

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        query = context.get_user_input()
        task = context.current_task

        # Logging the start of request processing
        logging.info("="*60)
        logging.info("🚀 AGENT EXECUTOR: Starting request processing")
        logging.info(f"📝 Query: {query}")
        logging.info(f"🔍 Current task: {task.id if task else 'None'}")
        logging.info(f"🎯 Context ID: {context.contextId if task else 'None'}")
        
        # Logging the request context
        try:
            context_message = context.message
            logging.info(f"📋 Context message: {context_message}")
            logging.info(f"📊 Context message size: {len(str(context_message))} chars")
            if hasattr(context_message, 'parts') and context_message.parts:
                logging.info(f"📦 Context parts count: {len(context_message.parts)}")
                for i, part in enumerate(context_message.parts):
                    part_size = len(str(part)) if part else 0
                    logging.info(f"📄 Part {i+1}: {part_size} chars, type: {type(part.root).__name__ if part and part.root else 'Unknown'}")
        except Exception as e:
            logging.warning(f"⚠️ Could not log context details: {e}")

        # This agent always produces Task objects. If this request does
        # not have current task, create a new one and use it.
        if not task:
            task = new_task(context.message)
            event_queue.enqueue_event(task)
            logging.info(f"✅ Created new task: {task.id}")
        
        updater = TaskUpdater(event_queue, task.id, task.contextId)
        # invoke the underlying agent, using streaming results. The streams
        # now are update events.
        logging.info("🔄 Starting agent stream processing...")
        async for item in self.agent.stream(query, task.contextId):
            is_task_complete = item['is_task_complete']
            artifacts = None
            if not is_task_complete:
                updater.update_status(
                    TaskState.working,
                    new_agent_text_message(
                        item['updates'], task.contextId, task.id
                    ),
                )
                continue
            logging.info(f'item {item}')
            # If the response is a dictionary, assume its a form
            if isinstance(item['content'], dict):
                # Verify it is a valid form
                logging.info(f'item {item}')
                if (
                    'response' in item['content']
                    and 'result' in item['content']['response']
                ):
                    print("item['content']['response']['result']", item['content']['response']['result'])

                    for function_results in item['content']['response']['result']:
                        updater.update_status(
                        TaskState.input_required,
                        new_agent_parts_message(
                                [Part(root=DataPart(data=function_results))],
                            task.contextId,
                            task.id,
                        ),
                        final=True,
                    )
                    break
                else:
                    updater.update_status(
                        TaskState.failed,
                        new_agent_text_message(
                            'Reaching an unexpected state',
                            task.contextId,
                            task.id,
                        ),
                        final=True,
                    )
                    break
            else:
                # Emit the appropriate events
                logging.info(f"📤 AGENT EXECUTOR: Completing with text response")
                logging.info(f"📄 Response content: {item['content']}")
                updater.add_artifact(
                    [Part(root=TextPart(text=item['content']))], name='form'
                )
                updater.complete()
                logging.info("✅ AGENT EXECUTOR: Request processing completed")
                logging.info("="*60)
                break

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
