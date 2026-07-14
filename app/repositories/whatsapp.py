"""SQLAlchemy async implementation of WhatsappRepository."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.uuid_default import uuid7
from app.domain.whatsapp.entity import WhatsappConversation, WhatsappMessage
from app.domain.whatsapp.repository import WhatsappRepository
from app.models.whatsapp import WhatsappConversation as ConversationORM
from app.models.whatsapp import WhatsappMessage as MessageORM


def _conv_to_entity(orm: ConversationORM) -> WhatsappConversation:
    return WhatsappConversation(
        id=orm.id,
        agent_id=orm.agent_id,
        phone_number=orm.phone_number,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _msg_to_entity(orm: MessageORM) -> WhatsappMessage:
    return WhatsappMessage(
        id=orm.id,
        conversation_id=orm.conversation_id,
        role=orm.role,
        content=orm.content,
        external_message_id=orm.external_message_id,
        wa_timestamp=orm.wa_timestamp,
        created_at=orm.created_at,
    )


class SQLWhatsappRepository(WhatsappRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_conversation(
        self, agent_id: UUID, phone_number: str
    ) -> WhatsappConversation:
        # Upsert: insert if not exists, return existing on conflict.
        stmt = (
            insert(ConversationORM)
            .values(id=uuid7(), agent_id=agent_id, phone_number=phone_number)
            .on_conflict_do_nothing(constraint="uq_conversation_agent_phone")
            .returning(ConversationORM)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            # Row already existed — fetch it.
            existing = await self._session.execute(
                select(ConversationORM).where(
                    ConversationORM.agent_id == agent_id,
                    ConversationORM.phone_number == phone_number,
                )
            )
            row = existing.scalar_one()

        await self._session.flush()
        return _conv_to_entity(row)

    async def save_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        external_message_id: str | None = None,
        wa_timestamp: datetime | None = None,
    ) -> WhatsappMessage:
        orm = MessageORM(
            id=uuid7(),
            conversation_id=conversation_id,
            role=role,
            content=content,
            external_message_id=external_message_id,
            wa_timestamp=wa_timestamp,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _msg_to_entity(orm)

    async def get_history(
        self, conversation_id: UUID, limit: int = 20
    ) -> list[dict[str, str]]:
        # Fetch the last `limit` messages ordered ascending for LLM consumption.
        subq = (
            select(MessageORM)
            .where(MessageORM.conversation_id == conversation_id)
            .order_by(MessageORM.created_at.desc())
            .limit(limit)
            .subquery()
        )
        stmt = select(subq).order_by(subq.c.created_at.asc())
        result = await self._session.execute(stmt)
        rows = result.mappings().all()
        return [{"role": row["role"], "content": row["content"]} for row in rows]

    async def message_exists(self, external_message_id: str) -> bool:
        result = await self._session.execute(
            select(MessageORM.id).where(
                MessageORM.external_message_id == external_message_id
            )
        )
        return result.scalar_one_or_none() is not None
