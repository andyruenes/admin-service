"""In-memory PromptRepository fake — at most one active per agent, save_as_active, restore_version."""

from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID

import uuid6

from app.domain.prompts.entity import PromptVersion
from app.domain.prompts.exceptions import NoActivePrompt, PromptNotFound
from app.domain.prompts.repository import PromptRepository


class InMemoryPromptRepository(PromptRepository):
    """Fake backed by list[PromptVersion]. Enforces single active per agent."""

    def __init__(self) -> None:
        self.store: list[PromptVersion] = []

    def _by_id(self, id: UUID) -> PromptVersion | None:
        for p in self.store:
            if p.id == id:
                return p
        return None

    def _by_agent(self, agent_id: UUID) -> list[PromptVersion]:
        return [p for p in self.store if p.agent_id == agent_id]

    async def get(self, id: UUID) -> PromptVersion | None:
        p = self._by_id(id)
        return deepcopy(p) if p is not None else None

    async def list_by_agent(
        self,
        agent_id: UUID,
        offset: int,
        limit: int,
    ) -> list[PromptVersion]:
        items = sorted(
            self._by_agent(agent_id),
            key=lambda p: p.version_number,
            reverse=True,
        )
        page = items[offset : offset + limit]
        return [deepcopy(p) for p in page]

    async def create(self, prompt_version: PromptVersion) -> PromptVersion:
        self.store.append(deepcopy(prompt_version))
        return deepcopy(self.store[-1])

    async def update(self, prompt_version: PromptVersion) -> PromptVersion:
        for i, p in enumerate(self.store):
            if p.id == prompt_version.id:
                self.store[i] = deepcopy(prompt_version)
                return deepcopy(self.store[i])
        raise PromptNotFound(
            f"Prompt version not found for update: {prompt_version.id}"
        )

    async def delete(self, id: UUID) -> None:
        for i, p in enumerate(self.store):
            if p.id == id:
                del self.store[i]
                return
        raise PromptNotFound(f"Prompt version not found for delete: {id}")

    async def set_active(self, id: UUID) -> None:
        target = self._by_id(id)
        if target is None:
            raise PromptNotFound(f"Prompt version not found for set_active: {id}")
        agent_id = target.agent_id
        for i, p in enumerate(self.store):
            if p.agent_id == agent_id:
                self.store[i] = PromptVersion(
                    id=p.id,
                    agent_id=p.agent_id,
                    version_number=p.version_number,
                    content=p.content,
                    created_at=p.created_at,
                    is_active=(p.id == id),
                )
        return

    async def get_active(self, agent_id: UUID) -> PromptVersion:
        for p in self._by_agent(agent_id):
            if p.is_active:
                return deepcopy(p)
        raise NoActivePrompt(f"No active prompt for agent {agent_id}")

    async def list_versions(self, agent_id: UUID, limit: int) -> list[PromptVersion]:
        items = sorted(
            self._by_agent(agent_id),
            key=lambda p: p.version_number,
            reverse=True,
        )[:limit]
        return [deepcopy(p) for p in items]

    async def get_by_version_number(
        self, agent_id: UUID, version_number: int
    ) -> PromptVersion | None:
        for p in self._by_agent(agent_id):
            if p.version_number == version_number:
                return deepcopy(p)
        return None

    async def save_as_active(
        self, agent_id: UUID, content: str, version_number: int
    ) -> PromptVersion:
        for i, p in enumerate(self.store):
            if p.agent_id == agent_id:
                self.store[i] = PromptVersion(
                    id=p.id,
                    agent_id=p.agent_id,
                    version_number=p.version_number,
                    content=p.content,
                    created_at=p.created_at,
                    is_active=False,
                )
        new_id = uuid6.uuid7()
        now = datetime.now(UTC)
        new_prompt = PromptVersion(
            id=new_id,
            agent_id=agent_id,
            version_number=version_number,
            content=content,
            created_at=now,
            is_active=True,
        )
        self.store.append(new_prompt)
        return deepcopy(new_prompt)

    async def restore_version(
        self, agent_id: UUID, version_number: int
    ) -> PromptVersion:
        source = await self.get_by_version_number(agent_id, version_number)
        if source is None:
            raise PromptNotFound(
                f"No prompt version {version_number} for agent {agent_id}"
            )
        versions = self._by_agent(agent_id)
        next_version = max(p.version_number for p in versions) + 1 if versions else 1
        return await self.save_as_active(agent_id, source.content, next_version)
