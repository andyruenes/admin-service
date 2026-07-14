"""Exception handlers by domain; register all with the FastAPI app."""

from fastapi import FastAPI

from app.exception_handlers import agents, documents, prompts, shared, tools, use_cases


def register_exception_handlers(app: FastAPI) -> None:
    """Register all domain exception handlers on the app. Call after creating the app."""
    agents.register(app)
    prompts.register(app)
    documents.register(app)
    use_cases.register(app)
    tools.register(app)
    shared.register(app)  # SessionNotFound, DomainException last (fallback)
