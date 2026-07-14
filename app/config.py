"""Application settings loaded from environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    AGENT_SERVICE_URL: str = "http://agent-service:8000"
    CONVERSATION_SERVICE_URL: str = "http://conversation-service:8000"
    # Document indexing (embeddings + Chroma) often exceeds 30s; short timeouts cause 502 + rolled-back rows.
    AGENT_HTTP_TIMEOUT_SECONDS: float = 300.0
    GRPC_SERVER_PORT: int = 50051
    HERMES_GRPC_URL: str = "hermes-server:50051"
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_CONSUMER_GROUP_ID: str = "admin-service"
    KAFKA_INBOUND_TOPIC: str = "channel.whatsapp.messages.received"
    KAFKA_OUTBOUND_TOPIC: str = "channel.whatsapp.messages.send"
    KAFKA_SESSION_EVENTS_TOPIC: str = "chatbot.whatsapp.session.events"


settings = Settings()  # type: ignore[call-arg]
