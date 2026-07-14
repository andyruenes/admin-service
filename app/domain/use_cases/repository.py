"""UseCase repository port (abstract). Infrastructure implements."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.use_cases.entity import UseCase


class UseCaseRepository(ABC):
    """Persistence port for UseCase (scoped by agent)."""

    @abstractmethod
    async def get(self, id: UUID) -> UseCase | None:
        """Return use case by id, or None if not found."""

    @abstractmethod
    async def list_by_agent(
        self,
        agent_id: UUID,
        offset: int,
        limit: int,
        search: str | None = None,
    ) -> list[UseCase]:
        """Return a page of use cases for the given agent; optional search on question/answer."""

    @abstractmethod
    async def create(self, use_case: UseCase) -> UseCase:
        """Persist a new use case; return the persisted entity."""

    @abstractmethod
    async def update(self, use_case: UseCase) -> UseCase:
        """Persist changes to an existing use case."""

    @abstractmethod
    async def delete(self, id: UUID) -> None:
        """Remove use case by id."""

    @abstractmethod
    async def get_random(self, agent_id: UUID, limit: int) -> list[UseCase]:
        """Return up to limit random use cases for the agent."""
