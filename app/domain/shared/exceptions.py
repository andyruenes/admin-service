"""Domain-level exceptions. No framework dependencies."""


class DomainException(Exception):  # noqa: N818
    """Base exception for domain errors.

    Carries a human-readable message and an optional machine-friendly code.
    """

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class SessionNotFound(DomainException):
    """Raised when a test session does not exist for the given session_id."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)
