"""SQLAlchemy async implementation of AgentRepository."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.agents.entity import Agent
from app.domain.agents.exceptions import (
    AgentAlreadyExists,
    AgentIsActive,
    AgentNotFound,
)
from app.domain.agents.repository import AgentRepository
from app.models.agent import AgentStatus, BotConfig


def _to_entity(orm: BotConfig) -> Agent:
    """Map ORM row → domain entity (all columns, nullable as | None)."""
    return Agent(
        id=orm.id,
        name=orm.name,
        llm_model=orm.llm_model,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        status=orm.status.value,
        description=orm.description,
        deleted_at=orm.deleted_at,
        phone_account_id=orm.phone_account_id,
    )


class SQLAgentRepository(AgentRepository):
    """Persistence adapter for Agent using BotConfig and AsyncSession.

    Commits are performed by the caller (service/use case). This repo uses
    flush/refresh only so IDs and defaults are available before commit.

    delete() performs a hard SQL DELETE (cascade); raises AgentIsActive if
    status is active. get/list filter rows with deleted_at IS NULL (column
    reserved for possible soft-delete flows; current API delete removes the row).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, id: UUID) -> Agent | None:
        result = await self._session.execute(
            select(BotConfig)
            .where(BotConfig.id == id)
            .where(BotConfig.deleted_at.is_(None))
        )
        orm = result.scalar_one_or_none()
        return _to_entity(orm) if orm is not None else None

    async def list(
        self,
        status: str | None,
        offset: int,
        limit: int,
        search: str | None = None,
    ) -> list[Agent]:
        stmt = (
            select(BotConfig)
            .where(BotConfig.deleted_at.is_(None))
            .order_by(BotConfig.created_at.desc())
        )
        if status is not None:
            stmt = stmt.where(BotConfig.status == AgentStatus(status))
        if search is not None and search.strip():
            stmt = stmt.where(BotConfig.name.ilike(f"%{search.strip()}%"))
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [_to_entity(row) for row in result.scalars().all()]

    async def count(
        self,
        status: str | None = None,
        search: str | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(BotConfig)
            .where(BotConfig.deleted_at.is_(None))
        )
        if status is not None:
            stmt = stmt.where(BotConfig.status == AgentStatus(status))
        if search is not None and search.strip():
            stmt = stmt.where(BotConfig.name.ilike(f"%{search.strip()}%"))
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, agent: Agent) -> Agent:
        orm = BotConfig(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            llm_model=agent.llm_model,
            deleted_at=agent.deleted_at,
            status=AgentStatus(agent.status),
            phone_account_id=agent.phone_account_id,
        )
        self._session.add(orm)
        try:
            await self._session.flush()
        except IntegrityError as e:
            try:
                self._session.expunge(orm)
            except InvalidRequestError:
                pass  # instance already not in session (e.g. async flush)
            raise AgentAlreadyExists(
                f"Agent with name {agent.name!r} already exists"
            ) from e
        await self._session.refresh(orm)
        return _to_entity(orm)

    async def update(self, agent: Agent) -> Agent:
        # Explicit assignment on a loaded row avoids merge() ambiguities and
        # keeps updated_at behavior driven by ORM onupdate where configured.
        result = await self._session.execute(
            select(BotConfig).where(BotConfig.id == agent.id)
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            raise AgentNotFound(f"Agent not found for update: {agent.id}")
        orm.name = agent.name
        orm.description = agent.description
        orm.llm_model = agent.llm_model
        orm.status = AgentStatus(agent.status)
        orm.deleted_at = agent.deleted_at
        orm.phone_account_id = agent.phone_account_id
        try:
            await self._session.flush()
        except IntegrityError:
            raise AgentAlreadyExists(
                f"Agent with name {agent.name!r} already exists"
            ) from None
        await self._session.refresh(orm)
        return _to_entity(orm)

    async def delete(self, id: UUID) -> None:
        # Hard delete so cascade removes prompt_versions, agent_tools, documents, use_cases.
        result = await self._session.execute(
            select(BotConfig).where(BotConfig.id == id)
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            raise AgentNotFound(f"Agent not found for delete: {id}")
        if orm.status == AgentStatus.active:
            raise AgentIsActive("Desactívalo antes de eliminarlo")
        await self._session.delete(orm)
        await self._session.flush()

    async def change_status(self, id: UUID, new_status: str) -> Agent:
        raise NotImplementedError("implement in phase 9")
