"""Pydantic schemas for PromptVersion API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


class SavePromptRequest(BaseModel):
    """Body for saving a new prompt version (content only)."""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., description="Full prompt content")


class PromptRead(BaseModel):
    """Full prompt version; built from domain PromptVersion."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    version_number: int
    content: str
    is_active: bool
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def char_count(self) -> int:
        return len(self.content)


class PromptVersionSummary(BaseModel):
    """Summary for list endpoint; exposes content_preview and is_active, not full content."""

    model_config = ConfigDict(from_attributes=True)

    version_number: int
    created_at: datetime
    is_active: bool
    content: str = Field(..., exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def content_preview(self) -> str:
        return self.content[:150]


class PromptVersionListResponse(BaseModel):
    """List of prompt version summaries."""

    model_config = ConfigDict()

    items: list[PromptVersionSummary]
