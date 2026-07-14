"""Agent aggregate root (domain entity)."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

# Status values match agent_status enum: draft | active | inactive


@dataclass
class Agent:
    """Domain entity mirroring the agents table (BotConfig ORM reference)."""

    id: UUID
    name: str
    llm_model: str
    created_at: datetime
    updated_at: datetime
    status: str = "draft"
    description: str | None = None
    deleted_at: datetime | None = None
    phone_account_id: str | None = None
