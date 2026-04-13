# CryptoDash

A self-hosted personal cryptocurrency portfolio dashboard. Track wallet balances and portfolio value across Bitcoin and Kaspa networks — no account registration, no private keys, no external service required to run.

## Features

- **Multi-wallet tracking** — add any number of Bitcoin and Kaspa addresses; balances are fetched from public blockchain APIs
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

External data sources: [Mempool.space](https://mempool.space) (Bitcoin), [api.kaspa.org](https://api.kaspa.org) (Kaspa), [CoinGecko](https://www.coingecko.com) (prices).

## Quick Start

**Prerequisites:** Python 3.11+, Node.js 18+

```bash
# 1. Clone
git clone https://gitlab.com/lukius/cryptodash.git
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

### Reset password

```bash
python run.py reset-password
```

## Project Structure

```
cryptodash/
├── backend/
│   ├── app.py              # FastAPI app factory + lifespan
│   ├── config.py           # Environment-variable configuration
│   ├── clients/            # External API clients (Bitcoin, Kaspa, CoinGecko)
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
├── migrations/             # Alembic database migrations
├── specs/                  # Functional spec, tech spec, UI mockups
└── tests/                  # pytest (backend) + Vitest (frontend) test suites
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
| GET | `/api/dashboard/summary` | Portfolio totals |
| GET | `/api/dashboard/portfolio-history` | Historical portfolio value |
| GET | `/api/dashboard/price-history` | BTC/USD and KAS/USD price history |
| GET | `/api/dashboard/wallet/{id}/history` | Per-wallet balance history |
| GET | `/api/dashboard/wallet/{id}/transactions` | Transaction timeline |
| GET/PUT | `/api/settings` | Read / update settings |
| WS | `/api/ws` | Real-time refresh events |

## Running Tests

```bash
# Backend (requires dev deps)
pip install -r requirements-dev.txt
pytest tests/backend/ -v

# Frontend
cd frontend && npm run test
```

## License

[MIT](LICENSE)
