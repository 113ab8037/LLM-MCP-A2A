import os
import asyncio
from typing import Any, AsyncIterable
from google.adk.agents.llm_agent import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseConnectionParams
import litellm
litellm._turn_on_debug()

class AgentEvolution:
    """
    AgentEvolution - an advanced AI agent with evolutionary capabilities.
    """

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
    STREAM_TIMEOUT = 300  # 5 minutes timeout

    def __init__(self):
        # Phoenix is ​​disabled (no dependencies)
        self._agent = self._build_agent()
        self._user_id = 'remote_agent'
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    def get_processing_message(self) -> str:
        return os.getenv('PROCESSING_MESSAGE')

    def _build_agent(self) -> LlmAgent:
        """Creates an LLM agent with evolutionary capabilities."""
        # Create a toolset without specific parameters for compatibility
        mcp_url = os.getenv('MCP_URL')
        if mcp_url:
            toolset = MCPToolset(connection_params=SseConnectionParams(url=mcp_url))
            tools = [toolset]
        else:
            tools = []
            
        return LlmAgent(
            model=LiteLlm(
                model=os.getenv('LLM_MODEL'),
                api_base=os.getenv('LLM_API_BASE'),
            ),
            name=os.getenv('AGENT_NAME'),
            description=os.getenv('AGENT_DESCRIPTION'),
            instruction=os.getenv('AGENT_SYSTEM_PROMPT', 'Вы - профессиональный агент.'),
            tools=tools,
        )

    async def stream(self, query, session_id) -> AsyncIterable[dict[str, Any]]:
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        )
        content = types.Content(
            role='user', parts=[types.Part.from_text(text=query)]
        )
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )
        
        try:
            # Use asyncio.timeout for proper timeout handling 
            # with async generators
            async with asyncio.timeout(self.STREAM_TIMEOUT):
                async for event in self._runner.run_async(
                    user_id=self._user_id, 
                    session_id=session.id, 
                    new_message=content
                ):
                    if event.is_final_response():
                        response = None
                        
                        # Handle text responses
                        if (
                            event.content
                            and event.content.parts
                            and any(
                                p.text for p in event.content.parts
                            )
                        ):
                            response = '\n'.join(
                                [
                                    p.text 
                                    for p in event.content.parts 
                                    if p.text
                                ]
                            )
                        # Handle function responses
                        elif (
                            event.content
                            and event.content.parts
                            and any(
                                p.function_response 
                                for p in event.content.parts
                            )
                        ):
                            response = next(
                                p.function_response.model_dump()
                                for p in event.content.parts
                                if p.function_response
                            )
                        
                        # Only mark as complete if we have actual content
                        if response:
                            yield {
                                'is_task_complete': True,
                                'content': response,
                            }
                        else:
                            # If no content, continue processing
                            yield {
                                'is_task_complete': False,
                                'updates': (
                                    self.get_processing_message() 
                                    or 'Processing...'
                                ),
                            }
                    else:
                        yield {
                            'is_task_complete': False,
                            'updates': (
                                self.get_processing_message() 
                                or 'Processing...'
                            ),
                        }
        except asyncio.TimeoutError:
            yield {
                'is_task_complete': True,
                'content': (
                    'Agent timed out while processing request'
                ),
            }
        except Exception as e:
            yield {
                'is_task_complete': True,
                'content': f'Agent error: {str(e)}',
            }