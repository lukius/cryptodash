# T01: Backend Project Scaffolding

**Status**: todo
**Layer**: backend
**Assignee**: developer
**Depends on**: none

## Context

The repository has only a frontend skeleton and `requirements.txt`. There is no backend package, no
test suite, no Alembic configuration, and no entry point. This task creates the skeletal structure
that all subsequent backend tasks build upon — nothing else can be written until the package layout,
database engine, config, and test fixtures exist.

> "Layered architecture with clear separation of concerns ... Backend: Python 3.11+, FastAPI,
> SQLAlchemy async, aiosqlite, Alembic ..."
> — specs/TECH_SPEC.md, Section 3 (Project Structure) and Section 1.2

## Files owned

- `backend/__init__.py` (create)
- `backend/config.py` (create)
- `backend/database.py` (create)
- `backend/models/__init__.py` (create)
- `backend/schemas/__init__.py` (create)
- `backend/routers/__init__.py` (create)
- `backend/services/__init__.py` (create)
- `backend/clients/__init__.py` (create)
- `backend/repositories/__init__.py` (create)
- `backend/core/__init__.py` (create)
- `backend/migrations/__init__.py` (create — empty, marks as package)
- `alembic.ini` (create)
- `backend/migrations/env.py` (create)
- `backend/migrations/script.py.mako` (create)
- `requirements-dev.txt` (create)
- `run.py` (create — stub, wired in T10)
- `tests/__init__.py` (create)
- `tests/backend/__init__.py` (create)
- `tests/backend/conftest.py` (create)
- `CLAUDE.md` (modify — update Build/Run/Test/Lint commands)

## Subtasks

- [ ] ST1: Create `backend/` package with all `__init__.py` stubs.
- [ ] ST2: Implement `backend/config.py` — `AppConfig` dataclass reading from env vars with defaults
      (CRYPTODASH_DB_PATH, CRYPTODASH_HOST, CRYPTODASH_PORT, CRYPTODASH_LOG_LEVEL).
- [ ] ST3: Implement `backend/database.py` — async SQLAlchemy engine, `async_session` factory, `Base`
      declarative base, `init_db()` coroutine (WAL mode + foreign keys + `create_all`).
- [ ] ST4: Create `alembic.ini` and `backend/migrations/env.py` / `script.py.mako` configured for
      async SQLite.
- [ ] ST5: Create `requirements-dev.txt` with: pytest, pytest-asyncio, httpx, ruff, vitest (note: vitest
      lives in frontend package.json — requirements-dev.txt is backend-only).
- [ ] ST6: Create `tests/backend/conftest.py` with: in-memory async SQLite engine fixture, async test
      client fixture (using FastAPI `TestClient`/`AsyncClient`), and helper to create a test user +
      session.
- [ ] ST7: Create `run.py` stub (Python version check, data dir creation, uvicorn launch, reset-password
      dispatch — per spec Section 6.2).
- [ ] ST8: Update `CLAUDE.md` Build/Run/Test/Lint sections with actual commands.
- [ ] ST9: Write a smoke test (`tests/backend/test_database.py`) that verifies `init_db()` creates all
      tables on an in-memory engine.

## Acceptance criteria

- [ ] `python -c "from backend.config import config; print(config.db_path)"` prints the default path.
- [ ] `python -c "import asyncio; from backend.database import init_db; asyncio.run(init_db())"` runs
      without error on a fresh environment (no pre-existing DB file).
- [ ] `pytest tests/backend/test_database.py -v` passes.
- [ ] `alembic current` runs without error from the project root.
- [ ] `ruff check backend/` exits 0 with no errors.

## Notes

- The `init_db()` function uses `Base.metadata.create_all` for development simplicity. Alembic
  migrations will layer on top for schema evolution. Both coexist per spec Section 5.2.
- `requirements-dev.txt` should pin versions matching TECH_SPEC.md Section 1.5:
  `pytest==8.3.4`, `pytest-asyncio==0.24.0`.
- The `conftest.py` must use an in-memory SQLite URL (`sqlite+aiosqlite:///:memory:`) to keep
  tests isolated and fast. Each test gets a fresh engine.
