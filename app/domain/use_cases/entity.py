"""UseCase domain entity (belongs to an agent)."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

# Field names align with ORM (question/answer) and DB.
# DB check constraints (question non-empty, answer min length) are not enforced here.


@dataclass
class UseCase:
    """Domain entity mirroring use_cases (UseCase ORM reference)."""

    id: UUID
    agent_id: UUID
    question: str
    answer: str
    created_at: datetime
    updated_at: datetime
