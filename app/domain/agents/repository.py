"""Agent repository port (abstract). Infrastructure implements."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.agents.entity import Agent


class AgentRepository(ABC):
    """Persistence port for the Agent aggregate."""

    @abstractmethod
    async def get(self, id: UUID) -> Agent | None:
        """Return agent by id, or None if not found."""

    @abstractmethod
    async def list(
        self,
        status: str | None,
        offset: int,
        limit: int,
        search: str | None = None,
    ) -> list[Agent]:
        """Return a page of agents, optionally filtered by status and name search."""

    @abstractmethod
    async def count(
        self,
        status: str | None = None,
        search: str | None = None,
    ) -> int:
        """Return total number of agents matching the same filters as list (excluding offset/limit)."""

    @abstractmethod
    async def create(self, agent: Agent) -> Agent:
        """Persist a new agent; return the persisted entity."""

    @abstractmethod
    async def update(self, agent: Agent) -> Agent:
        """Persist changes to an existing agent."""

    @abstractmethod
    async def delete(self, id: UUID) -> None:
        """Remove agent by id (or soft-delete per infrastructure policy)."""
