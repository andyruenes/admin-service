"""Unit tests for DocumentService."""

from uuid import uuid4

import httpx
import pytest

from app.domain.documents.exceptions import (
    AgentServiceUnavailable,
    DocumentNotBelongToAgent,
)
from app.services.documents import DocumentService
from tests.conftest import FakeSession
from tests.unit.factories import make_document
from tests.unit.fakes.documents import InMemoryDocumentRepository


@pytest.fixture
def repo():
    return InMemoryDocumentRepository()


@pytest.fixture
def session():
    return FakeSession()


@pytest.fixture
def agent_service_url():
    return "http://agent-service"


def _make_client(status_code: int = 200):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _make_client_500():
    return _make_client(500)


def _make_client_network_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed")

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def service(repo, session, agent_service_url):
    client = _make_client()
    return DocumentService(
        repo=repo,
        session=session,
        http_client=client,
        agent_service_url=agent_service_url,
    )


_MIN_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


@pytest.mark.asyncio
async def test_create_document_status_is_indexando(service):
    agent_id = uuid4()
    doc = await service.create(agent_id, "f.pdf", "pdf", _MIN_PDF)
    assert doc.status == "indexing"


@pytest.mark.asyncio
async def test_create_document_calls_agent_service(agent_service_url):
    requests_captured = []

    async def capture(request: httpx.Request) -> httpx.Response:
        requests_captured.append(request)
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(capture))
    repo = InMemoryDocumentRepository()
    session = FakeSession()
    svc = DocumentService(
        repo=repo,
        session=session,
        http_client=client,
        agent_service_url=agent_service_url,
    )
    agent_id = uuid4()
    await svc.create(agent_id, "f.pdf", "pdf", _MIN_PDF)
    assert len(requests_captured) == 1
    assert requests_captured[0].method == "POST"
    assert "/agent/documents/index" in str(requests_captured[0].url)


@pytest.mark.asyncio
async def test_create_document_multipart_contains_agent_and_doc_id(agent_service_url):
    requests_captured = []

    async def capture(request: httpx.Request) -> httpx.Response:
        requests_captured.append(request)
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(capture))
    repo = InMemoryDocumentRepository()
    session = FakeSession()
    svc = DocumentService(
        repo=repo,
        session=session,
        http_client=client,
        agent_service_url=agent_service_url,
    )
    agent_id = uuid4()
    doc = await svc.create(agent_id, "f.txt", "txt", b"hello indexing")
    assert len(requests_captured) == 1
    req = requests_captured[0]
    assert req.method == "POST"
    body = req.content.decode("utf-8", errors="replace")
    assert str(agent_id) in body
    assert str(doc.id) in body


@pytest.mark.asyncio
async def test_get_document_found(service, repo):
    agent_id = uuid4()
    doc = make_document(agent_id=agent_id, file_name="x.pdf", file_type="pdf")
    await repo.create(doc)
    got = await service.get(agent_id, doc.id)
    assert got.id == doc.id
    assert got.file_name == "x.pdf"


@pytest.mark.asyncio
async def test_list_documents_scoped_to_agent(service, repo):
    agent_id = uuid4()
    other = uuid4()
    d1 = make_document(agent_id=agent_id)
    d2 = make_document(agent_id=agent_id)
    d3 = make_document(agent_id=other)
    await repo.create(d1)
    await repo.create(d2)
    await repo.create(d3)
    items = await service.list(agent_id, 0, 10)
    assert len(items) == 2
    assert d3.id not in [x.id for x in items]


@pytest.mark.asyncio
async def test_delete_document_calls_vectors_endpoint(agent_service_url):
    requests_captured = []

    async def capture(request: httpx.Request) -> httpx.Response:
        requests_captured.append(request)
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(capture))
    repo = InMemoryDocumentRepository()
    session = FakeSession()
    svc = DocumentService(
        repo=repo,
        session=session,
        http_client=client,
        agent_service_url=agent_service_url,
    )
    doc = make_document(agent_id=uuid4())
    await repo.create(doc)
    await svc.delete(doc.id)
    assert len(requests_captured) == 1
    assert requests_captured[0].method == "DELETE"
    url_str = str(requests_captured[0].url)
    assert f"/agent/documents/{doc.id}/vectors" in url_str
    assert f"agent_id={doc.agent_id}" in url_str


@pytest.mark.asyncio
async def test_delete_document_removes_record(service, repo):
    agent_id = uuid4()
    doc = make_document(agent_id=agent_id)
    await repo.create(doc)
    await service.delete(doc.id)
    docs = await service.list(agent_id, 0, 10)
    assert doc.id not in [d.id for d in docs]


@pytest.mark.asyncio
async def test_delete_document_agent_404_still_removes_db_record(agent_service_url):
    """Vectors absent (404) is idempotent — DB row must still be removed."""
    client = _make_client(404)
    repo = InMemoryDocumentRepository()
    session = FakeSession()
    svc = DocumentService(
        repo=repo,
        session=session,
        http_client=client,
        agent_service_url=agent_service_url,
    )
    agent_id = uuid4()
    doc = make_document(agent_id=agent_id)
    await repo.create(doc)
    await svc.delete(doc.id)
    docs = await svc.list(agent_id, 0, 10)
    assert doc.id not in [d.id for d in docs]


@pytest.mark.asyncio
async def test_create_document_agent_service_500_raises(agent_service_url):
    client = _make_client_500()
    repo = InMemoryDocumentRepository()
    session = FakeSession()
    svc = DocumentService(
        repo=repo,
        session=session,
        http_client=client,
        agent_service_url=agent_service_url,
    )
    with pytest.raises(AgentServiceUnavailable):
        await svc.create(uuid4(), "f.pdf", "pdf", _MIN_PDF)


@pytest.mark.asyncio
async def test_create_document_agent_service_500_deletes_record(agent_service_url):
    client = _make_client_500()
    repo = InMemoryDocumentRepository()
    session = FakeSession()
    svc = DocumentService(
        repo=repo,
        session=session,
        http_client=client,
        agent_service_url=agent_service_url,
    )
    agent_id = uuid4()
    with pytest.raises(AgentServiceUnavailable):
        await svc.create(agent_id, "f.pdf", "pdf", _MIN_PDF)
    docs = await svc.list(agent_id, 0, 10)
    assert len(docs) == 0


@pytest.mark.asyncio
async def test_create_document_agent_service_500_commit_called_twice(agent_service_url):
    client = _make_client_500()
    repo = InMemoryDocumentRepository()
    session = FakeSession()
    svc = DocumentService(
        repo=repo,
        session=session,
        http_client=client,
        agent_service_url=agent_service_url,
    )
    with pytest.raises(AgentServiceUnavailable):
        await svc.create(uuid4(), "f.pdf", "pdf", _MIN_PDF)
    assert session.commit_count == 2


@pytest.mark.asyncio
async def test_create_document_agent_service_network_error_raises(agent_service_url):
    client = _make_client_network_error()
    repo = InMemoryDocumentRepository()
    session = FakeSession()
    svc = DocumentService(
        repo=repo,
        session=session,
        http_client=client,
        agent_service_url=agent_service_url,
    )
    with pytest.raises(AgentServiceUnavailable):
        await svc.create(uuid4(), "f.pdf", "pdf", _MIN_PDF)


@pytest.mark.asyncio
async def test_create_document_agent_service_network_error_deletes_record(
    agent_service_url,
):
    client = _make_client_network_error()
    repo = InMemoryDocumentRepository()
    session = FakeSession()
    svc = DocumentService(
        repo=repo,
        session=session,
        http_client=client,
        agent_service_url=agent_service_url,
    )
    agent_id = uuid4()
    with pytest.raises(AgentServiceUnavailable):
        await svc.create(agent_id, "f.pdf", "pdf", _MIN_PDF)
    docs = await svc.list(agent_id, 0, 10)
    assert len(docs) == 0


@pytest.mark.asyncio
async def test_get_document_wrong_agent_raises(service, repo):
    agent_id = uuid4()
    other_agent = uuid4()
    doc = make_document(agent_id=agent_id)
    await repo.create(doc)
    with pytest.raises(DocumentNotBelongToAgent):
        await service.get(other_agent, doc.id)
