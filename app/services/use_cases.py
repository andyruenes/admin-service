"""Application service for UseCase aggregate — agent-scoped CRUD (DocumentService pattern)."""

from __future__ import annotations

import builtins
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.domain.use_cases.entity import UseCase
from app.domain.use_cases.exceptions import UseCaseNotFound
from app.domain.use_cases.repository import UseCaseRepository


class _CommitSession(Protocol):
    async def commit(self) -> None: ...


# Commit only after create/update/delete; get/list stay read-only in the same tx.


class UseCaseService:
    """All operations scoped by agent_id; get() enforces ownership."""

    def __init__(self, repo: UseCaseRepository, session: _CommitSession) -> None:
        self._repo = repo
        self._session = session

    async def _get_for_agent(self, agent_id: UUID, id: UUID) -> UseCase:
        entity = await self._repo.get(id)
        if entity is None:
            raise UseCaseNotFound(f"Use case not found: {id}")
        if entity.agent_id != agent_id:
            raise UseCaseNotFound(
                f"Use case {id} belongs to agent {entity.agent_id}, not {agent_id}"
            )
        return entity

    async def create(self, agent_id: UUID, data: dict[str, Any]) -> UseCase:
        now = datetime.now(UTC)
        use_case = UseCase(
            id=data.get("id") or uuid4(),
            agent_id=agent_id,
            question=data["pregunta"],
            answer=data["respuesta"],
            created_at=now,
            updated_at=now,
        )
        created = await self._repo.create(use_case)
        await self._session.commit()
        return created

    async def get(self, agent_id: UUID, id: UUID) -> UseCase:
        return await self._get_for_agent(agent_id, id)

    async def list(
        self,
        agent_id: UUID,
        offset: int,
        limit: int,
        search: str | None = None,
    ) -> builtins.list[UseCase]:
        return await self._repo.list_by_agent(agent_id, offset, limit, search=search)

    async def update(self, agent_id: UUID, id: UUID, data: dict[str, Any]) -> UseCase:
        """Partial update on question/answer only; timestamps from repo after flush."""
        current = await self._get_for_agent(agent_id, id)
        question = data["pregunta"] if "pregunta" in data else current.question
        answer = data["respuesta"] if "respuesta" in data else current.answer
        patched = UseCase(
            id=current.id,
            agent_id=agent_id,
            question=question,
            answer=answer,
            created_at=current.created_at,
            updated_at=current.updated_at,
        )
        updated = await self._repo.update(patched)
        await self._session.commit()
        return updated

    async def delete(self, agent_id: UUID, id: UUID) -> None:
        await self._get_for_agent(agent_id, id)
        await self._repo.delete(id)
        await self._session.commit()

    async def get_random(self, agent_id: UUID, limit: int) -> builtins.list[UseCase]:
        """Return random use cases for the agent; read-only, no commit."""
        return await self._repo.get_random(agent_id, limit)
