"""Application service for Agent aggregate — orchestrates repo + transaction boundary."""

import logging
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

import httpx

from app.domain.agents.entity import Agent
from app.domain.agents.exceptions import (
    AgentIsActive,
    AgentNotFound,
    InvalidStatusTransition,
    PhoneAccountAlreadyLinked,
    PhoneAccountNotLinked,
)
from app.domain.agents.repository import AgentRepository
from app.domain.documents.exceptions import AgentServiceUnavailable
from app.grpc.generated.hermes.v2 import whatsapp_pb2
from app.grpc.hermes.client import HermesClient

logger = logging.getLogger(__name__)


class _CommitSession(Protocol):
    """Unit-of-work boundary; implemented by AsyncSession.commit in infrastructure."""

    async def commit(self) -> None: ...


_ALLOWED_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {("draft", "active"), ("active", "inactive")}
)


class AgentService:
    """Orchestrates Agent persistence via AgentRepository; commits on write paths."""

    def __init__(
        self,
        repo: AgentRepository,
        session: _CommitSession,
        http_client: httpx.AsyncClient,
        agent_service_url: str,
        hermes_client: HermesClient | None = None,
    ) -> None:
        self._repo = repo
        self._session = session
        self._http_client = http_client
        self._agent_service_url = agent_service_url.rstrip("/")
        self._hermes_client = hermes_client

    async def create(self, data: dict[str, Any]) -> Agent:
        """Build entity, persist via repo, commit. Duplicate name surfaces from DB/repo."""
        now = datetime.now(UTC)
        agent = Agent(
            id=data.get("id") or uuid4(),
            name=data["name"],
            llm_model=data["llm_model"],
            created_at=now,
            updated_at=now,
            status=data.get("status", "draft"),
            description=data.get("description"),
            deleted_at=data.get("deleted_at"),
        )
        created = await self._repo.create(agent)
        await self._session.commit()
        return created

    async def get(self, id: UUID) -> Agent:
        entity = await self._repo.get(id)
        if entity is None:
            raise AgentNotFound(f"Agent not found: {id}")
        return entity

    async def list(
        self,
        status: str | None,
        offset: int,
        limit: int,
        search: str | None = None,
    ) -> list[Agent]:
        return await self._repo.list(status, offset, limit, search=search)

    async def count(
        self,
        status: str | None = None,
        search: str | None = None,
    ) -> int:
        return await self._repo.count(status=status, search=search)

    async def update(self, id: UUID, data: dict[str, Any]) -> Agent:
        """Partial update: only keys present in data are applied; others unchanged."""
        current = await self.get(id)
        name = data["name"] if "name" in data else current.name
        llm_model = data["llm_model"] if "llm_model" in data else current.llm_model
        status = data["status"] if "status" in data else current.status
        description = (
            data["description"] if "description" in data else current.description
        )
        deleted_at = data["deleted_at"] if "deleted_at" in data else current.deleted_at
        patched = Agent(
            id=current.id,
            name=name,
            llm_model=llm_model,
            created_at=current.created_at,
            updated_at=current.updated_at,
            status=status,
            description=description,
            deleted_at=deleted_at,
            phone_account_id=current.phone_account_id,
        )
        updated = await self._repo.update(patched)
        await self._session.commit()
        return updated

    async def change_status(self, id: UUID, new_status: str) -> Agent:
        """Validate transition (draft→active, active→inactive only), update, commit."""
        current = await self.get(id)
        if (current.status, new_status) not in _ALLOWED_TRANSITIONS:
            raise InvalidStatusTransition(
                f"Invalid status transition from {current.status!r} to {new_status!r}"
            )
        patched = Agent(
            id=current.id,
            name=current.name,
            llm_model=current.llm_model,
            created_at=current.created_at,
            updated_at=current.updated_at,
            status=new_status,
            description=current.description,
            deleted_at=current.deleted_at,
            phone_account_id=current.phone_account_id,
        )
        updated = await self._repo.update(patched)
        await self._session.commit()
        return updated

    async def create_phone_account(self, agent_id: UUID) -> str:
        """Call hermes CreateAccount with chatbotId=agent_id and persist the returned accountId."""
        agent = await self.get(agent_id)
        if agent.phone_account_id is not None:
            raise PhoneAccountAlreadyLinked(
                f"Agent {agent_id} already has a phone account: {agent.phone_account_id}"
            )
        assert self._hermes_client is not None, "HermesClient not injected"
        response = await self._hermes_client.whatsapp.CreateAccount(
            whatsapp_pb2.CreateAccountRequest(chatbotId=str(agent_id))
        )
        if not response.success:
            raise RuntimeError(f"Hermes CreateAccount failed: {response.message}")
        agent.phone_account_id = response.accountId
        await self._repo.update(agent)
        await self._session.commit()
        return response.accountId

    async def request_qr(self, agent_id: UUID) -> None:
        """Trigger QR code generation for the agent's linked phone account."""
        agent = await self.get(agent_id)
        if agent.phone_account_id is None:
            raise PhoneAccountNotLinked(f"Agent {agent_id} has no linked phone account")
        assert self._hermes_client is not None, "HermesClient not injected"
        response = await self._hermes_client.whatsapp.RequestQR(
            whatsapp_pb2.RequestQRRequest(accountId=agent.phone_account_id)
        )
        if not response.success:
            raise RuntimeError(f"Hermes RequestQR failed: {response.message}")

    async def activate_phone_account(self, agent_id: UUID) -> None:
        """Activate the hermes WhatsApp account and queue the session-start job."""
        agent = await self.get(agent_id)
        if agent.phone_account_id is None:
            raise PhoneAccountNotLinked(f"Agent {agent_id} has no linked phone account")
        assert self._hermes_client is not None, "HermesClient not injected"
        response = await self._hermes_client.whatsapp.ActivateAccount(
            whatsapp_pb2.ActivateAccountRequest(
                accountId=agent.phone_account_id,
            )
        )
        if not response.success:
            raise RuntimeError(f"Hermes ActivateAccount failed: {response.message}")

    async def get_bot_status(self, agent_id: UUID) -> dict:
        """Return current bot status from hermes for the agent's linked phone account."""
        agent = await self.get(agent_id)
        if agent.phone_account_id is None:
            raise PhoneAccountNotLinked(f"Agent {agent_id} has no linked phone account")
        assert self._hermes_client is not None, "HermesClient not injected"
        response = await self._hermes_client.whatsapp.GetBotStatus(
            whatsapp_pb2.GetBotStatusRequest(accountId=agent.phone_account_id)
        )
        return {
            "account_id": response.accountId,
            "status": response.status,
            "phone_number": response.phoneNumber,
            "qr_code": response.qrCode,
        }

    async def delete(self, id: UUID) -> None:
        """Hard delete (cascade); raise if agent is active. Delete IA vectors first, then DB."""
        current = await self.get(id)
        if current.status == "active":
            raise AgentIsActive("Desactívalo antes de eliminarlo")
        try:
            response = await self._http_client.delete(
                f"{self._agent_service_url}/agent/agents/{id}/vectors"
            )
            if response.status_code >= 400 and response.status_code != 404:
                raise AgentServiceUnavailable(
                    f"agent-service returned {response.status_code} for agent vector delete"
                )
        except httpx.HTTPError as exc:
            logger.exception(
                "Agent vector delete failed for %s, agent row left unchanged: %s",
                id,
                exc,
            )
            raise AgentServiceUnavailable(
                "IA service unavailable; agent not deleted"
            ) from exc
        await self._repo.delete(id)
        await self._session.commit()
