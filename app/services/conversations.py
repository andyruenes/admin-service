"""Application service for Conversation aggregate — calls conversation-service."""

import logging
from datetime import datetime
from typing import Any

import httpx

from app.schemas.conversations import ClientListItem, UserConversationListItem

logger = logging.getLogger(__name__)


class ConversationService:
    """Orchestrates calls to conversation-service for admin endpoints."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        conversation_service_url: str,
    ) -> None:
        self._http_client = http_client
        self._conversation_service_url = conversation_service_url.rstrip("/")

    async def list_clients(
        self,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[ClientListItem]:
        """Call conversation-service to get clients statistics."""
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if search:
            params["search"] = search

        try:
            response = await self._http_client.get(
                f"{self._conversation_service_url}/admin/clients",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            return [ClientListItem(**item) for item in data["items"]]
        except httpx.HTTPError as exc:
            logger.exception(
                "Failed to fetch clients from conversation-service: %s", exc
            )
            raise

    async def count_clients(self, search: str | None = None) -> int:
        """Call conversation-service to get total clients count."""
        params: dict[str, Any] = {}
        if search:
            params["search"] = search

        try:
            response = await self._http_client.get(
                f"{self._conversation_service_url}/admin/clients/count",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            return data["total"]
        except httpx.HTTPError as exc:
            logger.exception(
                "Failed to fetch clients count from conversation-service: %s", exc
            )
            raise

    async def list_user_conversations(
        self,
        user_id: str,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[UserConversationListItem]:
        params: dict[str, Any] = {
            "offset": offset,
            "limit": limit,
        }
        if status:
            params["status"] = status
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()

        try:
            response = await self._http_client.get(
                f"{self._conversation_service_url}/admin/clients/{user_id}/conversations",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            return [UserConversationListItem(**item) for item in data["items"]]
        except httpx.HTTPError as exc:
            logger.exception("Failed to fetch user conversations: %s", exc)
            raise

    async def get_conversation_detail(self, session_id: str) -> dict[str, Any] | None:
        try:
            response = await self._http_client.get(
                f"{self._conversation_service_url}/admin/conversations/{session_id}",
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.exception("Failed to fetch conversation detail: %s", exc)
            raise

    async def count_user_conversations(
        self,
        user_id: str,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()

        try:
            response = await self._http_client.get(
                f"{self._conversation_service_url}/admin/clients/{user_id}/conversations/count",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            return data["total"]
        except httpx.HTTPError as exc:
            logger.exception("Failed to count user conversations: %s", exc)
            raise

    async def count_open_conversations(self) -> int:
        try:
            response = await self._http_client.get(
                f"{self._conversation_service_url}/admin/conversations/count",
            )
            response.raise_for_status()
            data = response.json()
            return data["count"]
        except httpx.HTTPError as exc:
            logger.exception(
                "Failed to count open conversations from conversation-service: %s", exc
            )
            raise

    async def get_metrics(self) -> dict[str, int]:
        try:
            response = await self._http_client.get(
                f"{self._conversation_service_url}/admin/conversations/metrics",
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.exception(
                "Failed to fetch conversation metrics from conversation-service: %s",
                exc,
            )
            raise

    async def get_cost_breakdown(self) -> dict:
        try:
            response = await self._http_client.get(
                f"{self._conversation_service_url}/admin/costs/breakdown",
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.exception(
                "Failed to fetch cost breakdown from conversation-service: %s", exc
            )
            raise

    async def list_organizations_costs(
        self,
        month: int | None = None,
        year: int | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Call conversation-service to get organizations cost statistics."""
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if month:
            params["month"] = month
        if year:
            params["year"] = year

        try:
            response = await self._http_client.get(
                f"{self._conversation_service_url}/admin/costs/organizations",
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.exception(
                "Failed to fetch organizations costs from conversation-service: %s", exc
            )
            raise

    async def list_organization_conversations_cost(
        self,
        organization_id: str,
        month: int | None = None,
        year: int | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Call conversation-service to get organization conversations cost breakdown."""
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if month:
            params["month"] = month
        if year:
            params["year"] = year

        try:
            response = await self._http_client.get(
                f"{self._conversation_service_url}/admin/costs/organizations/{organization_id}/conversations",
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.exception("Failed to fetch organization conversations cost: %s", exc)
            raise
