import pytest
import respx
import httpx
from uuid import uuid4
import json

from a2a.types import (
    Message, MessageSendParams, Task, TaskState, TextPart, AgentCard, 
    AgentCapabilities, AgentSkill, TaskStatus, Artifact
)
from app.remote_agent_connection import RemoteAgentConnections

pytestmark = pytest.mark.asyncio

@pytest.fixture
def remote_agent_card() -> AgentCard:
    """Provides a standard agent card for the remote agent."""
    return AgentCard(
        name="TestRemoteAgent",
        description="A test agent.",
        version="1.0.0",
        url="http://remote-agent.test",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[AgentSkill(id="test", name="test", description="test", tags=[])],
    )

@pytest.fixture
def remote_connection(
    http_client: httpx.AsyncClient, remote_agent_card: AgentCard
) -> RemoteAgentConnections:
    """Provides a RemoteAgentConnections instance."""
    return RemoteAgentConnections(http_client, remote_agent_card)


@respx.mock
async def test_send_message_receives_message(
    remote_connection: RemoteAgentConnections, remote_agent_card: AgentCard
):
    """
    Tests that send_message correctly handles a direct Message response.
    """
    # Arrange
    message_id = str(uuid4())
    response_message = Message(
        messageId=message_id,
        role="agent", 
        parts=[TextPart(text="Direct response")]
    )
    request_params = MessageSendParams(message=Message(role="user", parts=[], messageId=str(uuid4())))
    
    # Mock the correct URL that A2AClient will use
    respx.post(remote_agent_card.url).mock(
        return_value=httpx.Response(200, json={
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": response_message.model_dump(mode='json')
        })
    )

    # Act
    result = await remote_connection.send_message(request_params, None, False)

    # Assert
    assert isinstance(result, Message)
    assert result.parts[0].root.text == "Direct response"

@respx.mock
async def test_send_message_receives_completed_task(
    remote_connection: RemoteAgentConnections, remote_agent_card: AgentCard
):
    """
    Tests that send_message correctly handles a Task response that is completed.
    """
    # Arrange
    task_id = str(uuid4())
    context_id = str(uuid4())
    response_task = Task(
        id=task_id,
        contextId=context_id,
        status=TaskStatus(state=TaskState.completed),
        artifacts=[
            Artifact(
                artifactId=str(uuid4()),
                parts=[TextPart(text="Task finished.")]
            )
        ]
    )
    request_params = MessageSendParams(message=Message(role="user", parts=[], messageId=str(uuid4())))
    
    # Mock the correct URL that A2AClient will use
    respx.post(remote_agent_card.url).mock(
        return_value=httpx.Response(200, json={
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": response_task.model_dump(mode='json')
        })
    )

    # Act
    result = await remote_connection.send_message(request_params, None, False)

    # Assert
    assert isinstance(result, Task)
    assert result.id == task_id
    assert result.status.state == TaskState.completed 