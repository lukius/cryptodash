# Contributing

Thank you for your interest in contributing to CryptoDash. This document covers how to set up a development environment, coding conventions, testing requirements, and the pull-request process.

## Table of Contents

- [Development Setup](#development-setup)
- [Running the App Locally](#running-the-app-locally)
- [Getting to Know the Codebase](#getting-to-know-the-codebase)
- [Architecture Overview](#architecture-overview)
- [Testing](#testing)
- [Code Style](#code-style)
- [Database Migrations](#database-migrations)
- [Commit Conventions](#commit-conventions)
- [Submitting Changes](#submitting-changes)
- [AI-Assisted Development](#ai-assisted-development)
- [Project Conventions](#project-conventions)

---

## Development Setup

**Prerequisites:** Python 3.11+, Node.js 18+

```bash
git clone https://github.com/lukius/cryptodash.git
cd cryptodash

# Python — create virtualenv and install dev deps
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Frontend
cd frontend
npm install
cd ..
```

---

## Running the App Locally

### Option A — production-like (built frontend served by FastAPI)

```bash
cd frontend && npm run build && cd ..
python run.py
# open http://localhost:8000
```

### Option B — dev mode (hot-reload on both sides)

```bash
# Terminal 1
python run.py

# Terminal 2
cd frontend && npm run dev
# open http://localhost:5173
```

The Vite dev server proxies `/api` requests to the FastAPI backend at port 8000.

---

## Getting to Know the Codebase

Before touching anything non-trivial, spend a few minutes with these files:

| File / Directory | What it tells you |
|---|---|
| `specs/FUNC_SPEC.md` | What the system does — features, user flows, data requirements |
| `specs/TECH_SPEC.md` | How it is built — architecture, component specs, data models |
| `specs/mockups/` | Interactive HTML mockups — the visual source of truth for the UI |
| `CLAUDE.md` | Build commands, key design decisions, known gotchas |

The specs are the authoritative source of truth. If code and spec disagree, treat it as a bug.

---

## Architecture Overview

CryptoDash is a single-page app backed by an async Python API. The layers are strictly separated:

```
Frontend (Vue 3 SPA)
    │  HTTP / WebSocket
    ▼
Routers  (backend/routers/)   ← request/response, auth guards
    │
Services (backend/services/)  ← business logic, orchestration
    │
Repositories (backend/repositories/)  ← database queries only
    │
SQLite (WAL mode, aiosqlite)

External API clients (backend/clients/) ← Mempool.space, Blockbook, Kaspa, CoinGecko
Background scheduler (backend/core/scheduler.py)
WebSocket manager   (backend/core/websocket_manager.py)
```

Rules:
- Routes call services. Services call repositories and clients. Nothing else crosses a layer boundary.
- All I/O is `async`/`await`. There are no threads and no blocking calls.
- Pydantic schemas (`backend/schemas/`) are used for all request and response bodies.
- State lives in Pinia stores on the frontend; components do not make API calls directly.

---

## Testing

**Tests are non-negotiable.** Every change must keep the full suite green, and every new feature or bug fix requires accompanying tests.

### Backend

```bash
pytest tests/backend/ -v
```

- Uses `pytest-asyncio` with `asyncio_mode = auto`
- External HTTP calls must be mocked with `respx`
- Each test gets an isolated in-memory SQLite database via `conftest.py` fixtures
- Test files live under `tests/backend/` and mirror the `backend/` package structure

### Frontend

```bash
cd frontend && npm run test
```

- Uses Vitest + `@vue/test-utils`
- Component and store tests live under `tests/frontend/`

### Linting and formatting

```bash
# Backend
ruff check backend/ tests/          # lint
ruff check --fix backend/ tests/    # lint + auto-fix
ruff format backend/ tests/         # format

# Frontend
cd frontend && npm run lint          # ESLint
cd frontend && npm run format        # Prettier check
```

---

## Code Style

### Python

- Line length: 88 characters (ruff default)
- Async-first: use `async def` and `await` for all I/O
- Follow the layered architecture described above — do not skip layers
- Use Pydantic schemas for all request and response bodies
- Do not introduce new runtime dependencies without discussing it first

### TypeScript / Vue

- Composition API with `<script setup>` for all components
- Props and emits must be typed
- State lives in Pinia stores; components do not perform direct API calls — use store actions
- Tailwind utility classes for all styling; avoid inline styles

---

## Database Migrations

The project uses Alembic for schema migrations. Migration files live in `backend/migrations/versions/`.

When you change a SQLAlchemy model, create a new migration:

```bash
# Auto-generate from model diff
alembic revision --autogenerate -m "short description"

# Apply pending migrations
alembic upgrade head

# Check current revision
alembic current
```

Rules:
- Never edit existing migration files — always add a new revision
- Test that migrations apply cleanly on a fresh database before opening a PR
- The app applies migrations automatically on startup via `alembic upgrade head`

---

## Commit Conventions

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short description>
```

Types:

| Type | When to use |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change that is neither a fix nor a feature |
| `test` | Adding or updating tests |
| `docs` | Documentation only |
| `chore` | Build, tooling, dependencies |

Rules:
- One-liner messages only (no multi-paragraph body)
- Present tense, imperative mood: "add wallet validation" not "added" or "adds"
- No co-author lines or AI attribution in commit messages

---

## Submitting Changes

This project is hosted on GitHub. Use `gh` for all remote operations.

1. Fork the repository and create a feature branch:
   ```bash
   git checkout -b feat/my-feature
   ```
2. Make your changes with appropriate tests.
3. Ensure the full test suite passes and linting is clean.
4. Push your branch and open a pull request:
   ```bash
   gh pr create
   ```
5. Describe what the PR does and why in the PR description. Reference any related issues.

A maintainer will review and merge. Please keep PRs focused — one logical change per PR.

---

## AI-Assisted Development

The project is primarily developed with Claude Code, though any AI assistant can use `CLAUDE.md` and the specs in `specs/` to get context. Human contributors do not need to use any AI tooling — all conventions apply equally.

### CLAUDE.md

`CLAUDE.md` is the AI context file for this project. Keep it useful:

- **Under 200 lines.** If it grows past that, something belongs elsewhere or can be cut.
- **Only non-obvious information.** Things that a reader *cannot* derive by reading the source: the *why* behind decisions, implicit conventions, trust boundaries, known traps, and anything that would otherwise live only in someone's head. If the code, tests, or commit history already describe it, it does not belong here.
- Update it when project structure, build commands, or key workflows change. Do not add routine implementation details.

### Spec-driven development (SDD)

For larger features, this project encourages a spec-driven approach: write a functional spec first, then a technical spec, then implement. The `specs/` directory is the output of this process and is the source of truth for intended behavior. Smaller features and bug fixes can be implemented directly, as long as they follow the project conventions documented here.

### Claude Code agent workflow

If you use Claude Code, the project includes a pre-configured setup that supports SDD end-to-end:

- **Agent team** — `.claude/agents/` defines four specialised agents (project manager, developer, tech lead, QA analyst) that collaborate on larger tasks
- **Custom skills** — invoke from the Claude Code prompt:

  | Skill | What it does |
  |---|---|
  | `/generate-func-spec` | Produce a functional spec from a feature brief |
  | `/generate-tech-spec` | Produce a technical spec from a functional spec |
  | `/develop-feature <description>` | Full agent-team flow: plan → TDD → review → QA |

- **Specs and mockups are the source of truth** — agents read `specs/` before implementing anything; point Claude at `specs/mockups/*.html` to compare against the visual reference

---

## Project Conventions

A few non-obvious decisions documented in the codebase:

- **bcrypt directly, not via passlib** — `passlib==1.7.4` is incompatible with `bcrypt>=4.x`. The project uses `bcrypt==5.0.0` directly. Do not reintroduce passlib.
- **HD wallets use Trezor Blockbook, individual addresses use Mempool.space** — Blockbook accepts xpub/ypub/zpub natively and returns the full wallet balance + per-address breakdown in one call. Mempool.space does not support extended public keys. The `User-Agent: CryptoDash/1.0` header is required on Blockbook requests — generic UAs are blocked.
- **Single asyncio event loop** — there are no threads and no multiprocessing. All concurrency is cooperative (`async`/`await`). Keep it that way.
- **Refresh lock** — `RefreshService` holds an `asyncio.Lock` to prevent concurrent refresh cycles. Do not bypass this.
- **Specs are the source of truth** — `specs/FUNC_SPEC.md` and `specs/TECH_SPEC.md` define the intended behavior. UI mockups in `specs/mockups/` are the visual reference. Read them before implementing anything non-trivial.
- **`CLAUDE.md` is for Claude Code** — keep it under 200 lines, no obvious information, no duplicated content. Update it only when project structure or key workflows change.
