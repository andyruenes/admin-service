"""FastAPI application entrypoint (used by Docker/uvicorn)."""

import asyncio
from contextlib import asynccontextmanager

import grpc
import httpx
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agents import router as agents_router
from app.api.conversations import router as conversations_router
from app.api.cost import router as costs_router
from app.api.documents import router as documents_router
from app.api.prompts import router as prompts_router
from app.api.test_sessions import router as test_sessions_router
from app.api.tools import router as tools_router
from app.api.use_cases import router as use_cases_router
from app.config import settings
from app.db.session import engine
from app.exception_handlers import register_exception_handlers
from app.grpc.hermes.client import HermesClient
from app.grpc.server import start_grpc_server, stop_grpc_server
from app.kafka.consumer import consume_inbound_messages
from app.kafka.producer import WhatsappProducer


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(
        base_url=settings.AGENT_SERVICE_URL,
        timeout=settings.AGENT_HTTP_TIMEOUT_SECONDS,
    )
    app.state.test_sessions = {}
    app.state.hermes_channel = grpc.aio.insecure_channel(settings.HERMES_GRPC_URL)
    app.state.hermes_client = HermesClient(app.state.hermes_channel)
    await start_grpc_server()

    raw_producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
    )
    await raw_producer.start()
    app.state.whatsapp_producer = WhatsappProducer(raw_producer)

    consumer = AIOKafkaConsumer(
        settings.KAFKA_INBOUND_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP_ID,
        auto_offset_reset="latest",
        enable_auto_commit=True,
    )
    await consumer.start()
    app.state.kafka_consumer = consumer
    consumer_task = asyncio.create_task(
        consume_inbound_messages(
            consumer, app.state.http_client, app.state.whatsapp_producer
        )
    )

    try:
        yield
    finally:
        consumer_task.cancel()
        await consumer.stop()
        await raw_producer.stop()
        await stop_grpc_server()
        await app.state.hermes_channel.close()
        await app.state.http_client.aclose()
        await engine.dispose()


app = FastAPI(
    title="admin-service",
    version="1.0.0",
    root_path="/api/admin",
    lifespan=lifespan,
)

register_exception_handlers(app)

# Dev / disposable UI (e.g. ui/index.html on another port) — same pattern as agent-service.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents_router, prefix="/admin")
app.include_router(prompts_router, prefix="/admin")
app.include_router(use_cases_router, prefix="/admin")
app.include_router(tools_router, prefix="/admin")
app.include_router(documents_router, prefix="/admin")
app.include_router(test_sessions_router, prefix="/admin")
app.include_router(conversations_router)
app.include_router(costs_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
