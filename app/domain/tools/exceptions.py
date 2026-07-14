"""Tool catalog and agent-tool domain exceptions."""

from app.domain.shared.exceptions import DomainException


class ToolNotFound(DomainException):
    """Raised when a catalog tool does not exist for the given identifier."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)


class AgentToolNotFound(DomainException):
    """Raised when an agent-tool association does not exist."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)


class ToolAlreadyExists(DomainException):
    """Raised when creating a catalog tool would violate uniqueness (e.g. name)."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)


class AgentToolAlreadyAttached(DomainException):
    """Raised when attach would duplicate an existing agent-tool pair."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)
