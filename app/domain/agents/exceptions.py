"""Agent domain exceptions."""

from app.domain.shared.exceptions import DomainException


class AgentNotFound(DomainException):
    """Raised when an agent does not exist for the given identifier."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)


class AgentAlreadyExists(DomainException):
    """Raised when creating an agent would violate uniqueness (e.g. name)."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)


class AgentIsActive(DomainException):
    """Raised when an operation is not allowed because the agent is still active."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)


class InvalidStatusTransition(DomainException):
    """Raised when an agent status transition is not allowed (draft→active, active→inactive only)."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)


class PhoneAccountAlreadyLinked(DomainException):
    """Raised when an agent already has a phone account linked."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)


class PhoneAccountNotLinked(DomainException):
    """Raised when an operation requires a phone account but none is linked."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)
