import pytest
import respx
import httpx
from fastapi import status
from fastapi.testclient import TestClient

from app.fastapi_host_server import app
from a2a.types import AgentCard

pytestmark = pytest.mark.asyncio

@respx.mock
async def test_list_agents_initially_empty():
    """
    Tests that GET /agents returns an empty list initially.
    """
    with TestClient(app) as client:
        response = client.get("/agents")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

@respx.mock
async def test_add_and_remove_agent(mock_agent_card: AgentCard):
    """
    Tests adding a new agent via POST /agents and then removing it via DELETE /agents/{agent_name}.
    """
    with TestClient(app) as client:
        # Mock the remote agent's card endpoint
        card_route = respx.get(mock_agent_card.url).mock(
            return_value=httpx.Response(
                status.HTTP_200_OK, json=mock_agent_card.model_dump()
            )
        )

        # Add the agent
        add_response = client.post("/agents", json={"address": mock_agent_card.url})
        assert add_response.status_code == status.HTTP_201_CREATED
        assert add_response.json() == {"message": "Agent added", "name": mock_agent_card.name}
        assert card_route.called

        # Verify the agent is listed
        list_response = client.get("/agents")
        assert list_response.status_code == status.HTTP_200_OK
        assert list_response.json() == [
            {"name": mock_agent_card.name, "description": mock_agent_card.description}
        ]

        # Remove the agent
        remove_response = client.delete(f"/agents/{mock_agent_card.name}")
        assert remove_response.status_code == status.HTTP_200_OK
        assert remove_response.json() == {"message": "Agent removed", "name": mock_agent_card.name}

        # Verify the agent is no longer listed
        final_list_response = client.get("/agents")
        assert final_list_response.status_code == status.HTTP_200_OK
        assert final_list_response.json() == []

async def test_add_duplicate_agent(mock_agent_card: AgentCard):
    """
    Tests that adding a duplicate agent address returns a 400 Bad Request.
    """
    with TestClient(app) as client:
        with respx.mock:
            card_route = respx.get(mock_agent_card.url).mock(
                return_value=httpx.Response(
                    status.HTTP_200_OK, json=mock_agent_card.model_dump()
                )
            )

            # Add the agent for the first time
            client.post("/agents", json={"address": mock_agent_card.url})
            assert card_route.called

            # Attempt to add the same agent again
            response = client.post("/agents", json={"address": mock_agent_card.url})
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "already registered" in response.json()["detail"] 