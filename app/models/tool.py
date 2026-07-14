from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.uuid_default import uuid7
from app.models.agent_tool import AgentTool


class ToolCatalog(Base):
    __tablename__ = "tools_catalog"
    __table_args__ = (CheckConstraint(r"name ~ '^[a-z0-9_]+$'", name="ck_name_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    function_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)

    agent_tools: Mapped[list[AgentTool]] = relationship(
        back_populates="tool", cascade="all, delete-orphan"
    )
