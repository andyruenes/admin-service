"""Pydantic schemas for test session API — in-memory only."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.prompts import PromptRead
from app.schemas.tools import AgentToolRead
from app.schemas.use_cases import UseCaseRead


class TestSessionResponse(BaseModel):
    """Response shape for create/invalidate test session."""

    model_config = ConfigDict()

    session_id: str
    agent_id: UUID
    active_prompt: PromptRead | None
    use_cases: list[UseCaseRead]
    active_tools: list[AgentToolRead]
