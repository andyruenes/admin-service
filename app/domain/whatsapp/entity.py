"""WhatsApp conversation and message domain entities."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class WhatsappConversation:
    id: UUID
    agent_id: UUID
    phone_number: str
    created_at: datetime
    updated_at: datetime


@dataclass
class WhatsappMessage:
    id: UUID
    conversation_id: UUID
    role: str  # "user" | "assistant"
    content: str
    created_at: datetime
    external_message_id: str | None = None
    wa_timestamp: datetime | None = None
