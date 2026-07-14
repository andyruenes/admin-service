"""Tool catalog and agent-tool association domain entities."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Tool:
    """Global catalog entry; mirrors tools_catalog (ToolCatalog ORM reference)."""

    id: UUID
    name: str
    description: str
    function_ref: str
    created_at: datetime


@dataclass
class AgentTool:
    """Association agent ↔ tool; mirrors agent_tools (AgentTool ORM reference).
    Optional name/description are populated when loaded with catalog JOIN.
    """

    agent_id: UUID
    tool_id: UUID
    updated_at: datetime
    is_active: bool = False
    name: str | None = None
    description: str | None = None
