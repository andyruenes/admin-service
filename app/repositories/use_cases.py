"""SQLAlchemy async implementation of UseCaseRepository."""

from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.domain.use_cases.entity import UseCase
from app.domain.use_cases.exceptions import UseCaseNotFound
from app.domain.use_cases.repository import UseCaseRepository
from app.models.use_case import UseCase as UseCaseORM


def _to_entity(orm: UseCaseORM) -> UseCase:
    """Map ORM row → domain entity."""
    return UseCase(
        id=orm.id,
        agent_id=orm.agent_id,
        question=orm.question,
        answer=orm.answer,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class SQLUseCaseRepository(UseCaseRepository):
    """Persistence adapter for UseCase; list/update scoped by agent_id where
    applicable. get(id) is by PK only — same pattern as DocumentRepository.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, id: UUID) -> UseCase | None:
        result = await self._session.execute(
            select(UseCaseORM).where(UseCaseORM.id == id)
        )
        orm = result.scalar_one_or_none()
        return _to_entity(orm) if orm is not None else None

    async def list_by_agent(
        self,
        agent_id: UUID,
        offset: int,
        limit: int,
        search: str | None = None,
    ) -> list[UseCase]:
        stmt = (
            select(UseCaseORM)
            .where(UseCaseORM.agent_id == agent_id)
            .order_by(UseCaseORM.updated_at.desc())
        )
        if search is not None and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    UseCaseORM.question.ilike(term),
                    UseCaseORM.answer.ilike(term),
                )
            )
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [_to_entity(row) for row in result.scalars().all()]

    async def create(self, use_case: UseCase) -> UseCase:
        orm = UseCaseORM(
            id=use_case.id,
            agent_id=use_case.agent_id,
            question=use_case.question,
            answer=use_case.answer,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _to_entity(orm)

    async def update(self, use_case: UseCase) -> UseCase:
        result = await self._session.execute(
            select(UseCaseORM).where(UseCaseORM.id == use_case.id)
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            raise UseCaseNotFound(f"Use case not found for update: {use_case.id}")
        if orm.agent_id != use_case.agent_id:
            raise UseCaseNotFound(
                f"Use case {use_case.id} belongs to agent {orm.agent_id}, "
                f"not {use_case.agent_id}"
            )
        orm.question = use_case.question
        orm.answer = use_case.answer
        await self._session.flush()
        await self._session.refresh(orm)
        return _to_entity(orm)

    async def delete(self, id: UUID) -> None:
        result = await self._session.execute(
            select(UseCaseORM).where(UseCaseORM.id == id)
        )
        if result.scalar_one_or_none() is None:
            raise UseCaseNotFound(f"Use case not found for delete: {id}")
        await self._session.execute(delete(UseCaseORM).where(UseCaseORM.id == id))
        await self._session.flush()

    async def get_random(self, agent_id: UUID, limit: int) -> list[UseCase]:
        stmt = (
            select(UseCaseORM)
            .where(UseCaseORM.agent_id == agent_id)
            .order_by(func.random())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_to_entity(row) for row in result.scalars().all()]
