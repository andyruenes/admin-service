from __future__ import annotations

import httpx

from app.config import settings


class ConversationClient:
    def __init__(self) -> None:
        self.base_url = settings.CONVERSATION_SERVICE_URL

    async def save_message(
        self,
        user_id: str,
        agent_id: str,
        role: str,
        content: str,
        correlation_id: str | None = None,
    ) -> dict:
        url = f"{self.base_url}/messages"
        payload = {
            "user_id": user_id,
            "agent_id": agent_id,
            "role": role,
            "content": content,
            "correlation_id": correlation_id,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()

    async def get_history(self, user_id: str, limit: int = 20) -> list[dict]:
        url = f"{self.base_url}/sessions/{user_id}/messages?limit={limit}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return [{"role": m["role"], "content": m["content"]} for m in data["items"]]

    async def is_session_derived(self, user_id: str) -> bool:
        """Indica si la sesión del usuario ya fue derivada a un operador humano."""
        url = f"{self.base_url}/sessions/{user_id}/state"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            print(
                f"[WA-CLIENT] GET {url} -> status={resp.status_code} body={resp.text}",
                flush=True,
            )
            resp.raise_for_status()
            return bool(resp.json().get("is_derived", False))

    async def save_operator_message(
        self,
        user_id: str,
        agent_id: str,
        content: str,
    ) -> dict:
        """Guarda un mensaje del operador humano."""
        url = f"{self.base_url}/messages/operator"
        payload = {
            "user_id": user_id,
            "agent_id": agent_id,
            "content": content,
        }
        print(f"[WA-CLIENT] POST {url} payload={payload}", flush=True)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            print(
                f"[WA-CLIENT] POST /messages/operator -> status={resp.status_code} "
                f"body={resp.text}",
                flush=True,
            )
            resp.raise_for_status()
            return resp.json()