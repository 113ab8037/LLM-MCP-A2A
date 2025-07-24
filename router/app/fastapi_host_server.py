import asyncio
import logging
from typing import List, AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .host_agent import HostAgent, A2ACardResolver

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

http_client_instance: httpx.AsyncClient | None = None
host_agent_instance: HostAgent | None = None
_agent_lock = asyncio.Lock()  # protects modifications of remote agents

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage the lifespan of the application."""
    global http_client_instance, host_agent_instance
    http_client_instance = httpx.AsyncClient()
    host_agent_instance = HostAgent(remote_agent_addresses=[], http_client=http_client_instance)
    logger.info("🚀 HostAgent and FastAPI server started")
    
    yield
    
    if http_client_instance:
        await http_client_instance.aclose()
    logger.info("👋 FastAPI server shutdown completed")

app = FastAPI(title="HostAgent Manager", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


class AgentAddress(BaseModel):
    """Payload model for adding a new remote agent by its HTTP address."""

    address: str


@app.get("/agents", response_model=List[dict])
async def list_agents():
    """Return list of currently registered remote agents.

    Each item includes the agent name and description.
    """

    if host_agent_instance is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="HostAgent not initialised",
        )
    return host_agent_instance.list_remote_agents()


@app.post("/agents", status_code=status.HTTP_201_CREATED)
async def add_agent(agent: AgentAddress):
    """Add a new remote agent by URL.

    The card is fetched from the remote agent and registered inside HostAgent.
    """

    if host_agent_instance is None or http_client_instance is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="HostAgent not initialised",
        )

    async with _agent_lock:
        if agent.address in host_agent_instance.remote_agent_addresses:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Agent address already registered",
            )

        try:
            # Fetch the agent card from the remote agent
            resolver = A2ACardResolver(http_client_instance, agent.address)
            card = await resolver.get_agent_card()
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "❌ Failed to resolve agent card from %s", agent.address
            )
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))

        # Register within HostAgent internal structures
        host_agent_instance.remote_agent_addresses.append(agent.address)
        host_agent_instance.register_agent_card(card)
        logger.info(
            "✅ Added remote agent '%s' (%s)",
            card.name,
            agent.address,
        )

    return {"message": "Agent added", "name": card.name}


@app.delete("/agents/{agent_name}")
async def remove_agent(agent_name: str):
    """Remove a remote agent by its *name*.

    The name corresponds to the agent card name, not its base URL.
    """

    if host_agent_instance is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="HostAgent not initialised",
        )

    async with _agent_lock:
        try:
            host_agent_instance.remove_agent_card(agent_name)
        except ValueError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

        logger.info("🗑️ Removed remote agent '%s'", agent_name)
    return {"message": "Agent removed", "name": agent_name}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.fastapi_host_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    ) 