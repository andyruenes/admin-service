"""Shared Pydantic types — no resource imports to avoid circular deps."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):  # noqa: UP046
    """Generic list wrapper; T is the Read schema per resource (e.g. AgentRead)."""

    model_config = ConfigDict()

    items: list[T] = Field(description="Page of resources")
    total: int = Field(description="Total matching count before pagination")
    offset: int = Field(description="Number of items skipped")
    limit: int = Field(description="Maximum items in this page")


class ErrorResponse(BaseModel):
    """Stable shape for global exception handlers (404, 409, validation, etc.)."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(
        ...,
        description="Machine-readable code, e.g. NOT_FOUND, CONFLICT, VALIDATION_ERROR",
    )
    message: str = Field(..., description="Human-readable summary")
    details: dict[str, Any] | None = Field(
        default=None,
        description="Optional structured context (field errors, resource ids, etc.)",
    )
