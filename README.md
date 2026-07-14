# admin-service

## Stack completo (tres repositorios)

**Requisitos:** Docker y Docker Compose v2 (`docker compose`).

Los tres servicios viven en **repos Git distintos**. En una carpeta padre (cualquier nombre), clona con estos nombres de directorio **exactos**:

```bash
git clone <url-admin-service> admin-service
git clone <url-conversation-service> conversation-service
git clone <url-agent-service> agent-service
```

Copia el compose unificado al padre (donde están las tres carpetas) y arranca desde ahí:

```bash
cp admin-service/project.docker-compose.yml ./docker-compose.yml
# opcional: .env al lado de docker-compose.yml (p. ej. OPENAI_API_KEY, OPENAI_BASE_URL)
docker compose up --build
# en segundo plano: docker compose up --build -d
```

Tras cambiar dependencias (`pyproject.toml`, `Dockerfile`, etc.), vuelve a construir imágenes: `docker compose build` o `docker compose up --build`.

| Servicio (compose) | Puerto host | OpenAPI / docs |
|--------------------|------------:|----------------|
| conversation-api | 8000 | http://localhost:8000/docs |
| admin-api | 8001 | http://localhost:8001/docs |
| agent-service | 8002 | http://localhost:8002/docs |
| chromadb | 8003 | API HTTP de Chroma (sin `/docs` FastAPI) |
| postgres-conversation | 5432 | — |
| postgres-admin | 5433 | — |
| rabbitmq | 5672 (AMQP), 15672 (UI) | UI: http://localhost:15672 |
| redis | 6379 | — |

Detalle y perfiles opcionales (`--profile test`, etc.): comentarios al inicio de `project.docker-compose.yml`.

---

## Cómo ejecutar en aislamiento
```bash
docker-compose --parallel=$(nproc) up --build --force-recreate -d
# o en Windows
docker-compose --parallel={{cantidad de núcleos}} up --build --force-recreate -d
```

API disponible en: `http://localhost:8001`  
Documentación interactiva: `http://localhost:8001/docs`

El puerto **8001** en el host coincide con **`admin-api`** en el stack unificado (`project.docker-compose.yml`); dentro del contenedor la app sigue escuchando en **8000**.

## Notas
- El estado del agente en JSON usa **`draft`**, **`active`** e **`inactive`**. Las transiciones permitidas equivalen a **borrador → activo → inactivo** (`draft` → `active` → `inactive`). Cualquier otra transición dev **422** (`invalid_status_transition`).
- **DELETE** de un agente es **borrado físico** en base de datos (cascada sobre recursos relacionados), después de pedir a agent-service el borrado de vectores. Devuelve **409** si el agente sigue **`active`** (hay que pasarlo a **`inactive`** antes). La columna `deleted_at` existe en el modelo pero el flujo de eliminación actual no hace *soft delete*.
- El `name` de una herramienta del catálogo debe cumplir el patrón `^[a-z0-9_]+$`, de lo contrario la validación devuelve 422.
- La `respuesta` de un caso de uso tiene un mínimo de 10 caracteres; en el listado se expone `respuesta_truncada` (80 chars).
- La subida de documentos usa **multipart/form-data** con el campo `file`; máximo 10 MB; tipos admitidos: **.pdf**, **.txt**, **.docx** y **.md** (según `Content-Type` o extensión).
- Las sesiones de prueba son efímeras (en memoria). DELETE devuelve 200 con una nueva sesión en el cuerpo (no 204).
