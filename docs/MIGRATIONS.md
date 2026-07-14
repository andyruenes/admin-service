# Migrations (Alembic)

## How Alembic works (revisions and version control)

### What is a revision?

A **revision** is one step in your schema history. Think of it like a git commit for the database: it has a unique ID, an optional parent, and a defined change (forward and backward).

- **In code:** Each revision is a single Python file under `alembic/versions/`, e.g. `58c546e56bdc_initial.py`.
- **In the DB:** Alembic records which revision is currently applied in a table named `alembic_version` (one row: `version_num = '58c546e56bdc'`).

Revisions form a **chain**. Each revision (except the first) has a **parent** (`down_revision`). Moving “forward” runs `upgrade()`; moving “back” runs `downgrade()`.

### What a revision file looks like

Every revision file has the same shape. Here’s the one you have, trimmed:

```python
# revision identifiers
revision: str = '58c546e56bdc'           # This revision’s unique ID (like a hash)
down_revision: Union[str, None] = None  # Parent revision ID. None = first revision.
branch_labels: ... = None
depends_on: ... = None

def upgrade() -> None:
    """Apply this step: go from parent state → this state."""
    op.create_table('bot_config', ...)
    op.create_table('tools_catalog', ...)
    # ... more creates ...

def downgrade() -> None:
    """Undo this step: go from this state → parent state."""
    op.drop_table('use_cases')
    op.drop_table('prompt_versions')
    # ... reverse order of upgrade() ...
```

- `**revision**` – Unique id for this step (Alembic generates it, e.g. from a hash).
- `**down_revision**` – The id of the previous revision. `None` means “no parent” (the first migration).
- `**upgrade()**` – Runs when you move forward: applies the schema change (create table, add column, etc.). Uses Alembic’s `op.*` API (`op.create_table`, `op.add_column`, …), which emits SQL for your database.
- `**downgrade()**` – Runs when you roll back: undoes exactly what `upgrade()` did (drop table, drop column, …), usually in reverse order.

So: **one revision = one file = one forward step (`upgrade`) and one backward step (`downgrade`).**

### The revision chain (version control)

Revisions are a **linear history** (unless you use branches, which we’re not):

```
  (no DB)  →  58c546e56bdc (initial)  →  abc123 (add_foo)  →  def456 (add_bar)  →  ...
                    ↑                          ↑                     ↑
              down_revision=None         down_revision=58c...   down_revision=abc...
```

- **First revision:** `down_revision = None`.
- **Next revisions:** `down_revision = '<id of previous revision>'`.
- **Head** – The revision that has no *child* yet (the tip of the chain). `alembic upgrade head` means “run `upgrade()` for every revision from current DB state up to head.”

### What the database stores: `alembic_version`

When you run `upgrade`, Alembic:

1. Runs the revision’s `upgrade()` (so the actual SQL runs).
2. Inserts or updates a single row in a table `**alembic_version`**:
  `version_num = '58c546e56bdc'` (for that revision).

So the DB “remembers” exactly one revision id. That’s its **current version**. Next time you run `upgrade head`, Alembic compares that stored id to the chain and runs only the `upgrade()` of revisions that are *after* it.

### Commands in terms of revisions


| Command                                    | What it does                                                                                                           |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| `alembic revision --autogenerate -m "msg"` | **Creates** a new revision file (new id, `down_revision` = current head). Does **not** run it or change the DB.        |
| `alembic upgrade head`                     | For each revision from (current DB version) → head: run `upgrade()`, then write that revision id to `alembic_version`. |
| `alembic downgrade -1`                     | Run `downgrade()` of the **current** revision and set `alembic_version` to its `down_revision`.                        |
| `alembic current`                          | Print the revision id stored in `alembic_version` (current DB version).                                                |
| `alembic history`                          | List all revision ids and their `down_revision` (the chain).                                                           |


So: **revisions** are the versioned steps; **the DB** only stores one revision id; **upgrade/downgrade** move that pointer along the chain by running the corresponding functions.

---

## First time: DB just spun up

**Setup:** You have a new empty database (e.g. `docker compose up -d`), `DATABASE_URL` in `.env` pointing at it, and your models already defined in `app/models/`.

**What to do:**

1. **Generate the initial migration** (one-time, from project root):
  ```bash
   uv run alembic revision --autogenerate -m "initial"
  ```
   **What it does:** Connects to the DB, compares it (empty) to `Base.metadata` (your models), and **creates a new file** under `alembic/versions/`, e.g. `58c546e56bdc_initial.py`.
   **What that file is:** A Python script with `upgrade()` and `downgrade()`. `upgrade()` contains the ops to create all tables, enums, indexes, and constraints that match your models. `downgrade()` drops them so you can roll back.
2. **Apply the migration:**
  ```bash
   uv run alembic upgrade head
  ```
   **What it does:** Runs the `upgrade()` of every migration that hasn’t been applied yet (here, only the initial one). It **executes SQL** against the DB (CREATE TYPE, CREATE TABLE, etc.) and records the revision in the `alembic_version` table so Alembic knows the DB is at “head”.

**Result:** The database schema matches your models. You only do this once for a fresh DB (or when you introduce Alembic to an existing project and create the first revision).

---

## On any model change

**When:** You add a new model, add/remove/rename a column, change an enum, add a constraint, etc.

**What to do:**

1. **Edit your models** in `app/models/` as usual.
2. **Generate a new revision:**
  ```bash
   uv run alembic revision --autogenerate -m "add_foo_table"
  ```
   (Use a short descriptive message instead of `add_foo_table`.)
   **What it does:** Connects to the DB, compares the **current DB schema** to **current `Base.metadata`** (your code), and **creates a new file** in `alembic/versions/`, e.g. `a1b2c3d4e5f6_add_foo_table.py`. That file’s `upgrade()` contains only the **diff**: e.g. `op.create_table(...)`, `op.add_column(...)`, `op.create_enum(...)`. `downgrade()` contains the reverse (drop table, drop column, etc.).
3. **Review** the new file. Autogenerate is usually right but can miss renames or enum changes; fix by hand if needed.
4. **Apply the new revision:**
  ```bash
   uv run alembic upgrade head
  ```
   **What it does:** Runs the `upgrade()` of the new revision (and any other pending ones). It **executes the diff SQL** on the DB and updates `alembic_version` so the DB is again at “head”.

**Result:** The database schema is updated to match your updated models. Repeat this cycle for every change you want reflected in the DB.

---

## Quick reference


| Situation             | Command                                               | What it generates / does                                                           |
| --------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------------- |
| First time, empty DB  | `uv run alembic revision --autogenerate -m "initial"` | New file in `alembic/versions/` with full schema (all tables, enums, constraints). |
| First time, empty DB  | `uv run alembic upgrade head`                         | Runs that script: creates everything in the DB, sets `alembic_version`.            |
| After changing models | `uv run alembic revision --autogenerate -m "msg"`     | New file in `alembic/versions/` with only the **diff** (new/changed/removed bits). |
| After changing models | `uv run alembic upgrade head`                         | Runs the new revision(s): applies the diff to the DB, updates `alembic_version`.   |


**Useful:** `uv run alembic history` (list revisions); `uv run alembic downgrade -1` (roll back one revision).

---

## Resetting migrations (start over)

When you **delete revision files** but the database still has a row in `alembic_version` pointing at one of those revisions, Alembic will fail with **"Can't locate revision identified by '…'"**. The DB thinks it’s at a version that no longer exists in code.

Alembic does not provide a command to “forget” the current revision. You have to **clear the version table yourself**, then create a new revision and apply it.

### 1. Clear `alembic_version` in the database

Either remove the row or drop the table so the DB no longer claims any revision.

**Option A – With Docker Compose (Postgres):**

```bash
docker compose exec postgres psql -U root -d admin_service -c "DELETE FROM alembic_version;"
```

Or to drop the table (Alembic will recreate it on the next `upgrade`):

```bash
docker compose exec postgres psql -U root -d admin_service -c "DROP TABLE IF EXISTS alembic_version;"
```

**Option B – Full DB reset (truly empty DB):**  
Drop and recreate the database (e.g. `docker compose down -v`, then `docker compose up -d`). That removes all tables and types, including `alembic_version`.

**PostgreSQL:** Dropping tables with `CASCADE` does **not** drop custom ENUM types (e.g. `agent_status`, `document_type`, `document_status`). To avoid “type already exists” when re-running the initial migration, drop them too:

```bash
docker compose exec postgres psql -U root -d admin_service -c "
DROP TYPE IF EXISTS agent_status CASCADE;
DROP TYPE IF EXISTS document_type CASCADE;
DROP TYPE IF EXISTS document_status CASCADE;
"
```

(Adjust type names to match your models.)

### 2. (Optional) Drop old tables if you want a clean schema

If the DB still has tables from the old migrations (e.g. `bot_config`) and you want the new “initial” to create everything from scratch, drop those tables first. Otherwise autogenerate will produce a migration that alters/renames/drops old objects and creates new ones. For a single clean “initial” that only does `create_table`, use an empty DB (Option B above) or drop all app tables and `alembic_version`.

### 3. Create the new initial revision and apply

With no revision files (or only the new chain) and `alembic_version` empty (or table dropped):

```bash
uv run alembic upgrade head
```

The new file in `alembic/versions/` will have `down_revision = None` (first revision). The DB will then be at that revision.

**Reference:** Alembic doesn’t manage the contents of `alembic_version` for “reset” scenarios. The [cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html) describes pruning old migration files and setting `down_revision = None` on the earliest remaining file; when you delete *all* files and regenerate, you must clear `alembic_version` manually so Alembic doesn’t try to load a missing revision.