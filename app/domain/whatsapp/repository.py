"""WhatsApp repository port (abstract)."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.domain.whatsapp.entity import WhatsappConversation, WhatsappMessage


class WhatsappRepository(ABC):
    @abstractmethod
    async def get_or_create_conversation(
        self, agent_id: UUID, phone_number: str
    ) -> WhatsappConversation:
        """Return the existing conversation for (agent_id, phone_number) or create one."""

    @abstractmethod
    async def save_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        external_message_id: str | None = None,
        wa_timestamp: datetime | None = None,
    ) -> WhatsappMessage:
        """Persist a new message. Caller must commit."""

    @abstractmethod
    async def get_history(
        self, conversation_id: UUID, limit: int = 20
    ) -> list[dict[str, str]]:
        """Return last `limit` messages as [{"role": …, "content": …}] oldest-first."""

    @abstractmethod
    async def message_exists(self, external_message_id: str) -> bool:
        """Return True if a message with this external_message_id is already stored."""
