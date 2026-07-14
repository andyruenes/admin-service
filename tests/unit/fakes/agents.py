"""In-memory AgentRepository fake — enforces status transitions and hard delete."""

from copy import deepcopy
from uuid import UUID

from app.domain.agents.entity import Agent
from app.domain.agents.exceptions import (
    AgentIsActive,
    AgentNotFound,
    InvalidStatusTransition,
)
from app.domain.agents.repository import AgentRepository

_ALLOWED_TRANSITIONS = frozenset({("draft", "active"), ("active", "inactive")})


class InMemoryAgentRepository(AgentRepository):
    """Fake backed by dict[UUID, Agent]. Filters deleted_at; enforces change_status transitions."""

    def __init__(self) -> None:
        self.store: dict[UUID, Agent] = {}

    async def get(self, id: UUID) -> Agent | None:
        agent = self.store.get(id)
        if agent is None or agent.deleted_at is not None:
            return None
        return deepcopy(agent)

    async def list(
        self,
        status: str | None,
        offset: int,
        limit: int,
        search: str | None = None,
    ) -> list[Agent]:
        items = [a for a in self.store.values() if a.deleted_at is None]
        if status is not None:
            items = [a for a in items if a.status == status]
        if search is not None and search.strip():
            q = search.strip().lower()
            items = [a for a in items if q in a.name.lower()]
        items.sort(key=lambda a: a.created_at, reverse=True)
        page = items[offset : offset + limit]
        return [deepcopy(a) for a in page]

    async def count(
        self,
        status: str | None = None,
        search: str | None = None,
    ) -> int:
        items = [a for a in self.store.values() if a.deleted_at is None]
        if status is not None:
            items = [a for a in items if a.status == status]
        if search is not None and search.strip():
            q = search.strip().lower()
            items = [a for a in items if q in a.name.lower()]
        return len(items)

    async def create(self, agent: Agent) -> Agent:
        self.store[agent.id] = deepcopy(agent)
        return deepcopy(self.store[agent.id])

    async def update(self, agent: Agent) -> Agent:
        if agent.id not in self.store:
            raise AgentNotFound(f"Agent not found for update: {agent.id}")
        self.store[agent.id] = deepcopy(agent)
        return deepcopy(self.store[agent.id])

    async def delete(self, id: UUID) -> None:
        if id not in self.store:
            raise AgentNotFound(f"Agent not found for delete: {id}")
        current = self.store[id]
        if current.deleted_at is not None:
            return
        if current.status == "active":
            raise AgentIsActive("Desactívalo antes de eliminarlo")
        del self.store[id]

    async def change_status(self, id: UUID, new_status: str) -> Agent:
        if id not in self.store:
            raise AgentNotFound(f"Agent not found: {id}")
        current = self.store[id]
        if current.deleted_at is not None:
            raise AgentNotFound(f"Agent not found: {id}")
        if (current.status, new_status) not in _ALLOWED_TRANSITIONS:
            raise InvalidStatusTransition(f"{current.status!r} → {new_status!r}")
        updated = Agent(
            id=current.id,
            name=current.name,
            llm_model=current.llm_model,
            created_at=current.created_at,
            updated_at=current.updated_at,
            status=new_status,
            description=current.description,
            deleted_at=current.deleted_at,
        )
        self.store[id] = updated
        return deepcopy(updated)
