# CryptoDash

## Project Structure

```
cryptodash/
├── .claude/
│   ├── agents/            # Agent team definitions (PM, developer, tech lead, QA)
│   └── skills/            # Claude Code skills (invoke with /skill-name)
│       ├── develop-feature/       # /develop-feature — agent team: plan → TDD → review → QA
│       ├── generate-func-spec/   # /generate-func-spec — functional spec from a brief
│       └── generate-tech-spec/   # /generate-tech-spec — tech spec from a func spec
├── specs/                 # All design artifacts (specs + mockups)
│   ├── FUNC_SPEC.md       # What the system does
│   ├── TECH_SPEC.md       # How to build it
│   ├── TECH_NOTES.md      # Research notes and decision points
│   └── mockups/           # Interactive HTML mockups (visual source of truth for UI)
├── backend/               # Python 3.11+ / FastAPI backend
│   ├── app.py             # FastAPI app factory (create_app), lifespan, exception handlers
│   ├── routers/           # HTTP + WebSocket handlers (auth, wallets, dashboard, settings, ws)
│   ├── services/          # Business logic (auth, wallet, history, refresh)
│   ├── repositories/      # SQLAlchemy async DB access
│   ├── clients/           # External API clients (Bitcoin, Kaspa, CoinGecko, Blockbook/xpub)
│   ├── models/            # SQLAlchemy ORM models
│   ├── schemas/           # Pydantic request/response models
│   └── core/              # Cross-cutting: scheduler, WebSocket manager, dependencies, exceptions
├── tests/backend/         # pytest test suite (asyncio_mode=auto)
├── run.py                 # Entry point: `python run.py`
├── alembic.ini            # Alembic migrations config
├── requirements.txt       # Production Python deps
└── requirements-dev.txt   # Test + lint deps (includes requirements.txt)
```

Read `specs/` for detailed functional and technical specs before implementing features. UI mockups in `specs/mockups/` are the visual source of truth — open them in a browser to see the target look-and-feel.

## Build & Run

- Install deps: `pip install -r requirements-dev.txt` (uses `.venv` — activate first: `source .venv/bin/activate`)
- Run: `python run.py`
- Reset password: `python run.py reset-password`
- Test (backend): `pytest tests/backend/ -v`
- Lint (backend): `ruff check backend/ tests/`
- Format (backend): `ruff format backend/ tests/`
- Build (frontend): `cd frontend && npm run build`
- Test (frontend): `cd frontend && npm run test`
- Lint (frontend): `cd frontend && npm run lint`
- Dev server (frontend): `cd frontend && npm run dev`

## Git & Remote

- **Hosted on GitLab** (private): `gitlab.com:lukius/cryptodash`
- Use `glab` (not `gh`) for all remote operations: MRs, issues, CI, etc.
- Example: `glab mr create`, `glab issue list`, `glab ci status`

## Development Rules

### Testing — non-negotiable
- **Always run the full test suite after making changes.** Do not accept code that makes tests fail.
- Add new unit and/or functional tests for every new feature or bug fix.

### Commits
- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
- One-liner messages, no co-author info.

### After touching code
- Run tests.
- Update this CLAUDE.md if the change affects project structure, build commands, key dependencies, or development workflows.

### About this file
- **Keep it under 200 lines.** If it's growing past that, something belongs elsewhere or can be removed.
- **Only non-obvious information.** If the code, tests, or commit history already describe it, it should not be here. This file is for context that a reader *cannot* derive by reading the source: the *why* behind decisions, implicit conventions, trust boundaries, known traps, and anything that would otherwise live only in someone's head.

## Key Design Decisions

- **bcrypt directly, not via passlib** — `passlib==1.7.4` is incompatible with `bcrypt>=4.x`: passlib's internal wrap-bug detection hashes a 200-byte string, but newer bcrypt rejects passwords over 72 bytes. `requirements.txt` uses `bcrypt==5.0.0` directly. The spec's "bcrypt via passlib" recommendation cannot be followed; the `bcrypt` library directly produces equivalent `$2b$12$...` hashes.
- **HD wallets use Trezor Blockbook (`btc2.trezor.io`), individual BTC wallets use mempool.space** — Blockbook accepts xpub/ypub/zpub natively and returns balance + per-address breakdown + tx history for the entire wallet in one call, eliminating the rate-limit pressure that broke the per-address mempool.space approach. The spec's original blockchain.info choice does not work for BIP84 zpubs (it derives only legacy P2PKH addresses from an xpub). The User-Agent `CryptoDash/1.0` (set in `BaseClient`) is required — generic UAs like `Mozilla/5.0` are blocked by Cloudflare on Blockbook xpub paths.

