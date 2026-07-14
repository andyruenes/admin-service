"""SQLAlchemy async implementation of ToolRepository (catalog + agent_tool)."""

from __future__ import annotations

import builtins
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.tools.entity import AgentTool, Tool
from app.domain.tools.exceptions import (
    AgentToolAlreadyAttached,
    AgentToolNotFound,
    ToolAlreadyExists,
    ToolNotFound,
)
from app.domain.tools.repository import ToolRepository
from app.models.agent_tool import AgentTool as AgentToolORM
from app.models.tool import ToolCatalog


def _to_tool_entity(orm: ToolCatalog) -> Tool:
    """Map tools_catalog row → domain Tool."""
    return Tool(
        id=orm.id,
        name=orm.name,
        description=orm.description,
        function_ref=orm.function_ref,
        created_at=orm.created_at,
    )


def _to_agent_tool_entity(orm: AgentToolORM) -> AgentTool:
    """Map agent_tools row → domain AgentTool (no catalog fields)."""
    return AgentTool(
        agent_id=orm.agent_id,
        tool_id=orm.tool_id,
        updated_at=orm.updated_at,
        is_active=orm.is_active,
        name=None,
        description=None,
    )


def _to_agent_tool_entity_with_catalog(
    orm: AgentToolORM, name: str, description: str
) -> AgentTool:
    """Map agent_tools + catalog name/description → domain AgentTool."""
    return AgentTool(
        agent_id=orm.agent_id,
        tool_id=orm.tool_id,
        updated_at=orm.updated_at,
        is_active=orm.is_active,
        name=name,
        description=description,
    )


class SQLToolRepository(ToolRepository):
    """Catalog CRUD is unscoped; association methods are scoped by agent_id + tool_id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- Catalog (global) ---

    async def get(self, id: UUID) -> Tool | None:
        result = await self._session.execute(
            select(ToolCatalog).where(ToolCatalog.id == id)
        )
        orm = result.scalar_one_or_none()
        return _to_tool_entity(orm) if orm is not None else None

    async def list(self, offset: int, limit: int) -> builtins.list[Tool]:
        stmt = (
            select(ToolCatalog)
            .order_by(ToolCatalog.name.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_to_tool_entity(row) for row in result.scalars().all()]

    async def create(self, tool: Tool) -> Tool:
        orm = ToolCatalog(
            id=tool.id,
            name=tool.name,
            description=tool.description,
            function_ref=tool.function_ref,
        )
        self._session.add(orm)
        try:
            await self._session.flush()
        except IntegrityError as e:
            try:
                self._session.expunge(orm)
            except InvalidRequestError:
                pass  # instance already not in session (e.g. async flush)
            raise ToolAlreadyExists(
                f"Tool with name {tool.name!r} already exists"
            ) from e
        await self._session.refresh(orm)
        return _to_tool_entity(orm)

    async def update(self, tool: Tool) -> Tool:
        result = await self._session.execute(
            select(ToolCatalog).where(ToolCatalog.id == tool.id)
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            raise ToolNotFound(f"Tool not found for update: {tool.id}")
        orm.name = tool.name
        orm.description = tool.description
        orm.function_ref = tool.function_ref
        await self._session.flush()
        await self._session.refresh(orm)
        return _to_tool_entity(orm)

    async def delete(self, id: UUID) -> None:
        result = await self._session.execute(
            select(ToolCatalog).where(ToolCatalog.id == id)
        )
        if result.scalar_one_or_none() is None:
            raise ToolNotFound(f"Tool not found for delete: {id}")
        await self._session.execute(delete(ToolCatalog).where(ToolCatalog.id == id))
        await self._session.flush()

    # --- Association (agent ↔ tool) ---

    async def attach(self, agent_id: UUID, tool_id: UUID) -> AgentTool:
        # INSERT into agent_tools; on duplicate PK raise without aborting outer tx.
        orm = AgentToolORM(
            agent_id=agent_id,
            tool_id=tool_id,
            is_active=False,
        )
        self._session.add(orm)
        try:
            async with self._session.begin_nested():
                await self._session.flush()
        except IntegrityError as e:
            self._session.expunge(orm)
            raise AgentToolAlreadyAttached(
                f"Agent {agent_id} already attached to tool {tool_id}"
            ) from e
        await self._session.refresh(orm)
        return _to_agent_tool_entity(orm)

    async def detach(self, agent_id: UUID, tool_id: UUID) -> None:
        result = await self._session.execute(
            select(AgentToolORM).where(
                AgentToolORM.agent_id == agent_id,
                AgentToolORM.tool_id == tool_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise AgentToolNotFound(
                f"No association agent_id={agent_id} tool_id={tool_id}"
            )
        await self._session.execute(
            delete(AgentToolORM).where(
                AgentToolORM.agent_id == agent_id,
                AgentToolORM.tool_id == tool_id,
            )
        )
        await self._session.flush()

    async def set_active(
        self,
        agent_id: UUID,
        tool_id: UUID,
        is_active: bool,
    ) -> AgentTool:
        check = await self._session.execute(
            select(AgentToolORM).where(
                AgentToolORM.agent_id == agent_id,
                AgentToolORM.tool_id == tool_id,
            )
        )
        if check.scalar_one_or_none() is None:
            raise AgentToolNotFound(
                f"No association agent_id={agent_id} tool_id={tool_id}"
            )
        await self._session.execute(
            update(AgentToolORM)
            .where(
                AgentToolORM.agent_id == agent_id,
                AgentToolORM.tool_id == tool_id,
            )
            .values(is_active=is_active)
        )
        await self._session.flush()
        result = await self._session.execute(
            select(AgentToolORM).where(
                AgentToolORM.agent_id == agent_id,
                AgentToolORM.tool_id == tool_id,
            )
        )
        orm = result.scalar_one()
        return _to_agent_tool_entity(orm)

    async def toggle(self, agent_id: UUID, tool_id: UUID) -> AgentTool:
        raise NotImplementedError("implement in phase 9")

    async def get_agent_tool(self, agent_id: UUID, tool_id: UUID) -> AgentTool | None:
        stmt = (
            select(
                AgentToolORM,
                ToolCatalog.name.label("tool_name"),
                ToolCatalog.description.label("tool_description"),
            )
            .join(ToolCatalog, AgentToolORM.tool_id == ToolCatalog.id)
            .where(
                AgentToolORM.agent_id == agent_id,
                AgentToolORM.tool_id == tool_id,
            )
        )
        result = await self._session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None
        orm, name, description = row[0], row[1], row[2]
        return _to_agent_tool_entity_with_catalog(orm, name, description)

    async def list_by_agent(self, agent_id: UUID) -> builtins.list[AgentTool]:
        # JOIN tools_catalog to populate name/description on domain AgentTool.
        stmt = (
            select(
                AgentToolORM,
                ToolCatalog.name.label("tool_name"),
                ToolCatalog.description.label("tool_description"),
            )
            .join(ToolCatalog, AgentToolORM.tool_id == ToolCatalog.id)
            .where(AgentToolORM.agent_id == agent_id)
            .order_by(ToolCatalog.name.asc())
        )
        result = await self._session.execute(stmt)
        return [
            _to_agent_tool_entity_with_catalog(row[0], row[1], row[2])
            for row in result.all()
        ]
