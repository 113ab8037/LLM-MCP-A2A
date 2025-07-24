import pytest
import pytest_asyncio
import httpx
from typing import AsyncGenerator, List

from a2a.types import AgentCard, AgentCapabilities, AgentSkill

from app.host_agent import HostAgent

@pytest_asyncio.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Yields an httpx async client for testing."""
    async with httpx.AsyncClient() as client:
        yield client

@pytest.fixture
def mock_agent_card() -> AgentCard:
    """Returns a mock agent card for testing."""
    return AgentCard(
        name="MockAgent",
        description="A mock agent for testing purposes.",
        version="1.0.0",
        url="http://mock-agent.test",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id="mock_skill",
                name="Mock Skill",
                description="A skill for mocking.",
                tags=["mock"],
            )
        ],
    )

@pytest.fixture
def host_agent(http_client: httpx.AsyncClient) -> HostAgent:
    """
    Returns a HostAgent instance for testing, ensuring a clean global state.
    """
    # Clean up global state before each test
    HostAgent._global_remote_agent_connections.clear()
    HostAgent._global_cards.clear()
    HostAgent._global_addresses.clear()
    HostAgent._global_agents = ""

    return HostAgent(remote_agent_addresses=[], http_client=http_client) 