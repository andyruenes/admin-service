"""Application service for Document aggregate — agent-scoped + transaction on writes; sync index call with rollback on failure."""

import logging
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

import httpx

from app.domain.documents.entity import Document
from app.domain.documents.exceptions import (
    AgentServiceUnavailable,
    DocumentNotBelongToAgent,
    DocumentNotFound,
)
from app.domain.documents.repository import DocumentRepository

logger = logging.getLogger(__name__)


class _CommitSession(Protocol):
    async def commit(self) -> None: ...


class DocumentService:
    """All operations scoped by agent_id; get() enforces ownership. create() sync POST to index with rollback on failure."""

    def __init__(
        self,
        repo: DocumentRepository,
        session: _CommitSession,
        http_client: httpx.AsyncClient,
        agent_service_url: str,
    ) -> None:
        self._repo = repo
        self._session = session
        self._http_client = http_client
        self._agent_service_url = agent_service_url.rstrip("/")

    async def _get_for_agent(self, agent_id: UUID, id: UUID) -> Document:
        entity = await self._repo.get(id)
        if entity is None:
            raise DocumentNotFound(f"Document not found: {id}")
        if entity.agent_id != agent_id:
            raise DocumentNotBelongToAgent(
                f"Document {id} belongs to agent {entity.agent_id}, not {agent_id}"
            )
        return entity

    async def create(
        self,
        agent_id: UUID,
        file_name: str,
        file_type: str,
        file_content: bytes,
    ) -> Document:
        """Create document with status=indexing; commit; multipart POST to agent index; rollback on agent failure."""
        now = datetime.now(UTC)
        document = Document(
            id=uuid4(),
            agent_id=agent_id,
            file_name=file_name,
            file_type=file_type,
            created_at=now,
            status="indexing",
            chunks_total=None,
            error_message=None,
        )
        doc = await self._repo.create(document)
        await self._session.commit()
        try:
            # agent-service expects multipart: file, agent_id, doc_id (same UUID as DB row).
            files = {"file": (file_name, file_content)}
            data = {
                "agent_id": str(agent_id),
                "doc_id": str(doc.id),
            }
            response = await self._http_client.post(
                f"{self._agent_service_url}/agent/documents/index",
                files=files,
                data=data,
            )
            if response.status_code not in (200, 201, 202):
                raise AgentServiceUnavailable(
                    f"agent-service returned {response.status_code}"
                )
        except (httpx.HTTPError, AgentServiceUnavailable) as exc:
            await self._repo.delete(doc.id)
            await self._session.commit()
            raise AgentServiceUnavailable(
                "agent-service unreachable or returned error"
            ) from exc
        return doc

    async def get(self, agent_id: UUID, id: UUID) -> Document:
        return await self._get_for_agent(agent_id, id)

    async def list(
        self,
        agent_id: UUID,
        offset: int,
        limit: int,
    ) -> list[Document]:
        return await self._repo.list_by_agent(agent_id, offset, limit)

    async def update(self, agent_id: UUID, id: UUID, data: dict[str, Any]) -> Document:
        """Partial update; agent_id on entity must stay the scoped agent."""
        current = await self._get_for_agent(agent_id, id)
        file_name = data["file_name"] if "file_name" in data else current.file_name
        file_type = data["file_type"] if "file_type" in data else current.file_type
        status = data["status"] if "status" in data else current.status
        chunks_total = (
            data["chunks_total"] if "chunks_total" in data else current.chunks_total
        )
        error_message = (
            data["error_message"] if "error_message" in data else current.error_message
        )
        patched = Document(
            id=current.id,
            agent_id=agent_id,
            file_name=file_name,
            file_type=file_type,
            created_at=current.created_at,
            status=status,
            chunks_total=chunks_total,
            error_message=error_message,
        )
        updated = await self._repo.update(patched)
        await self._session.commit()
        return updated

    async def report_indexing_result(
        self,
        document_id: UUID,
        status: str,
        chunks_total: int | None = None,
        error_message: str | None = None,
    ) -> Document:
        """Update document status after IA processing (internal callback). status: indexed | error."""
        doc = await self._repo.get(document_id)
        if doc is None:
            raise DocumentNotFound(f"Document not found: {document_id}")
        patched = Document(
            id=doc.id,
            agent_id=doc.agent_id,
            file_name=doc.file_name,
            file_type=doc.file_type,
            created_at=doc.created_at,
            status=status,
            chunks_total=chunks_total if chunks_total is not None else doc.chunks_total,
            error_message=error_message
            if error_message is not None
            else doc.error_message,
        )
        updated = await self._repo.update(patched)
        await self._session.commit()
        return updated

    async def delete(self, id: UUID) -> None:
        """Delete document: call vector delete; only remove DB record if IA service succeeds."""
        doc = await self._repo.get(id)
        if doc is None:
            raise DocumentNotFound(f"Document not found: {id}")
        try:
            response = await self._http_client.delete(
                f"{self._agent_service_url}/agent/documents/{id}/vectors",
                params={"agent_id": str(doc.agent_id)},
            )
            # 404: vectors already gone — treat as success so delete is idempotent.
            if response.status_code >= 400 and response.status_code != 404:
                raise AgentServiceUnavailable(
                    f"agent-service returned {response.status_code} for vector delete"
                )
        except (httpx.HTTPError, AgentServiceUnavailable) as exc:
            logger.exception(
                "Vector delete failed for document %s, DB record left unchanged: %s",
                id,
                exc,
            )
            raise AgentServiceUnavailable(
                "IA service unavailable; document not deleted"
            ) from exc
        await self._repo.delete(id)
        await self._session.commit()
