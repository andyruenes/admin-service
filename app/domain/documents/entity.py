"""Document domain entity (scoped to an agent)."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

# file_type: pdf | txt | docx | md
# status: indexing | indexed | error (aligns with ORM DocumentStatus)


@dataclass
class Document:
    """Domain entity mirroring the documents table (Document ORM reference)."""

    id: UUID
    agent_id: UUID
    file_name: str
    file_type: str
    created_at: datetime
    status: str = "indexing"
    chunks_total: int | None = None
    error_message: str | None = None
