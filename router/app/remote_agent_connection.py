from typing import Callable
# flake8: noqa
import httpx
import logging
from a2a.client import A2AClient
from a2a.types import (
    AgentCard,
    Task,
    Message,
    MessageSendParams,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
    SendMessageRequest,
    SendStreamingMessageRequest,
    JSONRPCErrorResponse,
)


TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg, AgentCard], Task]


class RemoteAgentConnections:
    """A class to hold the connections to the remote agents."""

    def __init__(self, client: httpx.AsyncClient, agent_card: AgentCard):
        self.agent_client = A2AClient(client, agent_card)
        self.card = agent_card
        self.pending_tasks = set()

    def get_agent(self) -> AgentCard:
        return self.card

    async def send_message(
        self,
        request: MessageSendParams,
        task_callback: TaskUpdateCallback | None,
        streaming: bool
    ) -> Task | Message | None:
        # Logging message sending to a remote agent
        logging.info(f"🔗 REMOTE CONNECTION: Sending to {self.card.name}")
        
        # We log message details and context
        message = request.message
        logging.info(f"📝 Message: {message}")
        logging.info(f"📝 Message role: {message.role}")
        logging.info(f"📦 Message parts count: {len(message.parts) if message.parts else 0}")
        logging.info(f"🔑 Message ID: {message.messageId}")
        logging.info(f"🎯 Context ID: {message.contextId}")
        logging.info(f"📋 Task ID: {message.taskId}")
        
        # Logging content size
        if message.parts:
            for i, part in enumerate(message.parts):
                if part and part.root:
                    if hasattr(part.root, 'text') and part.root.text:
                        text_size = len(part.root.text)
                        logging.info(f"📄 Part {i+1} text: {text_size} chars")
                        logging.info(f"📝 Part {i+1} content: {part.root.text[:100]}...")
                    else:
                        logging.info(f"📄 Part {i+1}: {type(part.root).__name__}")
        
        # Logging the configuration
        config = request.configuration
        if config:
            logging.info(f"⚙️ Config output modes: {config.acceptedOutputModes}")
        
        
        if streaming and self.card.capabilities.streaming:
            task = None
            async for response in self.agent_client.send_message_streaming(
                SendStreamingMessageRequest(params=request), http_kwargs={'timeout': 60000}
            ):
                logging.info(f"📨 STREAMING RESPONSE from {self.card.name}")
                logging.info(f"📦 Response type: {type(response.root.result).__name__ if response.root.result else 'Error'}")
                
                if not response.root.result:
                    logging.error(f"❌ Error from {self.card.name}: {response.root.error}")
                    return response.root.error
                    
                # In the case a message is returned, that is the end of the interaction.
                event = response.root.result
                if isinstance(event, Message):
                    logging.info(f"✅ Final message received from {self.card.name}")
                    return event

                # Otherwise we are in the Task + TaskUpdate cycle.
                if task_callback and event:
                    task = task_callback(event, self.card)
                if hasattr(event, 'final') and event.final:
                    logging.info(f"🏁 Final event received from {self.card.name}")
                    break
            return task
        else:  # Non-streaming
            response = await self.agent_client.send_message(
                SendMessageRequest(params=request),
                http_kwargs={"timeout": 60},  # 60s timeout for slow agents
            )
            if isinstance(response.root, JSONRPCErrorResponse):
                return response.root.error
            if isinstance(response.root.result, Message):
                return response.root.result

            if task_callback:
                task_callback(response.root.result, self.card)
            return response.root.result
