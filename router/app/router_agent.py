from typing import AsyncIterable, Any, Optional
import logging

from google.adk import Runner
from google.adk.agents import LlmAgent, RunConfig
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.genai import types
from typing_extensions import override

from .host_agent import HostAgent
from .task_manager import AgentWithTaskManager

from google.adk.sessions.base_session_service import GetSessionConfig
from google.adk.sessions.session import Session

def task_callback(event, card):
    pass


class LimitedContextGetSessionService(InMemorySessionService):
    """
    An InMemorySessionService that limits the number of events returned by get_session,
    in order to control the size of the context sent to the LLM.
    """

    def __init__(self, max_recent_events_for_llm: int = 10):
        super().__init__()
        self.max_recent_events_for_llm = max_recent_events_for_llm
        print(f"--- LimitedContextGetSessionService initialized: will limit LLM context to "
              f"{self.max_recent_events_for_llm} recent events when reading ---")

    @override
    def get_session(
            self,
            *,
            app_name: str,
            user_id: str,
            session_id: str,
            config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:

        # Prepare an effective configuration to limit events
        effective_config = config

        if effective_config is None:
            # If the caller (Runner/Agent) does not provide a config, we apply our default limit.
            effective_config = GetSessionConfig(num_recent_events=self.max_recent_events_for_llm)
        elif effective_config.num_recent_events is None:
            # If the caller's config does not have num_recent_events, we apply our limit.
            effective_config.num_recent_events = self.max_recent_events_for_llm
        elif effective_config.num_recent_events > self.max_recent_events_for_llm:
            # If the caller requests more than our cap, we cap it.
            effective_config.num_recent_events = self.max_recent_events_for_llm

        return super().get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            config=effective_config
        )


class RouterAgent(AgentWithTaskManager):
    """An agent that handles reimbursement requests."""

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self, httpx_client, remote_agent_addresses):
        self._agent = self._build_agent(httpx_client, remote_agent_addresses)
        self._user_id = 'remote_agent'

        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=LimitedContextGetSessionService(max_recent_events_for_llm=3),
            memory_service=InMemoryMemoryService(),
        )

    def get_processing_message(self) -> str:
        return 'Processing the reimbursement request...'

    def _build_agent(self, httpx_client, remote_agent_addresses) -> LlmAgent:
        """Builds the LLM agent for the reimbursement agent."""
        return HostAgent(
            remote_agent_addresses,
            httpx_client,
        ).create_agent()

    async def stream(self, query, session_id) -> AsyncIterable[dict[str, Any]]:
        # Логируем начало обработки в RouterAgent
        logging.info("="*40)
        logging.info("🤖 ROUTER AGENT: Starting stream processing")
        logging.info(f"📝 Query: {query}")
        logging.info(f"📊 Query size: {len(query)} chars")
        logging.info(f"🔑 Session ID: {session_id}")
        
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
            logging.info(f"✅ Created new session: {session.id}")
            logging.info(f"📊 New session state size: {len(str(session.state)) if session.state else 0} chars")
        else:
            logging.info(f"🔄 Using existing session: {session.id}")
            logging.info(f"📊 Existing session state size: {len(str(session.state)) if session.state else 0} chars")
            if session.state:
                logging.info(f"🗂️ Session state: {session.state}")
            
        # Логируем содержимое сообщения
        logging.info(f"💬 Content parts: {len(content.parts) if content.parts else 0}")
        for i, part in enumerate(content.parts or []):
            if hasattr(part, 'text') and part.text:
                logging.info(f"📄 Part {i+1} text: {len(part.text)} chars")
            
        async for event in self._runner.run_async(
            user_id=self._user_id, session_id=session.id, new_message=content, run_config=RunConfig(max_llm_calls=10)
        ):
            logging.info(f"🎭 RouterAgent event: {type(event).__name__}")
            logging.info(f"🔍 Event final: {event.is_final_response()}")
            if event.is_final_response():
                response = ''
                if (
                    event.content
                    and event.content.parts
                    and event.content.parts[0].text
                ):
                    response = '\n'.join(
                        [p.text for p in event.content.parts if p.text]
                    )
                elif (
                    event.content
                    and event.content.parts
                    and any(
                        [
                            True
                            for p in event.content.parts
                            if p.function_response
                        ]
                    )
                ):
                    response = next(
                        p.function_response.model_dump()
                        for p in event.content.parts
                    )
                logging.info(f"✅ ROUTER AGENT: Final response ready")
                logging.info(f"📄 Response content: {response}")
                logging.info("="*40)
                yield {
                    'is_task_complete': True,
                    'content': response,
                }
            else:
                logging.info("⏳ ROUTER AGENT: Processing in progress...")
                yield {
                    'is_task_complete': False,
                    'updates': self.get_processing_message(),
                }