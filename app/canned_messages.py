"""Mensajes fijos (no generados por el LLM) que envía el admin-service."""

# Respuesta automática cuando el usuario envía un archivo/multimedia (pdf, docx,
# txt, audio, video, imagen, sticker, etc.) en vez de texto. El asistente NO debe
# interpretar ni analizar el contenido; solo invita a continuar por texto.
MEDIA_NOT_SUPPORTED_MESSAGE = (
    "Gracias por su mensaje. Por políticas de atención de la empresa, en este "
    "momento solo gestionamos consultas y pedidos mediante mensajes de texto. Le "
    "agradeceríamos que escribiera su consulta o pedido y con mucho gusto le ayudaré."
)
