"""Pydantic schemas for Agent API — aligned with app.domain.agents.entity.Agent semantics."""

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import PaginatedResponse

# Matches agent_status / domain Agent.status — Literal so wire values are validated.
AgentStatusLiteral = Literal["draft", "active", "inactive"]

# Name: alphanumeric, spaces, hyphen, underscore only (no special characters).
AGENT_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\s\-]+$")


def _validate_agent_name(name: str) -> str:
    if not name or not name.strip():
        raise ValueError("Name must not be empty")
    if not AGENT_NAME_PATTERN.match(name):
        raise ValueError(
            "Name must contain only letters, numbers, spaces, hyphens and underscores"
        )
    return name.strip()


class ChangeStatusRequest(BaseModel):
    """Body for PATCH/PUT status change (draft→active, active→inactive only)."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["draft", "active", "inactive"]


class AgentCreate(BaseModel):
    """Client payload to create an agent."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Display name; maps to domain name")
    description: str | None = Field(
        default=None, description="Maps to domain description"
    )
    llm_model: str = Field(..., description="LLM model id; maps to domain llm_model")
    status: AgentStatusLiteral = Field(default="draft")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_agent_name(v)


class AgentUpdate(BaseModel):
    """PATCH payload — every field optional; None means omit (no change)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    llm_model: str | None = None
    status: AgentStatusLiteral | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _validate_agent_name(v)


class AgentRead(BaseModel):
    """Full agent returned by API; field names match domain Agent for from_attributes."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    llm_model: str
    status: AgentStatusLiteral
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    phone_account_id: str | None = None


class PhoneAccountResponse(BaseModel):
    """Response body for POST /agents/{agent_id}/phone-account."""

    agent_id: UUID
    phone_account_id: str


class BotStatusResponse(BaseModel):
    """Response body for GET /agents/{agent_id}/phone-account/status."""

    account_id: str
    status: str
    phone_number: str
    qr_code: str


class AgentListItem(BaseModel):
    """Lightweight item for list endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    status: str
    updated_at: datetime


AgentListResponse = PaginatedResponse[AgentListItem]
