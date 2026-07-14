"""Pydantic schemas for UseCase API — agent_id from path only."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.schemas.common import PaginatedResponse

_MIN_RESPUESTA = 10


class UseCaseCreate(BaseModel):
    """Client payload only; agent_id from URL."""

    model_config = ConfigDict(extra="forbid")

    pregunta: str = Field(..., min_length=1)
    respuesta: str = Field(..., min_length=_MIN_RESPUESTA)


class UseCaseUpdate(BaseModel):
    """PATCH — both optional; respuesta min_length when provided."""

    model_config = ConfigDict(extra="forbid")

    pregunta: str | None = None
    respuesta: str | None = None

    @field_validator("respuesta")
    @classmethod
    def respuesta_min_length_when_set(cls, v: str | None) -> str | None:
        if v is not None and len(v) < _MIN_RESPUESTA:
            raise ValueError(
                f"respuesta must be at least {_MIN_RESPUESTA} chars when provided"
            )
        return v


class UseCaseRead(BaseModel):
    """Full use case; from_attributes binds domain question/answer to pregunta/respuesta."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    pregunta: str = Field(validation_alias="question")
    respuesta: str = Field(validation_alias="answer")
    created_at: datetime
    updated_at: datetime


class UseCaseListItem(BaseModel):
    """List item with truncated respuesta."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pregunta: str = Field(validation_alias="question")
    created_at: datetime
    respuesta: str = Field(validation_alias="answer", exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def respuesta_truncada(self) -> str:
        return self.respuesta[:80]


UseCaseListResponse = PaginatedResponse[UseCaseListItem]
