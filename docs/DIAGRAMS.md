# admin-service — Diagrams

Diagrams only; one-line title per diagram. If a type does not apply, it is skipped with a one-line reason.

---

## 1. Happy-path request lifecycle (HTTP in → DB out)

```mermaid
%% flowchart TD — happy-path request lifecycle (HTTP in → DB out)
flowchart TD
    Client[Client]
    FastAPI[FastAPI app]
    Deps[deps: get_session + get_*_service]
    Session[AsyncSession]
    Service[AgentService / DocumentService / ...]
    Repo[SQLAgentRepository / ...]
    ORM[BotConfig / Document / ...]
    DB[(PostgreSQL)]

    Client -->|HTTP| FastAPI
    FastAPI --> Deps
    Deps --> Session
    Deps --> Service
    Service -->|repo.get / create / update| Repo
    Repo --> Session
    Service -->|session.commit| Session
    Repo -->|select/insert/update| ORM
    ORM --> DB
```

---

## 2. Sequence: core use case (create agent)

```mermaid
%% sequenceDiagram — interaction between top modules for create-agent use case
sequenceDiagram
    participant Client
    participant Router as API Router
    participant Deps as deps
    participant Session as get_session
    participant Service as AgentService
    participant Repo as SQLAgentRepository
    participant DB as PostgreSQL

    Client->>Router: POST /agents
    Router->>Deps: Depends(get_agent_service)
    Deps->>Session: Depends(get_session)
    Session-->>Deps: AsyncSession
    Deps->>Repo: SQLAgentRepository(session)
    Deps->>Service: AgentService(repo, session)
    Deps-->>Router: AgentService
    Router->>Service: create(data)
    Service->>Service: build Agent entity
    Service->>Repo: create(agent)
    Repo->>DB: insert agents
    Repo-->>Service: Agent
    Service->>Session: commit()
    Session->>DB: COMMIT
    Service-->>Router: Agent
    Router-->>Client: 201 + body
```

---

## 3. Domain model — core entities and relationships

```mermaid
%% classDiagram — domain entities and their relationships
classDiagram
    class Agent {
        +UUID id
        +str name
        +str llm_model
        +datetime created_at
        +datetime updated_at
        +str status
        +str? description
        +datetime? deleted_at
    }
    class Document {
        +UUID id
        +UUID agent_id
        +str file_name
        +str file_type
        +datetime created_at
        +str status
        +int? chunks_total
        +str? error_message
    }
    class PromptVersion {
        +UUID id
        +UUID agent_id
        +int version_number
        +str content
        +datetime created_at
        +bool is_active
    }
    class UseCase {
        +UUID id
        +UUID agent_id
        +str pregunta
        +str respuesta
        +datetime created_at
        +datetime updated_at
    }
    class Tool {
        +UUID id
        +str name
        +str description
        +str function_ref
        +datetime created_at
    }
    class AgentTool {
        +UUID agent_id
        +UUID tool_id
        +datetime updated_at
        +bool is_active
    }

    Agent "1" --> "*" Document : has
    Agent "1" --> "*" PromptVersion : has
    Agent "1" --> "*" UseCase : has
    Agent "1" --> "*" AgentTool : has
    Tool "1" --> "*" AgentTool : has
```

---

## 4. Module dependency graph (circular deps flagged)

```mermaid
%% graph LR — module dependency graph; no circular deps in this project
graph LR
    subgraph entry
        main[app.main]
    end
    subgraph api
        deps[api.deps]
    end
    subgraph infra
        db_session[db.session]
        db_base[db.base]
        config[config]
        repos[repositories]
        models[models]
    end
    subgraph app_layer
        services[services]
    end
    subgraph domain_layer
        domain[domain]
    end
    subgraph schemas_layer
        schemas[schemas]
        common[schemas.common]
    end

    main --> deps
    deps --> db_session
    deps --> repos
    deps --> services
    db_session --> config
    repos --> domain
    repos --> models
    repos --> db_session
    services --> domain
    models --> db_base
    schemas --> common
```

*No circular dependencies; no `:::danger` nodes.*

---

## 5. Database schema (from ORM)

```mermaid
%% erDiagram — database schema inferred from SQLAlchemy models
erDiagram
    agents {
        uuid id PK
        string name UK
        text description
        string llm_model
        timestamp deleted_at
        timestamp created_at
        timestamp updated_at
        agent_status status
    }
    documents {
        uuid id PK
        uuid agent_id FK
        string file_name
        document_type file_type
        document_status status
        int chunks_total
        text error_message
        timestamp created_at
    }
    prompt_versions {
        uuid id PK
        uuid agent_id FK
        int version_number
        text content
        bool is_active
        timestamp created_at
    }
    use_cases {
        uuid id PK
        uuid agent_id FK
        string question
        text answer
        timestamp created_at
        timestamp updated_at
    }
    tools_catalog {
        uuid id PK
        string name UK
        string description
        string function_ref
        timestamp created_at
    }
    agent_tools {
        uuid agent_id PK,FK
        uuid tool_id PK,FK
        bool is_active
        timestamp updated_at
    }

    agents ||--o{ documents : "CASCADE"
    agents ||--o{ prompt_versions : "CASCADE"
    agents ||--o{ use_cases : "CASCADE"
    agents ||--o{ agent_tools : "CASCADE"
    tools_catalog ||--o{ agent_tools : "CASCADE"
```

---

## 6. State machines / workflow states

```mermaid
%% stateDiagram-v2 — agent status lifecycle (ORM: draft | active | inactive)
stateDiagram-v2
    [*] --> draft
    draft --> active
    draft --> inactive
    active --> inactive
```

```mermaid
%% stateDiagram-v2 — document status lifecycle (ORM: indexing | indexed | error)
stateDiagram-v2
    [*] --> indexing
    indexing --> indexed
    indexing --> error
```

*No other explicit state machines or workflow engines found in the codebase (e.g. no saga, no approval workflow).*
