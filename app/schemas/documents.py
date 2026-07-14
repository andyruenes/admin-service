"""Pydantic schemas for Document API — agent_id from path only."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginatedResponse

DocumentFileTypeLiteral = Literal["pdf", "txt", "docx", "md"]
DocumentStatusLiteral = Literal["indexando", "indexado", "error"]


class DocumentCreate(BaseModel):
    """Client payload; status set server-side as indexando."""

    model_config = ConfigDict(extra="forbid")

    file_name: str = Field(...)
    file_type: Literal["pdf", "txt", "docx", "md"] = Field(...)


class DocumentUpdate(BaseModel):
    """PATCH — only editable field."""

    model_config = ConfigDict(extra="forbid")

    file_name: str | None = None


class DocumentRead(BaseModel):
    """Full document; from_attributes from domain Document."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    file_name: str
    file_type: str
    status: str
    chunks_total: int | None = None
    error_message: str | None = None
    created_at: datetime


DocumentListResponse = PaginatedResponse[DocumentRead]


class IndexingResultCallback(BaseModel):
    """Body for internal callback when IA finishes indexing a document."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["indexed", "error"] = Field(
        ..., description="Result of indexing (indexed | error)"
    )
    chunks_total: int | None = Field(
        default=None, description="Number of chunks when status is indexed"
    )
    error_message: str | None = Field(
        default=None, description="Error details when status is error"
    )
