"""Pydantic schemas for Tool catalog + AgentTool association."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

_SLUG_PATTERN = re.compile(r"^[a-z0-9_]+$")


class ToolCreate(BaseModel):
    """Catalog entry create; name must be slug."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ..., description="Slug: lowercase letters, digits, underscores only"
    )
    description: str = Field(...)
    function_ref: str = Field(...)

    @field_validator("name")
    @classmethod
    def name_slug(cls, v: str) -> str:
        if not _SLUG_PATTERN.fullmatch(v):
            raise ValueError("name must match ^[a-z0-9_]+$")
        return v


class ToolUpdate(BaseModel):
    """PATCH — all optional."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    function_ref: str | None = None

    @field_validator("name")
    @classmethod
    def name_slug_when_set(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not _SLUG_PATTERN.fullmatch(v):
            raise ValueError("name must match ^[a-z0-9_]+$")
        return v


class ToolRead(BaseModel):
    """Full catalog row; from_attributes from domain Tool."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    function_ref: str
    created_at: datetime


class AgentToolAttach(BaseModel):
    """POST body to attach a catalog tool to an agent."""

    model_config = ConfigDict(extra="forbid")

    tool_id: UUID


class AgentToolRead(BaseModel):
    """Association row with catalog name/description (from repo JOIN)."""

    model_config = ConfigDict(from_attributes=True)

    agent_id: UUID
    tool_id: UUID
    is_active: bool
    name: str
    description: str


class AgentToolPatch(BaseModel):
    """PATCH body for direct is_active set (not toggle)."""

    model_config = ConfigDict(extra="forbid")

    is_active: bool


class AgentToolListResponse(BaseModel):
    """List of agent tools; active_count computed by router."""

    model_config = ConfigDict()

    items: list[AgentToolRead]
    active_count: int
