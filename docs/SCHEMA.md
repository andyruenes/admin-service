# Database schema

Tables and columns (English). All primary keys are UUID; timestamps use server defaults where noted.

---

## agents (Agent)

| Column        | Type           | Constraints                    |
|---------------|----------------|--------------------------------|
| id            | UUID           | PK, default uuid4              |
| name          | String(100)    | NOT NULL, UNIQUE               |
| description   | Text           | nullable                       |
| llm_model     | String(50)     | NOT NULL                       |
| status        | agent_status   | NOT NULL, default `draft`      |
| deleted_at    | DateTime(TZ)   | nullable (soft delete)         |
| created_at    | DateTime       | NOT NULL, default now()        |
| updated_at    | DateTime       | NOT NULL, default/on update now() |

**Enum `agent_status`:** `draft` \| `active` \| `inactive`

**Relations:** prompt_versions, agent_tools, documents, use_cases

---

## documents

| Column       | Type             | Constraints                    |
|--------------|------------------|--------------------------------|
| id           | UUID             | PK, default uuid4              |
| agent_id     | UUID             | NOT NULL, FK → agents.id (CASCADE) |
| file_name    | String(255)      | NOT NULL                       |
| file_type    | document_type    | NOT NULL                       |
| status       | document_status  | NOT NULL, default `indexing`   |
| chunks_total | Integer          | nullable                       |
| error_message| Text             | nullable                       |
| created_at   | DateTime         | NOT NULL, default now()         |

**Enum `document_type`:** `pdf` \| `txt` \| `docx`  
**Enum `document_status`:** `indexing` \| `indexed` \| `error`

**Constraints:**
- If `status = 'error'` then `error_message` must be NOT NULL.
- If `status = 'indexed'` then `chunks_total` must be NOT NULL.

**Relation:** agent (BotConfig)

---

## prompt_versions

| Column         | Type    | Constraints                    |
|----------------|---------|--------------------------------|
| id             | UUID    | PK, default uuid4              |
| agent_id       | UUID    | NOT NULL, FK → agents.id (CASCADE) |
| version_number | Integer | NOT NULL                       |
| content        | Text    | NOT NULL                       |
| is_active      | Boolean | NOT NULL, default false         |
| created_at     | DateTime| NOT NULL, default now()         |

**Constraints:**
- UNIQUE (agent_id, version_number).
- At most one row per agent with `is_active = TRUE` (partial unique index).

**Relation:** agent (BotConfig)

---

## use_cases

| Column    | Type      | Constraints                    |
|-----------|-----------|--------------------------------|
| id        | UUID      | PK, default uuid4              |
| agent_id  | UUID      | NOT NULL, FK → agents.id (CASCADE) |
| question  | String(500)| NOT NULL                      |
| answer    | Text      | NOT NULL                       |
| created_at| DateTime  | NOT NULL, default now()         |
| updated_at| DateTime  | NOT NULL, default/on update now() |

**Constraints:** `length(question) > 0`, `length(answer) >= 10`

**Relation:** agent (BotConfig)

---

## tools_catalog

| Column      | Type        | Constraints                    |
|-------------|-------------|--------------------------------|
| id          | UUID        | PK, default uuid4              |
| name        | String(100) | NOT NULL, UNIQUE               |
| description | String(300) | NOT NULL                       |
| function_ref| String(200) | NOT NULL                       |
| created_at  | DateTime    | NOT NULL, default now()         |

**Constraint:** `name` must match `^[a-z0-9_]+$` (slug).

**Relation:** agent_tools (many-to-many with agents via agent_tools)

---

## agent_tools (association: agents ↔ tools_catalog)

| Column    | Type    | Constraints                    |
|-----------|---------|--------------------------------|
| agent_id  | UUID    | PK, FK → agents.id (CASCADE)   |
| tool_id   | UUID    | PK, FK → tools_catalog.id (CASCADE) |
| is_active | Boolean | NOT NULL, default false         |
| updated_at| DateTime| NOT NULL, default/on update now() |

**Relations:** agent (BotConfig), tool (ToolCatalog)

---

## Entity overview (YAML-style)

```yaml
agent (agents):
  id: UUID (PK)
  name: string, unique
  description: text, optional
  llm_model: string
  status: draft | active | inactive
  deleted_at: datetime (tz), optional
  created_at: datetime
  updated_at: datetime
  # relations: prompt_versions, agent_tools, documents, use_cases

document:
  id: UUID (PK)
  agent_id: UUID (FK → agent)
  file_name: string
  file_type: pdf | txt | docx
  status: indexing | indexed | error
  chunks_total: int, optional
  error_message: text, optional
  created_at: datetime

prompt_version:
  id: UUID (PK)
  agent_id: UUID (FK → agent)
  version_number: int
  content: text
  is_active: bool
  created_at: datetime

use_case:
  id: UUID (PK)
  agent_id: UUID (FK → agent)
  question: string
  answer: text
  created_at: datetime
  updated_at: datetime

tool_catalog (tools_catalog):
  id: UUID (PK)
  name: string, unique, slug
  description: string
  function_ref: string
  created_at: datetime

agent_tool (association):
  agent_id: UUID (PK, FK → agent)
  tool_id: UUID (PK, FK → tool_catalog)
  is_active: bool
  updated_at: datetime
```
