"""Document domain exceptions."""

from app.domain.shared.exceptions import DomainException


class DocumentNotFound(DomainException):
    """Raised when a document does not exist for the given identifier."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)


class DocumentNotBelongToAgent(DomainException):
    """Raised when a document is not owned by the expected agent."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)


class AgentServiceUnavailable(DomainException):
    """Raised when the agent service (e.g. index endpoint) is unreachable or returns error."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)
