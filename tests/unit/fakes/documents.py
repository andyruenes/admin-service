"""In-memory DocumentRepository fake — get raises DocumentNotFound when not found."""

from copy import deepcopy
from uuid import UUID

from app.domain.documents.entity import Document
from app.domain.documents.exceptions import DocumentNotFound
from app.domain.documents.repository import DocumentRepository


class InMemoryDocumentRepository(DocumentRepository):
    """Fake backed by list[Document]. get() raises DocumentNotFound if not found."""

    def __init__(self) -> None:
        self.store: list[Document] = []

    def _by_id(self, id: UUID) -> Document | None:
        for d in self.store:
            if d.id == id:
                return d
        return None

    async def get(self, id: UUID) -> Document | None:
        doc = self._by_id(id)
        if doc is None:
            raise DocumentNotFound(f"Document not found: {id}")
        return deepcopy(doc)

    async def list_by_agent(
        self,
        agent_id: UUID,
        offset: int,
        limit: int,
    ) -> list[Document]:
        items = [d for d in self.store if d.agent_id == agent_id]
        items.sort(key=lambda d: d.created_at, reverse=True)
        page = items[offset : offset + limit]
        return [deepcopy(d) for d in page]

    async def create(self, document: Document) -> Document:
        self.store.append(deepcopy(document))
        return deepcopy(self.store[-1])

    async def update(self, document: Document) -> Document:
        for i, d in enumerate(self.store):
            if d.id == document.id:
                self.store[i] = deepcopy(document)
                return deepcopy(self.store[i])
        raise DocumentNotFound(f"Document not found for update: {document.id}")

    async def delete(self, id: UUID) -> None:
        for i, d in enumerate(self.store):
            if d.id == id:
                del self.store[i]
                return
        raise DocumentNotFound(f"Document not found: {id}")
