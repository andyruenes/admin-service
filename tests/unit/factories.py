"""Entity factories for tests — one per domain entity, sensible defaults, override via **kwargs."""

from datetime import UTC, datetime
from uuid import uuid4

from app.domain.agents.entity import Agent
from app.domain.documents.entity import Document
from app.domain.prompts.entity import PromptVersion
from app.domain.tools.entity import AgentTool, Tool
from app.domain.use_cases.entity import UseCase


def make_agent(**kwargs) -> Agent:
    now = datetime.now(UTC)
    return Agent(
        id=kwargs.pop("id", uuid4()),
        name=kwargs.pop("name", "test-agent"),
        description=kwargs.pop("description", "A test agent"),
        llm_model=kwargs.pop("llm_model", "gpt-4o"),
        status=kwargs.pop("status", "draft"),
        deleted_at=kwargs.pop("deleted_at", None),
        created_at=kwargs.pop("created_at", now),
        updated_at=kwargs.pop("updated_at", now),
        phone_account_id=kwargs.pop("phone_account_id", None),
    )


def make_prompt_version(**kwargs) -> PromptVersion:
    now = datetime.now(UTC)
    return PromptVersion(
        id=kwargs.pop("id", uuid4()),
        agent_id=kwargs.pop("agent_id", uuid4()),
        version_number=kwargs.pop("version_number", 1),
        content=kwargs.pop("content", "Test prompt content"),
        created_at=kwargs.pop("created_at", now),
        is_active=kwargs.pop("is_active", False),
    )


def make_use_case(**kwargs) -> UseCase:
    now = datetime.now(UTC)
    return UseCase(
        id=kwargs.pop("id", uuid4()),
        agent_id=kwargs.pop("agent_id", uuid4()),
        question=kwargs.pop("question", "Test question?"),
        answer=kwargs.pop("answer", "A" * 10),
        created_at=kwargs.pop("created_at", now),
        updated_at=kwargs.pop("updated_at", now),
    )


def make_tool(**kwargs) -> Tool:
    now = datetime.now(UTC)
    return Tool(
        id=kwargs.pop("id", uuid4()),
        name=kwargs.pop("name", "test_tool"),
        description=kwargs.pop("description", "A test tool"),
        function_ref=kwargs.pop("function_ref", "ref://test"),
        created_at=kwargs.pop("created_at", now),
    )


def make_agent_tool(**kwargs) -> AgentTool:
    now = datetime.now(UTC)
    return AgentTool(
        agent_id=kwargs.pop("agent_id", uuid4()),
        tool_id=kwargs.pop("tool_id", uuid4()),
        updated_at=kwargs.pop("updated_at", now),
        is_active=kwargs.pop("is_active", False),
        name=kwargs.pop("name", None),
        description=kwargs.pop("description", None),
    )


def make_document(**kwargs) -> Document:
    now = datetime.now(UTC)
    return Document(
        id=kwargs.pop("id", uuid4()),
        agent_id=kwargs.pop("agent_id", uuid4()),
        file_name=kwargs.pop("file_name", "test.pdf"),
        file_type=kwargs.pop("file_type", "pdf"),
        created_at=kwargs.pop("created_at", now),
        status=kwargs.pop("status", "indexing"),
        chunks_total=kwargs.pop("chunks_total", None),
        error_message=kwargs.pop("error_message", None),
    )
