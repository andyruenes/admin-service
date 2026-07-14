"""Kafka consumer for inbound WhatsApp messages from hermes-server."""

import asyncio
import json
import logging

import httpx
from aiokafka import AIOKafkaConsumer

from app.canned_messages import MEDIA_NOT_SUPPORTED_MESSAGE
from app.handoff_phrases import matches_handoff_phrase, matches_reactivate_phrase
from app.kafka.producer import WhatsappProducer
from app.services.whatsapp_chat import WhatsappChatService
from app.clients.conversation_client import ConversationClient

logger = logging.getLogger(__name__)


async def _dispatch(
    payload: dict,
    http_client: httpx.AsyncClient,
    producer: WhatsappProducer,
) -> None:
    """Full pipeline for one inbound message: persist → LLM → reply."""
    agent_id_str: str = payload.get("chatbotId", "")
    phone_number: str = payload.get("from", "")
    body: str = payload.get("body", "")
    external_message_id: str = payload.get("messageId", "")
    sender_type: str = payload.get("senderType", "user")
    # Tipo de mensaje que envía hermes: "text" para mensajes de texto y "media"
    # para CUALQUIER archivo no soportado (pdf, docx, txt, audio, video, imagen,
    # sticker, etc.). Si falta, se asume "text" por compatibilidad. Se aceptan
    # también valores específicos ("image", "audio", ...) tratándolos como media.
    msg_type: str = payload.get("type", payload.get("messageType", "text"))
    is_media: bool = msg_type != "text"

    print("[WA-CONSUMER] ================= INBOUND =================", flush=True)
    print(f"[WA-CONSUMER] payload completo: {payload}", flush=True)
    print(
        f"[WA-CONSUMER] from={phone_number!r} senderType={sender_type!r} "
        f"type={msg_type!r} agentId={agent_id_str!r} "
        f"messageId={external_message_id!r} body={body!r}",
        flush=True,
    )

    # Campos mínimos: para texto exigimos body; para media el body puede venir
    # vacío (el archivo no trae texto).
    if not agent_id_str or not phone_number or (not is_media and not body):
        print(f"[WA-CONSUMER] FALTAN CAMPOS REQUERIDOS -> descarto: {payload}", flush=True)
        logger.warning("Inbound message missing required fields, skipping: %s", payload)
        return

    conversation_client = ConversationClient()

    # ── Rama MEDIA / ARCHIVO (cualquier cosa que no sea texto) ─────────────────
    # El usuario envió un archivo no soportado. Respondemos con un texto fijo, SIN
    # llamar al agente y SIN guardar nada en base de datos (ni el mensaje del
    # usuario ni la respuesta), para no meter ruido en el historial. El bot solo
    # procesa texto.
    if is_media:
        if sender_type == "operator":
            # El operador humano envió un archivo al usuario: no lo procesamos.
            print(
                "[WA-CONSUMER] media de OPERADOR -> ignorado (sin guardar, sin responder)",
                flush=True,
            )
            return
        try:
            derived = await conversation_client.is_session_derived(phone_number)
        except Exception as exc:
            print(
                f"[WA-CONSUMER] ERROR consultando is_session_derived (media): {exc!r}",
                flush=True,
            )
            derived = False
        if derived:
            # Hay un operador atendiendo; el bot no debe responder. El operador
            # verá el archivo directamente en su WhatsApp.
            print(
                "[WA-CONSUMER] media de usuario en sesión DERIVADA -> no responde el bot",
                flush=True,
            )
            return
        print(
            f"[WA-CONSUMER] media de usuario (type={msg_type!r}) -> respuesta fija, "
            "sin guardar ni llamar al agente",
            flush=True,
        )
        try:
            await producer.send_text(
                chatbot_id=agent_id_str,
                to=phone_number,
                body=MEDIA_NOT_SUPPORTED_MESSAGE,
            )
            print(
                f"[WA-CONSUMER] respuesta fija de media ENVIADA (to={phone_number!r})",
                flush=True,
            )
        except Exception as exc:
            print(f"[WA-CONSUMER] ERROR enviando respuesta fija de media: {exc!r}", flush=True)
            logger.exception("Failed to send media-not-supported reply")
        return

    # ── Rama OPERADOR (dueño del número) ──────────────────────────────────────
    if sender_type == "operator":
        print(
            f"[WA-CONSUMER] -> RAMA OPERATOR. POST /messages/operator "
            f"(user_id={phone_number!r}, content={body!r})",
            flush=True,
        )
        try:
            result = await conversation_client.save_operator_message(
                user_id=phone_number,
                agent_id=agent_id_str,
                content=body,
            )
            print(f"[WA-CONSUMER] operator message OK -> respuesta={result}", flush=True)
        except Exception as exc:
            print(f"[WA-CONSUMER] ERROR guardando operator message: {exc!r}", flush=True)
            logger.exception("Failed to save operator message to conversation-service")
            return

        # REACTIVACIÓN: si el dueño del número escribió la frase de reactivación,
        # el admin-service (único conectado a hermes) emite el evento de sesión al
        # topic chatbot.whatsapp.session.events para que hermes reanude el bot.
        if matches_reactivate_phrase(body):
            session_id = (result or {}).get("session_id")
            print(
                f"[WA-CONSUMER] REACTIVATE detectado -> emit_session_event "
                f"(session_id={session_id!r})",
                flush=True,
            )
            try:
                await producer.emit_session_event(
                    session_id=str(session_id) if session_id else "",
                    user_id=phone_number,
                    agent_id=agent_id_str,
                    phone_number=phone_number,
                    event_type="reactivate",
                )
            except Exception as exc:
                print(
                    f"[WA-CONSUMER] ERROR emitiendo reactivate a hermes: {exc!r}",
                    flush=True,
                )
                logger.exception("Failed to emit reactivate session event")
        return

    print(f"[WA-CONSUMER] -> RAMA USER (senderType={sender_type!r})", flush=True)

    # 1. Guardar mensaje de usuario en conversation-service
    try:
        await conversation_client.save_message(
            user_id=phone_number,
            agent_id=agent_id_str,
            role="user",
            content=body,
            correlation_id=None,
        )
        print("[WA-CONSUMER] mensaje de usuario guardado (role=user)", flush=True)
    except Exception as exc:
        print(f"[WA-CONSUMER] ERROR guardando user message: {exc!r}", flush=True)
        logger.exception("Failed to save user message to conversation-service")
        return

    # 1.b ¿La conversación ya fue derivada a un operador humano?
    try:
        derived = await conversation_client.is_session_derived(phone_number)
        print(
            f"[WA-CONSUMER] is_session_derived({phone_number!r}) = {derived}",
            flush=True,
        )
        if derived:
            print(
                "[WA-CONSUMER] sesión DERIVADA -> NO responde la IA (atiende operador)",
                flush=True,
            )
            logger.info(
                "Session for %s is derived to operator; skipping AI response",
                phone_number,
            )
            return
    except Exception as exc:
        print(
            f"[WA-CONSUMER] ERROR consultando is_session_derived: {exc!r} "
            f"-> continúo con la IA",
            flush=True,
        )
        logger.exception("Failed to check derived state; continuing with AI")

    # 2. Obtener historial del conversation-service
    try:
        history = await conversation_client.get_history(user_id=phone_number, limit=20)
        print(f"[WA-CONSUMER] historial recibido: {len(history)} mensajes", flush=True)
    except Exception as exc:
        print(f"[WA-CONSUMER] ERROR obteniendo historial: {exc!r}", flush=True)
        logger.exception("Failed to get history from conversation-service")
        history = []

    # 3. Llamar al agent-service con el historial
    chat_service = WhatsappChatService(http_client)
    try:
        response_text = await chat_service.get_response(
            agent_id=agent_id_str,
            phone_number=phone_number,
            message=body,
            history=history[:-1],  # Excluir mensaje actual
        )
        print(f"[WA-CONSUMER] respuesta del agente: {response_text!r}", flush=True)
    except Exception as exc:
        print(f"[WA-CONSUMER] ERROR llamando al agente: {exc!r}", flush=True)
        logger.exception("agent-service call failed")
        return

    # 4. Guardar respuesta del assistant en conversation-service
    assistant_result: dict | None = None
    try:
        assistant_result = await conversation_client.save_message(
            user_id=phone_number,
            agent_id=agent_id_str,
            role="assistant",
            content=response_text,
            correlation_id=None,
        )
        print(
            "[WA-CONSUMER] respuesta del assistant guardada (role=assistant)",
            flush=True,
        )
    except Exception as exc:
        print(f"[WA-CONSUMER] ERROR guardando assistant message: {exc!r}", flush=True)
        logger.exception("Failed to save assistant message to conversation-service")

    # 4.b DERIVACIÓN: si la IA respondió con la frase de handoff, el admin-service
    # (único conectado a hermes) emite el evento de sesión al topic
    # chatbot.whatsapp.session.events para que hermes pause el bot / avise al
    # operador. El conversation-service ya marcó is_derived al guardar el mensaje.
    if matches_handoff_phrase(response_text):
        session_id = (assistant_result or {}).get("session_id")
        print(
            f"[WA-CONSUMER] HANDOFF detectado -> emit_session_event "
            f"(session_id={session_id!r})",
            flush=True,
        )
        try:
            await producer.emit_session_event(
                session_id=str(session_id) if session_id else "",
                user_id=phone_number,
                agent_id=agent_id_str,
                phone_number=phone_number,
                event_type="handoff",
            )
        except Exception as exc:
            print(
                f"[WA-CONSUMER] ERROR emitiendo handoff a hermes: {exc!r}",
                flush=True,
            )
            logger.exception("Failed to emit handoff session event")

    # 5. Publicar respuesta a WhatsApp
    try:
        await producer.send_text(
            chatbot_id=agent_id_str,
            to=phone_number,
            body=response_text,
        )
        print(
            f"[WA-CONSUMER] respuesta ENVIADA a WhatsApp (to={phone_number!r})",
            flush=True,
        )
    except Exception as exc:
        print(f"[WA-CONSUMER] ERROR enviando a WhatsApp: {exc!r}", flush=True)
        logger.exception("Failed to publish outbound message")


async def consume_inbound_messages(
    consumer: AIOKafkaConsumer,
    http_client: httpx.AsyncClient,
    producer: WhatsappProducer,
) -> None:
    """Main consumer loop. Runs as a background task for the app lifespan."""
    try:
        async for msg in consumer:
            try:
                payload = json.loads(msg.value)
                await _dispatch(payload, http_client, producer)
            except Exception:
                logger.exception(
                    "Failed to handle inbound message: offset=%s", msg.offset
                )
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("Inbound Kafka consumer crashed")
