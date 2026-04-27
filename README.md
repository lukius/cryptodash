<p align="center">
  <img src="frontend/public/favicon.svg" width="80" alt="CryptoDash">
</p>

# CryptoDash

A self-hosted personal cryptocurrency portfolio dashboard. Track wallet balances and portfolio value across Bitcoin and Kaspa — no account registration, no private keys, no third-party cloud required.

## Features

- **Multi-wallet tracking** — add any number of Bitcoin and Kaspa addresses; balances are fetched from public blockchain APIs
- **HD wallet support** — add an extended public key (xpub / ypub / zpub) to track an entire hierarchical-deterministic wallet with per-address breakdown
- **Portfolio dashboard** — total USD value, per-currency balances, composition pie chart, and historical value chart
- **Price history** — BTC/USD and KAS/USD charts sourced from CoinGecko
- **Wallet detail view** — per-wallet balance history and full transaction timeline
- **Background refresh** — configurable auto-refresh interval (default 5 min); manual refresh on demand
- **Real-time updates** — WebSocket push notifications when a refresh cycle completes
- **Single-user mode** — first-run account setup with bcrypt-hashed password; no registration flow
- **Portable storage** — single SQLite file; no external database

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy (async), Alembic, httpx |
| Frontend | TypeScript, Vue 3, Pinia, Vue Router, Chart.js, Tailwind CSS |
| Database | SQLite (WAL mode) via aiosqlite |
| Build / dev | Vite, Vitest, pytest, ruff |

External data sources: [Mempool.space](https://mempool.space) (Bitcoin individual addresses), [Trezor Blockbook](https://trezor.io) (HD wallets / xpub), [api.kaspa.org](https://api.kaspa.org) (Kaspa), [CoinGecko](https://www.coingecko.com) (prices).

## Quick Start (Docker)

The fastest way to run CryptoDash. Requires Docker.

```bash
docker run -d \
  --name cryptodash \
  -p 8000:8000 \
  -v cryptodash-data:/app/data \
  ghcr.io/lukius/cryptodash:latest
```

Or with Docker Compose:

```bash
curl -O https://raw.githubusercontent.com/lukius/cryptodash/master/docker-compose.yml
docker compose up -d
```

Open [http://localhost:8000](http://localhost:8000) in your browser. On first run you will be prompted to create a username and password. Your data lives in the `cryptodash-data` named volume — your wallet list and history persist across container restarts and image upgrades.

Images are published for `linux/amd64` and `linux/arm64` (e.g. Raspberry Pi 4/5).

## Quick Start (from source)

**Prerequisites:** Python 3.11+, Node.js 18+

```bash
# 1. Clone
git clone https://github.com/lukius/cryptodash.git
cd cryptodash

# 2. Backend — create and activate a virtualenv, then install deps
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Frontend — build the production bundle
cd frontend
npm install
npm run build
cd ..

# 4. Run
python run.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser. On first run you will be prompted to create a username and password.

### Development mode

Run the backend and frontend dev server concurrently for hot-reload:

```bash
# Terminal 1 — backend
source .venv/bin/activate
python run.py

# Terminal 2 — frontend dev server (proxies /api to backend)
cd frontend
npm run dev
```

Frontend dev server listens on [http://localhost:5173](http://localhost:5173).

## Configuration

All settings are optional environment variables with sensible defaults:

| Variable | Default | Description |
|---|---|---|
| `CRYPTODASH_DB_PATH` | `data/cryptodash.db` | Path to the SQLite database file |
| `CRYPTODASH_HOST` | `0.0.0.0` | Bind address |
| `CRYPTODASH_PORT` | `8000` | HTTP port |
| `CRYPTODASH_LOG_LEVEL` | `info` | Uvicorn log level (`debug`, `info`, `warning`, `error`) |

The refresh interval is configured inside the app via the Settings page and persisted in the database.

When running under Docker, pass these via `-e VAR=value` (or in the `environment:` block of `docker-compose.yml`). The default `CRYPTODASH_DB_PATH` inside the container is `/app/data/cryptodash.db` so the database lives in the mounted volume.

### Reset password

From source:

```bash
python run.py reset-password
```

In Docker:

```bash
docker exec -it cryptodash python run.py reset-password
```

## Project Structure

```
cryptodash/
├── backend/
│   ├── app.py              # FastAPI app factory + lifespan
│   ├── config.py           # Environment-variable configuration
│   ├── clients/            # External API clients (Bitcoin, Kaspa, CoinGecko, Blockbook)
│   ├── core/               # Scheduler, WebSocket manager, security, DI
│   ├── models/             # SQLAlchemy ORM models
│   ├── repositories/       # Database access layer
│   ├── routers/            # HTTP + WebSocket route handlers
│   ├── schemas/            # Pydantic request/response types
│   └── services/           # Business logic (auth, wallet, refresh, history, price)
├── frontend/src/
│   ├── components/         # Reusable Vue components (widgets, wallet, layout, common)
│   ├── composables/        # useApi, useWebSocket
│   ├── router/             # Vue Router routes + auth guards
│   ├── stores/             # Pinia state stores (auth, dashboard, wallets, settings)
│   ├── types/              # TypeScript interfaces
│   ├── utils/              # Formatting and address validation helpers
│   └── views/              # Page-level components
├── backend/migrations/     # Alembic database migrations
├── specs/                  # Functional spec, tech spec, UI mockups (source of truth)
├── tests/                  # pytest (backend) + Vitest (frontend) test suites
└── .claude/                # Claude Code agent team and custom skills
```

## API Overview

The REST API is available under `/api`. An interactive OpenAPI interface is served at `/docs` when the backend is running.

| Method | Path | Description |
|---|---|---|
| GET | `/api/auth/status` | Auth status and account existence |
| POST | `/api/auth/setup` | First-run account creation |
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/wallets/` | List wallets with latest balances |
| POST | `/api/wallets/` | Add wallet |
| PATCH | `/api/wallets/{id}` | Update wallet tag |
| DELETE | `/api/wallets/{id}` | Remove wallet |
| GET | `/api/wallets/{id}/transactions` | Transaction timeline for a wallet |
| POST | `/api/wallets/{id}/retry-history` | Retry failed history import |
| GET | `/api/dashboard/summary` | Portfolio totals |
| GET | `/api/dashboard/portfolio-history` | Historical portfolio value |
| GET | `/api/dashboard/wallet-history/{id}` | Per-wallet balance history |
| GET | `/api/dashboard/price-history` | BTC/USD and KAS/USD price history |
| GET | `/api/dashboard/composition` | Portfolio composition breakdown |
| POST | `/api/dashboard/refresh` | Trigger a manual refresh |
| GET/PUT | `/api/settings/` | Read / update settings |
| WS | `/api/ws` | Real-time refresh events |

## Running Tests

```bash
# Backend (requires dev deps)
pip install -r requirements-dev.txt
pytest tests/backend/ -v

# Backend lint + format check
ruff check backend/ tests/
ruff format --check backend/ tests/

# Frontend
cd frontend && npm run test
cd frontend && npm run lint
```

## AI-Assisted Development

CryptoDash is primarily developed with [Claude Code](https://claude.ai/code), though `CLAUDE.md` and the specs in `specs/` make the project approachable by any AI assistant.

- **`CLAUDE.md`** — project context file: build commands, key design decisions, known gotchas. Any AI assistant can read this to get up to speed quickly.
- **`.claude/agents/`** — a Claude Code agent team (project manager, developer, tech lead, QA analyst) for coordinated multi-step work
- **`.claude/skills/`** — Claude Code custom workflows:
  - `/develop-feature` — full agent-team flow: plan → TDD → code review → QA
  - `/generate-func-spec` — generate a functional spec from a brief
  - `/generate-tech-spec` — generate a technical spec from a functional spec

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on maintaining `CLAUDE.md` and using the agent workflow.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding conventions, testing requirements, and the pull-request process.

## License

[MIT](LICENSE)
