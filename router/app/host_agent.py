import asyncio
import base64
import json
import logging
# flake8: noqa
import traceback
import uuid
import os
import httpx

from a2a.client import A2ACardResolver
from a2a.types import (
    AgentCard,
    DataPart,
    Message,
    MessageSendConfiguration,
    MessageSendParams,
    Part,
    Task,
    TaskState,
    TextPart,
)
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext
from google.genai import types
# import litellm
# litellm._turn_on_debug()
from .remote_agent_connection import RemoteAgentConnections, TaskUpdateCallback
from dotenv import load_dotenv

load_dotenv()

HISTORY_LENGTH = 3
logger = logging.getLogger(__name__)



class HostAgent:
    """The host agent manages remote agent connections.

    All instances share a **common** registry so that agents added through
    FastAPI server, immediately became available to `RouterAgent`, created in another
    parts of the application. This eliminates duplication and ensures consistency
    state in all *HostAgent* objects within a single process.
    """

    # --------- Global shared state ---------
    _global_remote_agent_connections: dict[str, RemoteAgentConnections] = {}
    _global_cards: dict[str, AgentCard] = {}
    _global_addresses: list[str] = []
    _global_agents: str = ""

    """The host agent.

    This is the agent responsible for choosing which remote agents to send
    tasks to and coordinate their work.
    """

    def __init__(
        self,
        remote_agent_addresses: list[str],
        http_client: httpx.AsyncClient,
        task_callback: TaskUpdateCallback | None = None,
    ):
        # Use the global registries so that all HostAgent instances share state
        self.remote_agent_addresses = HostAgent._global_addresses
        self.task_callback = task_callback
        self.httpx_client = http_client
        self.remote_agent_connections = HostAgent._global_remote_agent_connections
        self.cards = HostAgent._global_cards

        # Add any new addresses passed during construction
        for addr in remote_agent_addresses:
            if addr not in HostAgent._global_addresses:
                HostAgent._global_addresses.append(addr)

        loop = asyncio.get_event_loop()
        loop.create_task(self.register_agent_cards())

    async def register_agent_cards(self):
        for address in self.remote_agent_addresses:
            card_resolver = A2ACardResolver(self.httpx_client, address)
            card = await card_resolver.get_agent_card()
            remote_connection = RemoteAgentConnections(self.httpx_client, card)
            self.remote_agent_connections[card.name] = remote_connection
            self.cards[card.name] = card
        agent_info = []
        for ra in self.list_remote_agents():
            agent_info.append(json.dumps(ra))
        HostAgent._global_agents = '\n'.join(agent_info)

    def register_agent_card(self, card: AgentCard):
        remote_connection = RemoteAgentConnections(self.httpx_client, card)
        self.remote_agent_connections[card.name] = remote_connection
        self.cards[card.name] = card
        agent_info = []
        for ra in self.list_remote_agents():
            agent_info.append(json.dumps(ra))
        HostAgent._global_agents = '\n'.join(agent_info)

    def remove_agent_card(self, agent_name: str) -> None:
        """Remove a remote agent and clean registries.

        Args:
            agent_name: Name of the agent card.
        Raises:
            ValueError: If the agent is not registered.
        """
        if agent_name not in self.remote_agent_connections:
            raise ValueError(f"Agent {agent_name} not found")

        connection = self.remote_agent_connections.pop(agent_name)
        self.cards.pop(agent_name, None)

        agent_url: str | None = getattr(connection.card, "url", None)
        if agent_url and agent_url in HostAgent._global_addresses:
            HostAgent._global_addresses.remove(agent_url)

        agent_info = [json.dumps(ra) for ra in self.list_remote_agents()]
        HostAgent._global_agents = "\n".join(agent_info)

    def create_agent(self) -> Agent:
        model_name = os.getenv("LLM_MODEL")
        api_base = os.getenv( "LLM_API_BASE")
        return Agent(
            model=LiteLlm(
                model=model_name,
                api_base=api_base,
            ),
            name='host_agent',
            instruction=self.root_instruction,
            before_model_callback=self.before_model_callback,
            description=(
                'This agent orchestrates the decomposition of the user request into'
                ' tasks that can be performed by the child agents.'
            ),
            tools=[
                self.send_message,
            ],
            generate_content_config=types.GenerateContentConfig(
                max_output_tokens=32000
            ),
            
        )

    def root_instruction(self, context: ReadonlyContext) -> str:
        current_agent = self.check_state(context)
        agent_system_prompt = os.getenv("AGENT_SYSTEM_PROMPT")
        return f"""{agent_system_prompt}
    
Agents:
{HostAgent._global_agents}

Current agent: {current_agent['active_agent']}
DO NOT ANSWER BY YOURSELF! USE TOOLS!
DO NOT ANSWER BY YOURSELF! USE TOOLS!
DO NOT ANSWER BY YOURSELF! USE TOOLS!
DO NOT ANSWER BY YOURSELF! USE TOOLS!
DO NOT ANSWER BY YOURSELF! USE TOOLS!
DO NOT ANSWER BY YOURSELF! USE TOOLS!
"""

    def check_state(self, context: ReadonlyContext):
        state = context.state
        if (
            'context_id' in state
            and 'session_active' in state
            and state['session_active']
            and 'agent' in state
        ):
            return {'active_agent': f'{state["agent"]}'}
        return {'active_agent': 'None'}

    def before_model_callback(
        self, callback_context: CallbackContext, llm_request
    ):
        """
        This feature is used to shorten the conversation history.
        It is called before the model is called.
        It is used to shorten the conversation history to the last 3 lines.
        """
        n = len(llm_request.contents)
        logging.info(f"📚 Before model callback - Total contents: {n}")
        
        if n == 0:
            logging.info("📚 No contents to process, returning None")
            return None

        if n % 2 == 0:
            logging.info("📚 Even number of contents, returning None")
            return None

        num_turns = (n - 1) // 2
        keep_turns = min(HISTORY_LENGTH, num_turns)
        start_idx = (num_turns - keep_turns) * 2
        
        logging.info(
            f"📚 History management - Total turns: {num_turns}, "
            f"Keep turns: {keep_turns}, Start index: {start_idx}"
        )
        
        if start_idx > 0:
            original_length = len(llm_request.contents)
            llm_request.contents = llm_request.contents[start_idx:]
            new_length = len(llm_request.contents)
            removed_count = original_length - new_length
            logging.info(
                f"📚 History trimmed - Original: {original_length} contents, "
                f"New: {new_length} contents, Removed: {removed_count}"
            )
        else:
            logging.info("📚 No history trimming needed - all contents kept")
        
        return None


    def list_remote_agents(self):
        """List the available remote agents you can use to delegate the task."""
        if not self.remote_agent_connections:
            return []

        remote_agent_info = []
        for card in self.cards.values():
            remote_agent_info.append(
                {'name': card.name, 'description': card.description}
            )
        return remote_agent_info

    async def send_message(
        self, agent_name: str, message: str, tool_context: ToolContext
    ):
        """Sends a task either streaming (if supported) or non-streaming.

        This will send a message to the remote agent named agent_name.

        Args:
          agent_name: The name of the agent to send the task to.
          message: The message to send to the agent for the task.
          tool_context: The tool context this method runs in.

        Yields:
          A dictionary of JSON data.
        """
        # Логируем отправку запроса к удаленному агенту
        logging.info("="*50)
        logging.info(f"🌐 HOST AGENT: Sending message to remote agent")
        logging.info(f"🎯 Target agent: {agent_name}")
        logging.info(f"📝 Message: {message}")
        logging.info(f"📊 Message size: {len(message)} chars")
        
        # Логируем контекст tool_context
        try:
            context_state = tool_context.state
            logging.info(f"🗂️ Tool context state: {context_state}")
            logging.info(f"📊 Tool context state size: {len(str(context_state))} chars")
            if context_state:
                for key, value in context_state.items():
                    value_size = len(str(value)) if value else 0
                    logging.info(f"🔑 Context[{key}]: {value_size} chars - {value}")
        except Exception as e:
            logging.warning(f"⚠️ Could not log tool context: {e}")
        
        try:
            if agent_name not in self.remote_agent_connections:
                raise ValueError(f'Agent {agent_name} not found')
            state = tool_context.state
            state['agent'] = agent_name
            client = self.remote_agent_connections[agent_name]
            if not client:
                raise ValueError(f'Client not available for {agent_name}')
            taskId = state.get('task_id', None)
            contextId = state.get('context_id', None)
            messageId = state.get('message_id', None)
            task: Task
            if not messageId:
                messageId = str(uuid.uuid4())
            request: MessageSendParams = MessageSendParams(
                id=str(uuid.uuid4()),
                message=Message(
                    role='user',
                    parts=[TextPart(text=message)],
                    messageId=messageId,
                    contextId=contextId,
                    taskId=taskId,
                ),
                configuration=MessageSendConfiguration(
                    acceptedOutputModes=['text', 'text/plain', 'image/png'],
                ),
            )
            response = await client.send_message(request, self.task_callback, False)
            
            # Logging the response from the remote agent
            logging.info(f"📨 Received response from {agent_name}")
            logging.info(f"📦 Response type: {type(response).__name__}")
            
            if isinstance(response, Message):
                logging.info("📄 Response is Message type")
                logging.info(f"📝 Message parts: {len(response.parts) if response.parts else 0}")
                return await convert_parts(response.parts, tool_context)
            
            task: Task = response
            logging.info(f"📋 Response is Task type - ID: {task.id}")
            logging.info(f"🔄 Task status: {task.status.state if task.status else 'No status'}")
            
            # Assume completion unless a state returns that isn't complete
            state['session_active'] = task.status.state not in [
                TaskState.completed,
                TaskState.canceled,
                TaskState.failed,
                TaskState.unknown,
            ]
            if task.contextId:
                state['context_id'] = task.contextId
            state['task_id'] = task.id
            if task.status.state == TaskState.input_required:
                # Force user input back
                tool_context.actions.skip_summarization = True
                tool_context.actions.escalate = True
            elif task.status.state == TaskState.canceled:
                # Open question, should we return some info for cancellation instead
                raise ValueError(f'Agent {agent_name} task {task.id} is cancelled')
            elif task.status.state == TaskState.failed:
                # Raise error for failure
                raise ValueError(f'Agent {agent_name} task {task.id} failed')
            response = []
            if task.status.message:
                # Assume the information is in the task message.
                response.extend(
                    await convert_parts(task.status.message.parts, tool_context)
                )
            if task.artifacts:
                for artifact in task.artifacts:
                    response.extend(
                        await convert_parts(artifact.parts, tool_context)
                    )
            # print("!!!!!!! response", response)
            return response
        except Exception as e:
            error = traceback.format_exc()
            print(error)
            return error




async def convert_parts(parts: list[Part], tool_context: ToolContext):
    rval = []
    for p in parts:
        rval.append(await convert_part(p, tool_context))
    return rval


async def convert_part(part: Part, tool_context: ToolContext):
    if part.root.kind == 'text':
        return part.root.text
    elif part.root.kind == 'data':
        return part.root.data
    elif part.root.kind == 'file':
        # Repackage A2A FilePart to google.genai Blob
        # Currently not considering plain text as files
        file_id = part.root.file.name
        file_bytes = base64.b64decode(part.root.file.bytes)
        file_part = types.Part(
            inline_data=types.Blob(
                mime_type=part.root.file.mimeType, data=file_bytes
            )
        )
        await tool_context.save_artifact(file_id, file_part)
        tool_context.actions.skip_summarization = True
        tool_context.actions.escalate = True
        return DataPart(data={'artifact-file-id': file_id})
    return f'Unknown type: {part.kind}'
