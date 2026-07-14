"""Application service for Tool catalog + agent-tool associations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from app.domain.tools.entity import AgentTool, Tool
from app.domain.tools.exceptions import (
    AgentToolNotFound,
    ToolAlreadyExists,
    ToolNotFound,
)
from app.domain.tools.repository import ToolRepository


class _CommitSession(Protocol):
    async def commit(self) -> None: ...


# Catalog writes and association mutations commit; catalog get/list read-only.


class ToolService:
    """Catalog CRUD is global; attach/detach/set_active are scoped by agent_id + tool_id."""

    def __init__(self, repo: ToolRepository, session: _CommitSession) -> None:
        self._repo = repo
        self._session = session

    # --- Catalog (unscoped) ---

    async def create_tool(self, data: dict[str, Any]) -> Tool:
        now = datetime.now(UTC)
        tool = Tool(
            id=data.get("id") or uuid4(),
            name=data["name"],
            description=data["description"],
            function_ref=data["function_ref"],
            created_at=now,
        )
        try:
            created = await self._repo.create(tool)
            await self._session.commit()
            return created
        except IntegrityError as e:
            raise ToolAlreadyExists(
                f"Tool with name {tool.name!r} already exists"
            ) from e

    async def get_tool(self, id: UUID) -> Tool:
        entity = await self._repo.get(id)
        if entity is None:
            raise ToolNotFound(f"Tool not found: {id}")
        return entity

    async def list_tools(self, offset: int, limit: int) -> list[Tool]:
        return await self._repo.list(offset, limit)

    async def update_tool(self, id: UUID, data: dict[str, Any]) -> Tool:
        current = await self.get_tool(id)
        name = data["name"] if "name" in data else current.name
        description = (
            data["description"] if "description" in data else current.description
        )
        function_ref = (
            data["function_ref"] if "function_ref" in data else current.function_ref
        )
        patched = Tool(
            id=current.id,
            name=name,
            description=description,
            function_ref=function_ref,
            created_at=current.created_at,
        )
        updated = await self._repo.update(patched)
        await self._session.commit()
        return updated

    async def delete_tool(self, id: UUID) -> None:
        await self.get_tool(id)
        await self._repo.delete(id)
        await self._session.commit()

    # --- Association (agent_id + tool_id) ---

    async def attach(self, agent_id: UUID, tool_id: UUID) -> AgentTool:
        """Ensure catalog tool exists, then link; repo raises if already attached."""
        if await self._repo.get(tool_id) is None:
            raise ToolNotFound(f"Tool not found, cannot attach: {tool_id}")
        linked = await self._repo.attach(agent_id, tool_id)
        await self._session.commit()
        return linked

    async def detach(self, agent_id: UUID, tool_id: UUID) -> None:
        await self._repo.detach(agent_id, tool_id)
        await self._session.commit()

    async def toggle(self, agent_id: UUID, tool_id: UUID) -> AgentTool:
        """Flip is_active for the agent-tool association; return updated entity."""
        associations: list[AgentTool] = await self._repo.list_by_agent(agent_id)
        current = next((a for a in associations if a.tool_id == tool_id), None)
        if current is None:
            raise AgentToolNotFound(f"Agent {agent_id} has no tool {tool_id}")
        new_state = not current.is_active
        updated = await self._repo.set_active(agent_id, tool_id, new_state)
        await self._session.commit()
        return updated

    async def set_active(
        self, agent_id: UUID, tool_id: UUID, is_active: bool
    ) -> AgentTool:
        """Set is_active for the agent-tool association; return updated entity."""
        associations: list[AgentTool] = await self._repo.list_by_agent(agent_id)
        current = next((a for a in associations if a.tool_id == tool_id), None)
        if current is None:
            raise AgentToolNotFound(f"Agent {agent_id} has no tool {tool_id}")
        if current.is_active == is_active:
            return current
        updated = await self._repo.set_active(agent_id, tool_id, is_active)
        await self._session.commit()
        return updated

    async def list_by_agent(self, agent_id: UUID) -> list[AgentTool]:
        return await self._repo.list_by_agent(agent_id)
