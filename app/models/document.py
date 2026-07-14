from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.uuid_default import uuid7

if TYPE_CHECKING:
    from app.models.agent import BotConfig


class DocumentType(enum.StrEnum):
    pdf = "pdf"
    txt = "txt"
    docx = "docx"
    md = "md"


class DocumentStatus(enum.StrEnum):
    indexing = "indexing"
    indexed = "indexed"
    error = "error"


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "(status = 'error' AND error_message IS NOT NULL) OR (status <> 'error')",
            name="ck_error_requires_message",
        ),
        CheckConstraint(
            "(status = 'indexed' AND chunks_total IS NOT NULL) OR (status <> 'indexed')",
            name="ck_indexed_requires_chunks",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type"), nullable=False
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"),
        default=DocumentStatus.indexing,
        nullable=False,
    )
    chunks_total: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)

    agent: Mapped[BotConfig] = relationship(back_populates="documents")
