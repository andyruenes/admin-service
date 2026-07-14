"""Shared pytest fixtures: FakeSession, fake HTTP client, mock agent-service."""

import httpx
import pytest


class FakeSession:
    """No-op session — satisfies the session.commit() call in services."""

    commit_count: int = 0

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        pass


@pytest.fixture
def fake_session():
    """No-op session — satisfies the session.commit() call in services."""
    return FakeSession()


@pytest.fixture
def fake_http_client():
    """
    httpx.AsyncClient backed by a mock transport.
    Default handler: returns httpx.Response(200).
    Tests that need different behavior create their own client inline.
    """

    async def default_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    transport = httpx.MockTransport(default_handler)
    return httpx.AsyncClient(transport=transport)


@pytest.fixture
def mock_agent_service_ok(fake_http_client):
    """Pre-configured fake_http_client that returns 201 for any POST."""

    async def handler_201(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201)

    transport = httpx.MockTransport(handler_201)
    return httpx.AsyncClient(transport=transport)
