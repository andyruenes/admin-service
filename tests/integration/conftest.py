"""Integration test fixtures: live HTTP client, DB session, truncation, respx agent-service mock."""

import asyncio
import os
import re
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
import respx
from sqlalchemy import text


def _load_env_tests_file() -> None:
    """Load key=value pairs from repo-root .env.tests for pytest runs."""
    env_path = Path(__file__).resolve().parents[2] / ".env.tests"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_env_tests_file()

TEST_API_BASE_URL = os.getenv("TEST_API_BASE_URL", "http://localhost:8001")
TEST_MODE = os.getenv("TEST_MODE", "isolation").strip().lower()


def is_integration_mode() -> bool:
    return TEST_MODE == "integration"


from app import models  # noqa: F401,E402 — register all ORM tables with Base.metadata
from app.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "isolation: runs only in TEST_MODE=isolation")
    config.addinivalue_line(
        "markers", "integration: runs only in TEST_MODE=integration"
    )
    config.addinivalue_line("markers", "requires_agent: depends on live agent-service")


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if TEST_MODE not in ("isolation", "integration"):
        raise pytest.UsageError(
            f"Invalid TEST_MODE={TEST_MODE!r}. Use 'isolation' or 'integration'."
        )
    for item in items:
        has_integration_marker = item.get_closest_marker("integration") is not None
        has_isolation_marker = item.get_closest_marker("isolation") is not None
        if has_integration_marker and TEST_MODE != "integration":
            item.add_marker(pytest.mark.skip(reason="requires TEST_MODE=integration"))
        if has_isolation_marker and TEST_MODE != "isolation":
            item.add_marker(pytest.mark.skip(reason="requires TEST_MODE=isolation"))


@pytest.fixture(scope="session")
def event_loop():
    """
    Session-scoped event loop so client and db_session run in the same loop as tests.
    Required to avoid "bound to a different event loop" when using session-scoped async fixtures.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def wait_for_api(url: str, retries: int = 10, delay: float = 0.5) -> None:
    """Poll the API until it responds (for CI when docker compose starts just before pytest)."""
    for _ in range(retries):
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(url, timeout=2.0)
                if r.status_code < 500:
                    return
        except Exception:
            pass
        await asyncio.sleep(delay)
    raise RuntimeError(
        f"API at {url} did not become ready in time. "
        "Start the app first (e.g. 'docker compose up' or 'uv run uvicorn app.main:app --reload'), then run pytest."
    )


def _app_table_names() -> list[str]:
    """All app table names from ORM metadata (avoids forgetting new tables when schema evolves)."""
    return list(Base.metadata.tables.keys())


async def _truncate_all(session: Any) -> None:
    """Truncate all app tables. Uses CASCADE so order is irrelevant; new tables are included via metadata."""
    names = _app_table_names()
    if not names:
        return
    await session.execute(
        text("TRUNCATE {} RESTART IDENTITY CASCADE".format(", ".join(names)))
    )
    await session.commit()


@pytest_asyncio.fixture(scope="session")
async def client():
    """Session-scoped HTTP client for the live FastAPI app.
    Depends on event_loop (session-scoped) above; do not change to function scope.
    """
    await wait_for_api(TEST_API_BASE_URL)
    c = httpx.AsyncClient(base_url=TEST_API_BASE_URL)
    yield c
    try:
        await c.aclose()
    except RuntimeError as e:
        if "Event loop is closed" not in str(e):
            raise


@pytest.fixture
def require_integration_mode() -> None:
    if not is_integration_mode():
        pytest.skip("requires TEST_MODE=integration")


@pytest_asyncio.fixture(scope="session")
async def db_session():
    """Session-scoped DB session for truncation and verification against real PostgreSQL."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="module", autouse=True)
async def truncate_before_module(db_session):
    """Truncate all app tables at the start of each test module (FK-safe order)."""
    await _truncate_all(db_session)
    yield


# Base URL of the live API under test (must match client base_url so pass_through matches).
TEST_CLIENT_BASE_URL = TEST_API_BASE_URL


@pytest.fixture
def mock_agent_service():
    """respx mock for agent-service; intercepts calls to settings.AGENT_SERVICE_URL. Per-test scope.
    Pass-through for TEST_CLIENT_BASE_URL so test client requests hit the real app.
    Do not use base_url on the router: it would bind route host/port to AGENT_SERVICE_URL, so
    requests to the admin app (e.g. http://localhost:8001) would not match and would get
    auto-mocked (200 empty body).
    """
    with respx.mock(
        assert_all_mocked=False,
        assert_all_called=False,
    ) as mock:
        for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            mock.route(
                method=method,
                url__startswith=TEST_CLIENT_BASE_URL + "/",
            ).pass_through()
        mock.post(
            url__startswith=settings.AGENT_SERVICE_URL.rstrip("/")
            + "/agent/documents/index",
        ).respond(201)
        mock.delete(
            url=re.compile(
                re.escape(settings.AGENT_SERVICE_URL.rstrip("/"))
                + r"/agent/documents/.+/vectors"
            ),
        ).respond(200)
        mock.delete(
            url=re.compile(
                re.escape(settings.AGENT_SERVICE_URL.rstrip("/"))
                + r"/agent/agents/.+/vectors"
            ),
        ).respond(200)
        yield mock
