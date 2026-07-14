"""In-memory ToolRepository fake — catalog + agent_tools, toggle mutates stored AgentTool."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID

from app.domain.tools.entity import AgentTool, Tool
from app.domain.tools.exceptions import (
    AgentToolAlreadyAttached,
    AgentToolNotFound,
    ToolNotFound,
)
from app.domain.tools.repository import ToolRepository


class InMemoryToolRepository(ToolRepository):
    """Fake: catalog in dict[UUID, Tool], associations in list[AgentTool]. list_by_agent joins catalog."""

    def __init__(self) -> None:
        self.catalog: dict[UUID, Tool] = {}
        self.agent_tools: list[AgentTool] = []

    def _find_assoc(self, agent_id: UUID, tool_id: UUID) -> int | None:
        for i, at in enumerate(self.agent_tools):
            if at.agent_id == agent_id and at.tool_id == tool_id:
                return i
        return None

    async def get(self, id: UUID) -> Tool | None:
        t = self.catalog.get(id)
        return deepcopy(t) if t is not None else None

    async def list(self, offset: int, limit: int) -> list[Tool]:
        items = sorted(self.catalog.values(), key=lambda t: t.name)
        page = items[offset : offset + limit]
        return [deepcopy(t) for t in page]

    async def create(self, tool: Tool) -> Tool:
        self.catalog[tool.id] = deepcopy(tool)
        return deepcopy(self.catalog[tool.id])

    async def update(self, tool: Tool) -> Tool:
        if tool.id not in self.catalog:
            raise ToolNotFound(f"Tool not found for update: {tool.id}")
        self.catalog[tool.id] = deepcopy(tool)
        return deepcopy(self.catalog[tool.id])

    async def delete(self, id: UUID) -> None:
        if id not in self.catalog:
            raise ToolNotFound(f"Tool not found for delete: {id}")
        del self.catalog[id]

    async def attach(self, agent_id: UUID, tool_id: UUID) -> AgentTool:
        if self._find_assoc(agent_id, tool_id) is not None:
            raise AgentToolAlreadyAttached(
                f"Agent {agent_id} already attached to tool {tool_id}"
            )
        if tool_id not in self.catalog:
            raise ToolNotFound(f"Tool not found, cannot attach: {tool_id}")
        at = AgentTool(
            agent_id=agent_id,
            tool_id=tool_id,
            updated_at=datetime.now(UTC),
            is_active=False,
            name=self.catalog[tool_id].name,
            description=self.catalog[tool_id].description,
        )
        self.agent_tools.append(at)
        return deepcopy(at)

    async def detach(self, agent_id: UUID, tool_id: UUID) -> None:
        i = self._find_assoc(agent_id, tool_id)
        if i is None:
            raise AgentToolNotFound(
                f"No association agent_id={agent_id} tool_id={tool_id}"
            )
        del self.agent_tools[i]

    async def set_active(
        self,
        agent_id: UUID,
        tool_id: UUID,
        is_active: bool,
    ) -> AgentTool:
        i = self._find_assoc(agent_id, tool_id)
        if i is None:
            raise AgentToolNotFound(
                f"No association agent_id={agent_id} tool_id={tool_id}"
            )
        at = self.agent_tools[i]
        tool = self.catalog.get(tool_id)
        name = tool.name if tool else None
        desc = tool.description if tool else None
        updated = AgentTool(
            agent_id=at.agent_id,
            tool_id=at.tool_id,
            updated_at=at.updated_at,
            is_active=is_active,
            name=name,
            description=desc,
        )
        self.agent_tools[i] = updated
        return deepcopy(updated)

    async def toggle(self, agent_id: UUID, tool_id: UUID) -> AgentTool:
        i = self._find_assoc(agent_id, tool_id)
        if i is None:
            raise AgentToolNotFound(
                f"No association agent_id={agent_id} tool_id={tool_id}"
            )
        at = self.agent_tools[i]
        new_active = not at.is_active
        tool = self.catalog.get(tool_id)
        name = tool.name if tool else None
        desc = tool.description if tool else None
        updated = AgentTool(
            agent_id=at.agent_id,
            tool_id=at.tool_id,
            updated_at=at.updated_at,
            is_active=new_active,
            name=name,
            description=desc,
        )
        self.agent_tools[i] = updated
        return deepcopy(updated)

    async def get_agent_tool(self, agent_id: UUID, tool_id: UUID) -> AgentTool | None:
        i = self._find_assoc(agent_id, tool_id)
        if i is None:
            return None
        at = self.agent_tools[i]
        tool = self.catalog.get(tool_id)
        name = tool.name if tool else None
        desc = tool.description if tool else None
        result = AgentTool(
            agent_id=at.agent_id,
            tool_id=at.tool_id,
            updated_at=at.updated_at,
            is_active=at.is_active,
            name=name,
            description=desc,
        )
        return deepcopy(result)

    async def list_by_agent(self, agent_id: UUID) -> list[AgentTool]:
        result = []
        for at in self.agent_tools:
            if at.agent_id != agent_id:
                continue
            tool = self.catalog.get(at.tool_id)
            name = tool.name if tool else None
            desc = tool.description if tool else None
            result.append(
                AgentTool(
                    agent_id=at.agent_id,
                    tool_id=at.tool_id,
                    updated_at=at.updated_at,
                    is_active=at.is_active,
                    name=name,
                    description=desc,
                )
            )
        result.sort(key=lambda x: (x.name or "", x.tool_id))
        return [deepcopy(a) for a in result]
