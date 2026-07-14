"""Prompt version repository port (abstract). Infrastructure implements."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.prompts.entity import PromptVersion


class PromptRepository(ABC):
    """Persistence port for PromptVersion (scoped by agent).

    Ensures at most one active prompt per agent when implementing set_active
    and related writes.
    """

    @abstractmethod
    async def get(self, id: UUID) -> PromptVersion | None:
        """Return prompt version by id, or None if not found."""

    @abstractmethod
    async def list_by_agent(
        self,
        agent_id: UUID,
        offset: int,
        limit: int,
    ) -> list[PromptVersion]:
        """Return a page of prompt versions for the given agent."""

    @abstractmethod
    async def create(self, prompt_version: PromptVersion) -> PromptVersion:
        """Persist a new prompt version; return the persisted entity."""

    @abstractmethod
    async def update(self, prompt_version: PromptVersion) -> PromptVersion:
        """Persist changes to an existing prompt version."""

    @abstractmethod
    async def delete(self, id: UUID) -> None:
        """Remove prompt version by id."""

    @abstractmethod
    async def set_active(self, id: UUID) -> None:
        """Mark this version active and deactivate others for the same agent."""
