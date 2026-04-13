# Contributing

Thank you for your interest in contributing to CryptoDash. This document covers how to set up a development environment, coding conventions, testing requirements, and the pull-request process.

## Table of Contents

- [Development Setup](#development-setup)
- [Running the App Locally](#running-the-app-locally)
- [Testing](#testing)
- [Code Style](#code-style)
- [Commit Conventions](#commit-conventions)
- [Submitting Changes](#submitting-changes)
- [Project Conventions](#project-conventions)

---

## Development Setup

**Prerequisites:** Python 3.11+, Node.js 18+

```bash
git clone https://gitlab.com/lukius/cryptodash.git
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

## Testing

**Tests are non-negotiable.** Every change must keep the full suite green, and every new feature or bug fix requires accompanying tests.

### Backend

```bash
pytest tests/backend/ -v
```

- Uses `pytest-asyncio` with `asyncio_mode = auto`
- External HTTP calls must be mocked with `respx`
- Each test gets an isolated in-memory SQLite database via the `conftest.py` fixtures

### Frontend

```bash
cd frontend && npm run test
```

- Uses Vitest + `@vue/test-utils`
- Component and store tests live under `tests/frontend/`

### Linting

```bash
# Backend
ruff check backend/ tests/

# Backend (auto-fix)
ruff check --fix backend/ tests/

# Frontend
cd frontend && npm run lint
```

### Formatting

```bash
# Backend
ruff format backend/ tests/

# Frontend (check only; prettier is the formatter)
cd frontend && npm run format
```

---

## Code Style

### Python

- Line length: 88 characters (ruff default)
- Async-first: use `async def` and `await` for all I/O
- Follow the existing layered architecture: routes call services, services call repositories, repositories call the database. Do not skip layers.
- Use Pydantic schemas for all request and response bodies
- Do not introduce new runtime dependencies without discussing it first

### TypeScript / Vue

- Composition API with `<script setup>` for all components
- Props and emits must be typed
- State lives in Pinia stores; components do not perform direct API calls — use the store actions
- Tailwind utility classes for all styling; avoid inline styles

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

This project is hosted on GitLab. Use `glab` for all remote operations.

1. Fork the repository and create a feature branch:
   ```bash
   git checkout -b feat/my-feature
   ```
2. Make your changes with appropriate tests.
3. Ensure tests pass and linting is clean.
4. Push your branch and open a merge request:
   ```bash
   glab mr create
   ```
5. Describe what the MR does and why. Reference any related issues.

---

## Project Conventions

A few non-obvious decisions documented in the codebase:

- **bcrypt directly, not via passlib** — `passlib==1.7.4` is incompatible with `bcrypt>=4.x`. The project uses `bcrypt==5.0.0` directly. Do not reintroduce passlib.
- **Single asyncio event loop** — there are no threads and no multiprocessing. All concurrency is cooperative (`async`/`await`). Keep it that way.
- **Refresh lock** — `RefreshService` holds an `asyncio.Lock` to prevent concurrent refresh cycles. Do not bypass this.
- **Specs are the source of truth** — `specs/FUNC_SPEC.md` and `specs/TECH_SPEC.md` define the intended behavior. UI mockups in `specs/mockups/` are the visual reference. Read them before implementing anything non-trivial.
- **`CLAUDE.md` is for Claude Code** — keep it under 200 lines, no obvious information, no duplicated content. Update it only when project structure or key workflows change.
