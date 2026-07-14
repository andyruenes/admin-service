from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.uuid_default import uuid7
from app.models.agent_tool import AgentTool
from app.models.document import Document

if TYPE_CHECKING:
    from app.models.prompt_version import PromptVersion
    from app.models.use_case import UseCase


class AgentStatus(enum.StrEnum):
    draft = "draft"
    active = "active"
    inactive = "inactive"


class BotConfig(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    llm_model: Mapped[str] = mapped_column(String(50), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now(), nullable=False
    )

    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus, name="agent_status"), default=AgentStatus.draft
    )
    phone_account_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    prompt_versions: Mapped[list[PromptVersion]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )
    agent_tools: Mapped[list[AgentTool]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )
    documents: Mapped[list[Document]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )
    use_cases: Mapped[list[UseCase]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )
