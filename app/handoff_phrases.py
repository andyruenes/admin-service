"""Detección de las frases de derivación/reactivación en el camino WhatsApp.

El admin-service es el único servicio conectado a hermes, así que es quien debe
emitir el evento de sesión (handoff/reactivate) al topic
`chatbot.whatsapp.session.events`. Para decidir cuándo emitir necesita reconocer
las mismas frases que usa el conversation-service. La lógica de normalización es
idéntica (minúsculas, sin acentos, sin puntuación, espacios colapsados) para que
el match sea tolerante al punto final, mayúsculas, acentos y espacios que el LLM
o el operador suelen variar.

Fuente de verdad de las frases: deben coincidir con las del conversation-service
(`app/config.py`) y con la instrucción que el agent-service inyecta al modelo.
"""

from __future__ import annotations

import re
import unicodedata

HANDOFF_TO_OPERATOR_PHRASE = "Derivando a operador humano, enseguida le atenderemos"
REACTIVATE_AI_PHRASE = (
    "Le pondré en contacto con la inteligencia artificial para que siga su conversación"
)


def _normalize_phrase(text: str) -> str:
    """Minúsculas, sin acentos, sin puntuación y con espacios colapsados."""
    t = unicodedata.normalize("NFD", text.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")  # quita acentos
    t = re.sub(r"[^\w\s]", " ", t)  # quita toda la puntuación
    t = re.sub(r"\s+", " ", t).strip()
    return t


def matches_handoff_phrase(text: str) -> bool:
    """True si `text` es —o empieza con— la frase de derivación."""
    if not text:
        return False
    return _normalize_phrase(text).startswith(
        _normalize_phrase(HANDOFF_TO_OPERATOR_PHRASE)
    )


def matches_reactivate_phrase(text: str) -> bool:
    """True si `text` es —o empieza con— la frase de reactivación."""
    if not text:
        return False
    return _normalize_phrase(text).startswith(
        _normalize_phrase(REACTIVATE_AI_PHRASE)
    )
