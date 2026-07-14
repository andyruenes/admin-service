"""Kafka producer for outbound WhatsApp messages to hermes-server."""

import json
import logging

from aiokafka import AIOKafkaProducer

from app.config import settings

logger = logging.getLogger(__name__)


class WhatsappProducer:
    def __init__(self, producer: AIOKafkaProducer) -> None:
        self._producer = producer

    async def send_text(self, chatbot_id: str, to: str, body: str) -> None:
        """Publish a text message to hermes for WhatsApp delivery."""
        payload = {
            "chatbotId": chatbot_id,
            "to": to,
            "message": body,
            "type": "text",
        }
        print(
            f"[WA-PRODUCER] send_text -> topic={settings.KAFKA_OUTBOUND_TOPIC} "
            f"payload={payload}",
            flush=True,
        )
        await self._producer.send(
            settings.KAFKA_OUTBOUND_TOPIC,
            json.dumps(payload).encode(),
        )
        print(f"[WA-PRODUCER] send_text OK (to={to!r})", flush=True)
        logger.debug("Queued outbound WhatsApp message: agent=%s to=%s", chatbot_id, to)

    async def emit_session_event(
        self, 
        session_id: str, 
        user_id: str, 
        agent_id: str, 
        phone_number: str, 
        event_type: str  # "handoff" | "reactivate"
    ) -> None:
        from datetime import datetime
        payload = {
            "session_id": session_id,
            "user_id": user_id,
            "agent_id": agent_id,
            "phone_number": phone_number,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
        }
        print(
            f"[WA-PRODUCER] emit_session_event -> "
            f"topic={settings.KAFKA_SESSION_EVENTS_TOPIC} payload={payload}",
            flush=True,
        )
        await self._producer.send(
            settings.KAFKA_SESSION_EVENTS_TOPIC,
            json.dumps(payload).encode(),
        )
        print(f"[WA-PRODUCER] emit_session_event OK (event={event_type!r})", flush=True)