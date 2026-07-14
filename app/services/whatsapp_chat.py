"""Thin wrapper around agent-service's /agent/test/query endpoint."""

import logging

import httpx

logger = logging.getLogger(__name__)


class WhatsappChatService:
    """Sends a message + history to agent-service and returns the LLM response."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http_client = http_client

    async def get_response(
        self,
        agent_id: str,
        phone_number: str,
        message: str,
        history: list[dict[str, str]],
    ) -> str:
        payload = {
            "agent_id": agent_id,
            "session_id": f"wa_{phone_number}",
            "message": message,
            "history": history,
        }
        response = await self._http_client.post("/agent/test/query", json=payload)
        response.raise_for_status()
        return response.json()["response"]
