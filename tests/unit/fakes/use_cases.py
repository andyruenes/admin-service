"""In-memory UseCaseRepository fake — scoped by agent_id, get_random via random.sample."""

import random
from copy import deepcopy
from uuid import UUID

from app.domain.use_cases.entity import UseCase
from app.domain.use_cases.exceptions import UseCaseNotFound
from app.domain.use_cases.repository import UseCaseRepository


class InMemoryUseCaseRepository(UseCaseRepository):
    """Fake backed by list[UseCase]. All operations filter by agent_id where applicable."""

    def __init__(self) -> None:
        self.store: list[UseCase] = []

    def _by_agent(self, agent_id: UUID) -> list[UseCase]:
        return [u for u in self.store if u.agent_id == agent_id]

    async def get(self, id: UUID, *, agent_id: UUID | None = None) -> UseCase | None:
        for u in self.store:
            if u.id == id:
                if agent_id is not None and u.agent_id != agent_id:
                    raise UseCaseNotFound(
                        f"Use case {id} belongs to agent {u.agent_id}, not {agent_id}"
                    )
                return deepcopy(u)
        if agent_id is not None:
            raise UseCaseNotFound(f"Use case not found: {id}")
        return None

    async def list_by_agent(
        self,
        agent_id: UUID,
        offset: int,
        limit: int,
        search: str | None = None,
    ) -> list[UseCase]:
        items = sorted(
            self._by_agent(agent_id),
            key=lambda u: u.updated_at,
            reverse=True,
        )
        if search is not None and search.strip():
            term = search.strip().lower()
            items = [
                u
                for u in items
                if term in (u.question or "").lower()
                or term in (u.answer or "").lower()
            ]
        page = items[offset : offset + limit]
        return [deepcopy(u) for u in page]

    async def create(self, use_case: UseCase) -> UseCase:
        self.store.append(deepcopy(use_case))
        return deepcopy(self.store[-1])

    async def update(self, use_case: UseCase) -> UseCase:
        for i, u in enumerate(self.store):
            if u.id == use_case.id:
                if u.agent_id != use_case.agent_id:
                    raise UseCaseNotFound(
                        f"Use case {use_case.id} belongs to agent {u.agent_id}, "
                        f"not {use_case.agent_id}"
                    )
                self.store[i] = deepcopy(use_case)
                return deepcopy(self.store[i])
        raise UseCaseNotFound(f"Use case not found for update: {use_case.id}")

    async def delete(self, id: UUID) -> None:
        for i, u in enumerate(self.store):
            if u.id == id:
                del self.store[i]
                return
        raise UseCaseNotFound(f"Use case not found for delete: {id}")

    async def get_random(self, agent_id: UUID, limit: int) -> list[UseCase]:
        pool = self._by_agent(agent_id)
        n = min(limit, len(pool))
        if n == 0:
            return []
        sampled = random.sample(pool, n)
        return [deepcopy(u) for u in sampled]
