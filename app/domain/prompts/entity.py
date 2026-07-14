"""PromptVersion domain entity (belongs to an agent)."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

# At most one is_active=True per agent; enforced in repository/infrastructure.


@dataclass
class PromptVersion:
    """Domain entity mirroring prompt_versions (PromptVersion ORM reference)."""

    id: UUID
    agent_id: UUID
    version_number: int
    content: str
    created_at: datetime
    is_active: bool = False
