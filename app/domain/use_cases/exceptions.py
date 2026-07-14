"""UseCase domain exceptions."""

from app.domain.shared.exceptions import DomainException


class UseCaseNotFound(DomainException):
    """Raised when a use case does not exist for the given identifier."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)
