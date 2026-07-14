"""Tool catalog and agent-tool association repository port (abstract)."""

from __future__ import annotations

import builtins
from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.tools.entity import AgentTool, Tool


class ToolRepository(ABC):
    """Persistence port for Tool catalog and AgentTool associations."""

    # --- Catalog (global) ---

    @abstractmethod
    async def get(self, id: UUID) -> Tool | None:
        """Return tool by id, or None if not found."""

    @abstractmethod
    async def list(self, offset: int, limit: int) -> builtins.list[Tool]:
        """Return a page of tools from the catalog."""

    @abstractmethod
    async def create(self, tool: Tool) -> Tool:
        """Persist a new catalog tool; return the persisted entity."""

    @abstractmethod
    async def update(self, tool: Tool) -> Tool:
        """Persist changes to an existing catalog tool."""

    @abstractmethod
    async def delete(self, id: UUID) -> None:
        """Remove catalog tool by id."""

    # --- Association (agent ↔ tool) ---

    @abstractmethod
    async def attach(self, agent_id: UUID, tool_id: UUID) -> AgentTool:
        """Link agent to tool; return the association row."""

    @abstractmethod
    async def detach(self, agent_id: UUID, tool_id: UUID) -> None:
        """Remove agent-tool link."""

    @abstractmethod
    async def set_active(
        self,
        agent_id: UUID,
        tool_id: UUID,
        is_active: bool,
    ) -> AgentTool:
        """Update is_active on the association; return updated entity."""

    @abstractmethod
    async def list_by_agent(self, agent_id: UUID) -> builtins.list[AgentTool]:
        """Return all agent-tool associations for the given agent."""
