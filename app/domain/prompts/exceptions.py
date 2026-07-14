"""Prompt version domain exceptions."""

from app.domain.shared.exceptions import DomainException


class PromptNotFound(DomainException):
    """Raised when a prompt version does not exist for the given identifier."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)


class PromptVersionConflict(DomainException):
    """Raised on uniqueness or active-version constraint violation."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)


class NoActivePrompt(DomainException):
    """Raised when no active prompt version exists for the agent."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)
