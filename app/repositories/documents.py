"""SQLAlchemy async implementation of DocumentRepository."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.documents.entity import Document
from app.domain.documents.exceptions import DocumentNotBelongToAgent, DocumentNotFound
from app.domain.documents.repository import DocumentRepository
from app.models.document import Document as DocumentORM
from app.models.document import DocumentStatus, DocumentType


def _to_entity(orm: DocumentORM) -> Document:
    """Map ORM row → domain entity; nullable columns as | None."""
    return Document(
        id=orm.id,
        agent_id=orm.agent_id,
        file_name=orm.file_name,
        file_type=orm.file_type.value,
        created_at=orm.created_at,
        status=orm.status.value,
        chunks_total=orm.chunks_total,
        error_message=orm.error_message,
    )


def _orm_status(domain_status: str) -> DocumentStatus:
    return DocumentStatus(domain_status)


class SQLDocumentRepository(DocumentRepository):
    """Persistence adapter for Document; agent scoping enforced in queries
    where the API allows an agent context; get(id) is by primary key only.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, id: UUID) -> Document | None:
        # Scoped only by PK: ABC has no agent_id on get(). Callers that must
        # enforce tenancy should use list_by_agent + filter, or pass ids
        # already proven to belong to the agent; alternative would be
        # get_for_agent(id, agent_id) on the port — not on the ABC today.
        result = await self._session.execute(
            select(DocumentORM).where(DocumentORM.id == id)
        )
        orm = result.scalar_one_or_none()
        return _to_entity(orm) if orm is not None else None

    async def list_by_agent(
        self,
        agent_id: UUID,
        offset: int,
        limit: int,
    ) -> list[Document]:
        stmt = (
            select(DocumentORM)
            .where(DocumentORM.agent_id == agent_id)
            .order_by(DocumentORM.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_to_entity(row) for row in result.scalars().all()]

    async def create(self, document: Document) -> Document:
        orm = DocumentORM(
            id=document.id,
            agent_id=document.agent_id,
            file_name=document.file_name,
            file_type=DocumentType(document.file_type),
            status=_orm_status(document.status),
            chunks_total=document.chunks_total,
            error_message=document.error_message,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _to_entity(orm)

    async def update(self, document: Document) -> Document:
        result = await self._session.execute(
            select(DocumentORM).where(DocumentORM.id == document.id)
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            raise DocumentNotFound(f"Document not found for update: {document.id}")
        if orm.agent_id != document.agent_id:
            raise DocumentNotBelongToAgent(
                f"Document {document.id} belongs to agent {orm.agent_id}, not {document.agent_id}"
            )
        orm.file_name = document.file_name
        orm.file_type = DocumentType(document.file_type)
        orm.status = _orm_status(document.status)
        orm.chunks_total = document.chunks_total
        orm.error_message = document.error_message
        await self._session.flush()
        await self._session.refresh(orm)
        return _to_entity(orm)

    async def delete(self, id: UUID) -> None:
        result = await self._session.execute(
            select(DocumentORM).where(DocumentORM.id == id)
        )
        if result.scalar_one_or_none() is None:
            raise DocumentNotFound(f"Document not found for delete: {id}")
        await self._session.execute(delete(DocumentORM).where(DocumentORM.id == id))
        await self._session.flush()
