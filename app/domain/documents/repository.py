"""Document repository port (abstract). Infrastructure implements."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.documents.entity import Document


class DocumentRepository(ABC):
    """Persistence port for Document (scoped by agent)."""

    @abstractmethod
    async def get(self, id: UUID) -> Document | None:
        """Return document by id, or None if not found."""

    @abstractmethod
    async def list_by_agent(
        self,
        agent_id: UUID,
        offset: int,
        limit: int,
    ) -> list[Document]:
        """Return a page of documents for the given agent."""

    @abstractmethod
    async def create(self, document: Document) -> Document:
        """Persist a new document; return the persisted entity."""

    @abstractmethod
    async def update(self, document: Document) -> Document:
        """Persist changes to an existing document."""

    @abstractmethod
    async def delete(self, id: UUID) -> None:
        """Remove document by id."""
