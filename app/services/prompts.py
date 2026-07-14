"""Application service for PromptVersion aggregate — agent-scoped + get_active, save_as_active, restore."""

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from app.domain.prompts.entity import PromptVersion
from app.domain.prompts.exceptions import NoActivePrompt, PromptNotFound
from app.domain.prompts.repository import PromptRepository


class _CommitSession(Protocol):
    async def commit(self) -> None: ...


class PromptService:
    """Operations scoped by agent_id; get_active, save_as_active, list_versions, get_version, restore_version."""

    def __init__(self, repo: PromptRepository, session: _CommitSession) -> None:
        self._repo = repo
        self._session = session

    async def get_active(self, agent_id: UUID) -> PromptVersion:
        """Return the active prompt for the agent; raise NoActivePrompt if none."""
        page = await self._repo.list_by_agent(agent_id, 0, 100)
        for p in page:
            if p.is_active:
                return p
        raise NoActivePrompt(f"No active prompt for agent {agent_id}")

    async def get_active_or_empty(self, agent_id: UUID) -> PromptVersion:
        """Return the active prompt, or a sentinel with empty content if none (200, no error)."""
        try:
            return await self.get_active(agent_id)
        except NoActivePrompt:
            return PromptVersion(
                id=uuid4(),
                agent_id=agent_id,
                version_number=0,
                content="",
                created_at=datetime.now(UTC),
                is_active=True,
            )

    async def save_as_active(self, agent_id: UUID, content: str) -> PromptVersion:
        """Create new version and set it active; one commit after create + set_active."""
        page = await self._repo.list_by_agent(agent_id, 0, 1)
        next_version = (page[0].version_number + 1) if page else 1
        now = datetime.now(UTC)
        prompt = PromptVersion(
            id=uuid4(),
            agent_id=agent_id,
            version_number=next_version,
            content=content,
            created_at=now,
            is_active=False,
        )
        created = await self._repo.create(prompt)
        await self._repo.set_active(created.id)
        await self._session.commit()
        entity = await self._repo.get(created.id)
        if entity is None:
            raise PromptNotFound(f"Prompt not found after set_active: {created.id}")
        return entity

    async def list_versions(
        self, agent_id: UUID, limit: int = 10
    ) -> list[PromptVersion]:
        """Return prompt versions for the agent (ordered by version_number desc)."""
        return await self._repo.list_by_agent(agent_id, 0, limit)

    async def get_version(self, agent_id: UUID, version_number: int) -> PromptVersion:
        """Return the prompt version with the given version_number; raise PromptNotFound if missing."""
        page = await self._repo.list_by_agent(agent_id, 0, 1000)
        for p in page:
            if p.version_number == version_number:
                return p
        raise PromptNotFound(f"No prompt version {version_number} for agent {agent_id}")

    async def restore_version(
        self, agent_id: UUID, version_number: int
    ) -> PromptVersion:
        """Create a new version with the same content as the given version and set it active."""
        old = await self.get_version(agent_id, version_number)
        page = await self._repo.list_by_agent(agent_id, 0, 1)
        next_version = (page[0].version_number + 1) if page else 1
        now = datetime.now(UTC)
        new_prompt = PromptVersion(
            id=uuid4(),
            agent_id=agent_id,
            version_number=next_version,
            content=old.content,
            created_at=now,
            is_active=False,
        )
        created = await self._repo.create(new_prompt)
        await self._repo.set_active(created.id)
        await self._session.commit()
        entity = await self._repo.get(created.id)
        if entity is None:
            raise PromptNotFound(f"Prompt not found after set_active: {created.id}")
        return entity
