"""SQLAlchemy async implementation of PromptRepository."""

from typing import cast
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.prompts.entity import PromptVersion
from app.domain.prompts.exceptions import PromptNotFound, PromptVersionConflict
from app.domain.prompts.repository import PromptRepository
from app.models.prompt_version import PromptVersion as PromptVersionORM


def _to_entity(orm: PromptVersionORM) -> PromptVersion:
    """Map ORM row → domain entity."""
    return PromptVersion(
        id=orm.id,
        agent_id=orm.agent_id,
        version_number=orm.version_number,
        content=orm.content,
        created_at=orm.created_at,
        is_active=orm.is_active,
    )


class SQLPromptRepository(PromptRepository):
    """Persistence adapter for PromptVersion.

    set_active uses exactly two UPDATEs in the caller's transaction so
    deactivate + activate are atomic with the final commit. The partial
    unique index is a backstop; we still deactivate first to avoid a
    transient double-active if the DB enforced only on commit.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, id: UUID) -> PromptVersion | None:
        result = await self._session.execute(
            select(PromptVersionORM).where(PromptVersionORM.id == id)
        )
        orm = result.scalar_one_or_none()
        return _to_entity(orm) if orm is not None else None

    async def list_by_agent(
        self,
        agent_id: UUID,
        offset: int,
        limit: int,
    ) -> list[PromptVersion]:
        stmt = (
            select(PromptVersionORM)
            .where(PromptVersionORM.agent_id == agent_id)
            .order_by(PromptVersionORM.version_number.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_to_entity(row) for row in result.scalars().all()]

    async def create(self, prompt_version: PromptVersion) -> PromptVersion:
        # version_number is caller-provided (service allocates next number).
        orm = PromptVersionORM(
            id=prompt_version.id,
            agent_id=prompt_version.agent_id,
            version_number=prompt_version.version_number,
            content=prompt_version.content,
            is_active=prompt_version.is_active,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _to_entity(orm)

    async def update(self, prompt_version: PromptVersion) -> PromptVersion:
        result = await self._session.execute(
            select(PromptVersionORM).where(PromptVersionORM.id == prompt_version.id)
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            raise PromptNotFound(
                f"Prompt version not found for update: {prompt_version.id}"
            )
        if orm.agent_id != prompt_version.agent_id:
            raise PromptVersionConflict(
                "Cannot move prompt version to another agent via update"
            )
        orm.version_number = prompt_version.version_number
        orm.content = prompt_version.content
        orm.is_active = prompt_version.is_active
        await self._session.flush()
        await self._session.refresh(orm)
        return _to_entity(orm)

    async def delete(self, id: UUID) -> None:
        result = await self._session.execute(
            select(PromptVersionORM).where(PromptVersionORM.id == id)
        )
        if result.scalar_one_or_none() is None:
            raise PromptNotFound(f"Prompt version not found for delete: {id}")
        await self._session.execute(
            delete(PromptVersionORM).where(PromptVersionORM.id == id)
        )
        await self._session.flush()

    async def list_versions(self, agent_id: UUID, limit: int) -> list[PromptVersion]:
        stmt = (
            select(PromptVersionORM)
            .where(PromptVersionORM.agent_id == agent_id)
            .order_by(PromptVersionORM.version_number.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_to_entity(row) for row in result.scalars().all()]

    async def get_by_version_number(
        self, agent_id: UUID, version_number: int
    ) -> PromptVersion | None:
        result = await self._session.execute(
            select(PromptVersionORM).where(
                PromptVersionORM.agent_id == agent_id,
                PromptVersionORM.version_number == version_number,
            )
        )
        orm = result.scalar_one_or_none()
        return _to_entity(orm) if orm is not None else None

    async def set_active(self, id: UUID) -> None:
        # Exactly 2 UPDATEs, same transaction as caller's commit:
        # 1) Deactivate all rows for the same agent as the target row (subquery
        #    ties to id; if id missing, subquery is empty → no row matches agent_id).
        # 2) Activate the target row; rowcount 0 → id does not exist.
        agent_id_subq = (
            select(PromptVersionORM.agent_id)
            .where(PromptVersionORM.id == id)
            .scalar_subquery()
        )
        await self._session.execute(
            update(PromptVersionORM)
            .where(PromptVersionORM.agent_id == agent_id_subq)
            .values(is_active=False)
        )
        res = await self._session.execute(
            update(PromptVersionORM)
            .where(PromptVersionORM.id == id)
            .values(is_active=True)
        )
        if cast(CursorResult, res).rowcount != 1:
            raise PromptNotFound(f"Prompt version not found for set_active: {id}")
        await self._session.flush()

    async def get_active(self, agent_id: UUID) -> PromptVersion:
        raise NotImplementedError("implement in phase 9")

    async def save_as_active(
        self, agent_id: UUID, content: str, version_number: int
    ) -> PromptVersion:
        raise NotImplementedError("implement in phase 9")

    async def restore_version(
        self, agent_id: UUID, version_number: int
    ) -> PromptVersion:
        raise NotImplementedError("implement in phase 9")
