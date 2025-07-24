import pytest
from a2a.types import AgentCard
from app.host_agent import HostAgent

pytestmark = pytest.mark.asyncio

async def test_host_agent_initialization(host_agent: HostAgent):
    """
    Tests that the HostAgent is initialized correctly.
    """
    assert host_agent.remote_agent_connections == {}
    assert host_agent.cards == {}
    assert host_agent.list_remote_agents() == []

async def test_register_agent_card(host_agent: HostAgent, mock_agent_card: AgentCard):
    """
    Tests that a new agent card can be registered successfully.
    """
    host_agent.register_agent_card(mock_agent_card)
    
    assert mock_agent_card.name in host_agent.remote_agent_connections
    assert mock_agent_card.name in host_agent.cards
    
    agent_info = host_agent.list_remote_agents()[0]
    assert agent_info["name"] == mock_agent_card.name
    assert agent_info["description"] == mock_agent_card.description

async def test_remove_agent_card(host_agent: HostAgent, mock_agent_card: AgentCard):
    """
    Tests that a registered agent can be removed successfully.
    """
    host_agent.register_agent_card(mock_agent_card)
    assert mock_agent_card.name in host_agent.remote_agent_connections

    host_agent.remove_agent_card(mock_agent_card.name)
    
    assert mock_agent_card.name not in host_agent.remote_agent_connections
    assert mock_agent_card.name not in host_agent.cards
    assert host_agent.list_remote_agents() == []

async def test_remove_nonexistent_agent_raises_error(host_agent: HostAgent):
    """
    Tests that attempting to remove a non-existent agent raises a ValueError.
    """
    with pytest.raises(ValueError, match="Agent NonExistentAgent not found"):
        host_agent.remove_agent_card("NonExistentAgent") 