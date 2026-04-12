# CryptoDash — Technical Specification

**Version:** 1.0
**Date:** 2026-04-12
**Status:** Draft
**Source:** `specs/FUNC_SPEC.md` v1.0

### UI Mockups

Interactive HTML mockups are in `specs/mockups/`. Open in a browser — no build step needed.

| File | Screen | Key elements |
|------|--------|-------------|
| `01-login.html` | Login / First-run setup | Auth forms, password strength meter, error states |
| `02-dashboard.html` | Main dashboard | All 8 widgets (W1–W8), Chart.js charts, wallet table, add-wallet modal |
| `03-wallet-detail.html` | Per-wallet detail | Balance-over-time chart, transaction timeline, delete confirmation |

These are the **visual source of truth** for the frontend implementation. Design tokens (colors, fonts, spacing) are defined as CSS custom properties in each file.

---

## 1. Technology Stack

### 1.1 Language and Versions

| Component | Language | Version | Justification |
|-----------|----------|---------|---------------|
| Backend | Python | 3.11+ | Significant performance gains over 3.10, `asyncio.TaskGroup`, `tomllib` in stdlib, broad OS availability. |
| Frontend | TypeScript | 5.5+ | Type safety across the SPA; Vue 3 tooling is TypeScript-first. |
| Database | SQLite | 3.35+ (bundled with Python) | WAL mode, `RETURNING` clause, `STRICT` tables. |

### 1.2 Backend Frameworks and Libraries

| Package | Version | Purpose | Why chosen |
|---------|---------|---------|------------|
| `fastapi` | `==0.115.6` | Web framework (HTTP + WebSocket) | Async-native, automatic OpenAPI docs, Pydantic integration, built-in WebSocket support. |
| `uvicorn[standard]` | `==0.34.0` | ASGI server | Reference server for FastAPI; `standard` extra includes `uvloop` and `httptools` for performance. |
| `sqlalchemy[asyncio]` | `==2.0.36` | ORM / query builder | Async support via `aiosqlite`; type-safe queries; mature migration ecosystem (Alembic). |
| `aiosqlite` | `==0.20.0` | Async SQLite driver | Required by SQLAlchemy async engine for SQLite. |
| `alembic` | `==1.14.1` | Database migrations | Schema versioning; needed for future schema changes. |
| `httpx` | `==0.28.1` | Async HTTP client | Modern, async-native, connection pooling, timeout control. Replaces `requests`+`aiohttp`. |
| `passlib[bcrypt]` | `==1.7.4` | Password hashing | bcrypt with embedded salt. Well-audited. `bcrypt` extra installs the C-extension backend. |
| `pydantic` | `==2.10.4` | Data validation / serialization | Transitive via FastAPI. Used for all request/response schemas. |
| `python-multipart` | `==0.0.18` | Form parsing | Required by FastAPI for form-data endpoints (login form). |

**No additional dependencies.** The scheduler is implemented with `asyncio` tasks (no APScheduler). Token generation uses `secrets` from the stdlib.

### 1.3 Frontend Frameworks and Libraries

| Package | Version | Purpose | Why chosen |
|---------|---------|---------|------------|
| `vue` | `^3.5.0` | UI framework | Fine-grained reactivity ideal for independent dashboard widgets; Composition API; lighter than React (~33 KB gzip). |
| `vue-router` | `^4.4.0` | Client-side routing | Official Vue router; supports navigation guards for auth. |
| `pinia` | `^2.2.0` | State management | Official Vue store; simple API, TypeScript-first, devtools support. |
| `chart.js` | `^4.4.0` | Chart rendering | Covers all needed chart types (line, pie); ~60 KB gzip; canvas-based for performance. |
| `vue-chartjs` | `^5.3.0` | Vue ↔ Chart.js bridge | Reactive Chart.js components for Vue 3. |
| `chartjs-adapter-date-fns` | `^3.0.0` | Time axis adapter | Required by Chart.js for time-scale X axes. |
| `date-fns` | `^4.1.0` | Date utilities | Tree-shakeable, no mutable globals (unlike Moment/Day.js). Needed by the Chart.js adapter. |
| `tailwindcss` | `^3.4.0` | Utility-first CSS | Full responsive design control without a heavy component library; small production builds via purging. |

**Dev dependencies:**

| Package | Version | Purpose |
|---------|---------|---------|
| `vite` | `^6.0.0` | Build tool / dev server |
| `@vitejs/plugin-vue` | `^5.2.0` | Vue SFC compilation |
| `typescript` | `^5.5.0` | Type checking |
| `vue-tsc` | `^2.1.0` | Vue template type checking |
| `autoprefixer` | `^10.4.0` | CSS vendor prefixing (Tailwind peer dep) |
| `postcss` | `^8.4.0` | CSS processing (Tailwind peer dep) |
| `eslint` | `^9.0.0` | Linting |
| `eslint-plugin-vue` | `^9.30.0` | Vue-specific lint rules |
| `prettier` | `^3.4.0` | Code formatting |

### 1.4 Frontend Framework Evaluation

| Criterion | Vue 3 | React 19 | Svelte 5 |
|-----------|-------|----------|----------|
| Bundle size (gzip) | ~33 KB | ~42 KB | ~2 KB (compiled) |
| Reactivity model | Built-in, fine-grained | Manual (`useState`, etc.) | Built-in (runes — new in v5) |
| Chart ecosystem | vue-chartjs, vue-echarts | react-chartjs-2, recharts | svelte-chartjs (smaller community) |
| State management | Pinia (official, mature) | Context/Zustand/Redux | Built-in stores |
| TypeScript DX | Excellent (SFC + Volar) | Excellent | Good (v5 improved) |
| Maturity | Very mature | Very mature | Runes API is new (v5, late 2024) |

**Decision: Vue 3.** Fine-grained reactivity is a natural fit for dashboard widgets that update independently. The ecosystem is mature, the bundle is lighter than React, and Svelte 5's runes API is too new for a project that values stability. TypeScript support via Volar is first-class.

### 1.5 Build System and Toolchain

| Concern | Tool | Notes |
|---------|------|-------|
| Backend dependency management | `pip` + `requirements.txt` | Simple, no Poetry/PDM overhead for a single-app project. A `requirements-dev.txt` for test/lint deps. |
| Frontend build | Vite 6 | Dev server with HMR, production build with tree-shaking and minification. |
| Frontend package manager | `npm` | Bundled with Node.js. Lockfile via `package-lock.json`. |
| Linting (backend) | `ruff` `==0.8.4` | Fast Python linter + formatter. Replaces flake8/black/isort. |
| Linting (frontend) | ESLint + Prettier | Standard Vue 3 config. |
| Testing (backend) | `pytest` `==8.3.4` + `pytest-asyncio` `==0.24.0` + `httpx` (for `TestClient`) | Async test support; FastAPI's `TestClient` uses httpx under the hood. |
| Testing (frontend) | `vitest` `^2.1.0` + `@vue/test-utils` `^2.4.0` | Vite-native test runner; fast, compatible with Vue component testing. |

---

## 2. Architecture Overview

### 2.1 Architectural Pattern

**Layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────┐
│                   Vue 3 SPA (Browser)               │
│  ���─────────┐ ┌──────────┐ ┌───────────┐ ┌────────┐ │
│  │  Views  │ │  Stores  │ │ Composables│ │ Router │ │
│  └────���────┘ └──────────┘ └���──────────┘ └────────┘ │
└────────────────┬──────────────────┬─────────────────┘
                 │ REST (JSON)      │ WebSocket
┌────────────────▼──────────────────▼──────────────��──┐
│                FastAPI Application                   │
│  ┌────────────────────────────────────────────────┐  │
│  │           API Layer (Routers)                  │  │
│  ��   auth · wallets · dashboard · settings · ws   │  │
│  └──────────────────┬─────────────────────────────┘  │
│  ┌──────────────────▼─────────���───────────────────┐  │
│  │           Service Layer                        │  │
│  │   auth · wallet · refresh · history · price    │  │
│  └───���──────────────┬────────��────────────────────┘  │
│  ┌──────────────────▼──────────┐ ┌────────────────┐  │
│  │   Repository Layer (DAL)    │ │ External Clients│  │
│  │   SQLAlchemy async + SQLite │ │ Bitcoin · Kaspa │  │
│  │                             │ │ CoinGecko       │  │
│  └───────��─────────────────────┘ └────────────────┘  │
│  ┌────────────────────────────────────────────────┐  │
│  │           Infrastructure                       │  │
│  │   Scheduler · WebSocket Manager · Config       │  │
│  └───────────────���────────────────────────────────┘  │
└──��───────────────────────────────────────────────────┘
                         │
                         ▼
                  ┌─────────────┐
                  │   SQLite DB │
                  │  (WAL mode) │
                  └─────────────┘
```

**Justification:** A layered architecture keeps the codebase navigable for a single developer while enforcing separation. Each layer depends only on the layer below it. The external API clients are isolated behind an interface so providers can be swapped (per Assumption A2/A3).

### 2.2 Component Responsibility Table

| Component | Layer | Responsibility |
|-----------|-------|----------------|
| **Auth Router** | API | HTTP endpoints for setup, login, logout, session status. |
| **Wallet Router** | API | CRUD endpoints for wallets (add, list, edit tag, remove). |
| **Dashboard Router** | API | Read-only endpoints for portfolio summary, history, and price charts. |
| **Settings Router** | API | Read/write endpoints for configuration (refresh interval). |
| **WebSocket Manager** | API/Infra | Manages active WebSocket connections; authenticates via token; broadcasts events. |
| **Auth Service** | Service | Account creation, credential validation, session lifecycle, password reset. |
| **Wallet Service** | Service | Wallet CRUD logic, address validation, duplicate detection, tag uniqueness. |
| **Refresh Service** | Service | Orchestrates a full refresh cycle: fetch balances + prices for all wallets, store snapshots. |
| **History Service** | Service | Full transaction history import and incremental sync for a single wallet. |
| **Price Service** | Service | Current and historical price fetching and caching logic. |
| **Bitcoin Client** | External | Communicates with Mempool.space API for BTC balance and transactions. |
| **Kaspa Client** | External | Communicates with api.kaspa.org for KAS balance and transactions. |
| **CoinGecko Client** | External | Fetches current and historical BTC/USD and KAS/USD prices. |
| **Scheduler** | Infrastructure | Runs periodic refresh cycles using `asyncio` tasks; restartable. |
| **Database / Repositories** | Repository | All SQL queries: wallet repo, snapshot repo, transaction repo, session repo, config repo. |

### 2.3 Threading / Concurrency Model

The entire backend runs on a **single asyncio event loop** managed by `uvicorn`.

| Concern | Mechanism |
|---------|-----------|
| HTTP request handling | FastAPI async route handlers on the event loop. |
| WebSocket connections | FastAPI WebSocket handlers; each connection is an async task. |
| External API calls | `httpx.AsyncClient` — non-blocking I/O on the event loop. |
| Database queries | `aiosqlite` via SQLAlchemy async — non-blocking I/O. SQLite itself serializes writes (WAL mode allows concurrent reads). |
| Background scheduler | `asyncio.Task` created at startup; sleeps for the configured interval, then runs the refresh coroutine. |
| History imports | Separate `asyncio.Task` per wallet import; runs concurrently with the scheduler and with other imports. |
| Refresh lock | `asyncio.Lock` shared between manual refresh, scheduled refresh, and (for snapshot writes) history imports. Prevents concurrent refresh cycles (FR-047). History imports are **not** blocked by the refresh lock — they run independently (per user decision). |

**No threads, no multiprocessing.** All concurrency is cooperative async/await. This avoids thread-safety issues with SQLite.

---

## 3. Project Structure

```
cryptodash/
├── run.py                          # Standalone entry point (shebang: #!/usr/bin/env python3)
├── requirements.txt                # Production Python dependencies
├── requirements-dev.txt            # Test + lint Python dependencies
├── alembic.ini                     # Alembic configuration
├── CLAUDE.md
├── README.md
│
├── specs/
│   ├── FUNC_SPEC.md
│   ├── TECH_SPEC.md                # This file
│   └── TECH_NOTES.md
│
├── commands/                       # Claude Code custom commands
│
├── backend/
│   ├── __init__.py
│   ├── app.py                      # FastAPI app factory, lifespan, middleware, static mount
│   ├── config.py                   # AppConfig dataclass, env var / default loading
│   ├── database.py                 # SQLAlchemy async engine, session factory, Base
│   │
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── __init__.py             # Re-exports all models
│   │   ├── user.py                 # User model
│   │   ├── session.py              # Session model
│   │   ├── wallet.py               # Wallet model
��   │   ├── transaction.py          # Transaction model
│   │   ├── balance_snapshot.py     # BalanceSnapshot model
│   │   ├── price_snapshot.py       # PriceSnapshot model
│   │   └── configuration.py        # Configuration key-value model
│   │
│   ├── schemas/                    # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── auth.py                 # SetupRequest, LoginRequest, AuthStatusResponse, etc.
│   │   ├── wallet.py               # WalletCreate, WalletResponse, WalletListResponse, etc.
│   │   ├── dashboard.py            # PortfolioSummary, HistoryDataPoint, PriceDataPoint, etc.
│   │   └── settings.py             # SettingsResponse, SettingsUpdate
│   │
│   ├── routers/                    # FastAPI routers (API layer)
│   │   ├── __init__.py
│   │   ├── auth.py                 # POST /api/auth/setup, /login, /logout; GET /api/auth/status
│   │   ├── wallets.py              # GET/POST /api/wallets, PATCH/DELETE /api/wallets/{id}
│   │   ├── dashboard.py            # GET /api/dashboard/summary, /portfolio-history, etc.
│   │   ├── settings.py             # GET/PUT /api/settings
│   │   └── websocket.py            # WS /api/ws
│   │
│   ├── services/                   # Business logic (service layer)
│   │   ├── __init__.py
│   │   ├── auth.py                 # AuthService: create account, login, validate session, etc.
│   │   ├── wallet.py               # WalletService: add, edit tag, remove, validate address
│   │   ├── refresh.py              # RefreshService: orchestrate full refresh cycle
│   │   ├── history.py              # HistoryService: full import + incremental sync
│   │   └── price.py                # PriceService: current + historical price logic
│   │
│   ├── clients/                    # External API clients
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseClient: shared httpx.AsyncClient, retry, timeout
│   │   ├── bitcoin.py              # BitcoinClient: Mempool.space endpoints
│   │   ├── kaspa.py                # KaspaClient: api.kaspa.org endpoints
│   │   └── coingecko.py            # CoinGeckoClient: price endpoints
│   │
│   ├── repositories/               # Database access (repository layer)
│   │   ├── __init__.py
│   │   ├── user.py                 # UserRepository
│   │   ├── session.py              # SessionRepository
│   │   ├── wallet.py               # WalletRepository
│   │   ├── transaction.py          # TransactionRepository
│   │   ├── snapshot.py             # BalanceSnapshotRepository, PriceSnapshotRepository
│   │   └── config.py               # ConfigRepository
│   │
│   ├── core/                       # Cross-cutting infrastructure
│   │   ├── __init__.py
│   │   ├── scheduler.py            # Scheduler: asyncio-based periodic refresh
│   │   ├── websocket_manager.py    # ConnectionManager: track connections, broadcast events
│   │   ├── dependencies.py         # FastAPI dependencies: get_db, get_current_user, etc.
│   │   ├── security.py             # Password hashing, token generation
│   │   └── exceptions.py           # Application exception classes
│   │
│   └── migrations/                 # Alembic migrations
│       ├── env.py
│       ├── script.py.mako
│       └── versions/
│           └── 001_initial_schema.py
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── tsconfig.app.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── env.d.ts
│   │
│   └── src/
│       ├── main.ts                 # App bootstrap: createApp, router, pinia
│       ├── App.vue                 # Root component: <RouterView>
│       │
│       ├── router/
│       │   └── index.ts            # Route definitions, auth navigation guard
│       │
│       ├── stores/
│       │   ├── auth.ts             # Auth state: token, user, login/logout actions
│       │   ├── dashboard.ts        # Dashboard data: summary, history, prices
│       │   ├── wallets.ts          # Wallet list, CRUD actions
│       │   └── settings.ts         # Settings state and save action
│       │
│       ├── composables/
│       │   ├── useApi.ts           # Axios-like fetch wrapper: base URL, auth header, error handling
│       │   └── useWebSocket.ts     # WebSocket connection: auto-reconnect, event dispatch
│       │
│       ├── views/
│       │   ├── SetupView.vue       # First-run account creation
│       │   ├── LoginView.vue       # Login form
│       │   ├── DashboardView.vue   # Main dashboard with all widgets
│       │   ├── WalletDetailView.vue # Per-wallet detail (balance chart, tx timeline)
│       │   └── SettingsView.vue    # Configuration panel
│       │
│       ├── components/
│       │   ├── layout/
│       │   │   ├── AppHeader.vue   # Top bar: logo, refresh button, settings icon, logout
│       │   │   └── AppFooter.vue   # Last updated timestamp
│       │   │
│       │   ├── widgets/
│       │   │   ├── TotalPortfolioValue.vue   # W1
│       │   │   ├── TotalBtcBalance.vue       # W2
│       │   │   ├── TotalKasBalance.vue       # W3
│       │   │   ├── WalletTable.vue           # W4
│       │   │   ├── PortfolioComposition.vue  # W5 (pie chart)
│       │   │   ├── PortfolioValueChart.vue   # W6 (line chart)
│       │   │   ├── WalletBalanceChart.vue    # W7 (line chart)
│       │   │   └── PriceChart.vue            # W8 (line chart)
│       │   │
│       │   ├── wallet/
│       │   │   ├── AddWalletDialog.vue       # Modal form for adding a wallet
│       │   │   ├── EditTagInput.vue          # Inline editable tag field
│       │   │   ├── RemoveWalletDialog.vue    # Confirmation dialog
│       │   │   └── WalletStatusBadge.vue     # Warning/pending icons
│       │   │
│       │   └── common/
│       │       ├── TimeRangeSelector.vue     # 7d / 30d / 90d / 1y / All buttons
│       │       ├── LoadingSpinner.vue
│       │       └── EmptyState.vue
│       │
│       ├── types/
│       │   ├── api.ts              # TypeScript interfaces for API responses
│       │   └── websocket.ts        # WebSocket event types
│       │
│       └── utils/
│           ├── format.ts           # Number formatting (USD, BTC, KAS, percentages)
│           └── validation.ts       # Client-side address validation (mirrors backend)
│
└── tests/
    ├── backend/
    │   ├── conftest.py             # Fixtures: test DB, test client, auth helpers
    │   ├── test_auth.py
    │   ├── test_wallets.py
    │   ├── test_dashboard.py
    │   ├── test_settings.py
    │   ├── test_refresh.py
    │   ├── test_history.py
    │   ├── test_bitcoin_client.py
    │   ├── test_kaspa_client.py
    │   ├── test_coingecko_client.py
    │   ├── test_scheduler.py
    │   ├── test_address_validation.py
    │   └── test_security.py
    │
    └── frontend/
        ├── setup.ts                # Vitest setup
        ├── components/
        ��   ├── WalletTable.test.ts
        │   ├── AddWalletDialog.test.ts
        │   └── TimeRangeSelector.test.ts
        └── stores/
            ├── auth.test.ts
            └── wallets.test.ts
```

### 3.1 Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Python files | `snake_case.py` | `balance_snapshot.py` |
| Python classes | `PascalCase` | `WalletService`, `BitcoinClient` |
| Python functions | `snake_case` | `get_wallet_by_id` |
| Python constants | `UPPER_SNAKE_CASE` | `MAX_WALLETS = 50` |
| Vue components | `PascalCase.vue` | `WalletTable.vue` |
| TypeScript files | `camelCase.ts` | `useWebSocket.ts` |
| TypeScript interfaces | `PascalCase` | `WalletResponse` |
| CSS classes | Tailwind utilities | `class="text-lg font-bold"` |
| API routes | `kebab-case` under `/api/` | `/api/dashboard/portfolio-history` |
| Database tables | `snake_case`, plural | `balance_snapshots` |
| Database columns | `snake_case` | `created_at` |

### 3.2 Module Boundaries

| Package | Exposes (public) | Keeps internal |
|---------|-----------------|----------------|
| `routers/` | FastAPI `APIRouter` instances | Route handler implementation |
| `services/` | Service classes with public methods | Internal helpers, validation logic |
| `repositories/` | Repository classes with CRUD methods | Raw SQL / SQLAlchemy query construction |
| `clients/` | Client classes with typed return values | HTTP request details, pagination, parsing |
| `models/` | SQLAlchemy model classes | Nothing hidden — all fields are the public schema |
| `schemas/` | Pydantic models | Validators (embedded in models) |
| `core/` | `Scheduler`, `ConnectionManager`, dependencies, security helpers | Implementation internals |

---

## 4. Component Specifications

### 4.1 Auth System

#### 4.1.a Interface and Contract

**Router: `backend/routers/auth.py`**

```python
router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.get("/status")
async def get_auth_status(db: AsyncSession) -> AuthStatusResponse:
    """
    Returns whether an account exists and whether the request has a valid session.
    No auth required.
    Returns: { "account_exists": bool, "authenticated": bool, "username": str | None }
    """

@router.post("/setup", status_code=201)
async def setup_account(body: SetupRequest, db: AsyncSession) -> LoginResponse:
    """
    Creates the single user account. Only callable when no account exists.
    Precondition: no user record in the database.
    Postcondition: user created, session created, token returned.
    Errors:
      - 409 Conflict: account already exists.
      - 422 Unprocessable Entity: validation error (password too short, mismatch).
    Returns: { "token": str, "expires_at": str (ISO 8601) }
    """

@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession) -> LoginResponse:
    """
    Validates credentials and creates a session.
    Precondition: account exists.
    Errors:
      - 401 Unauthorized: invalid credentials.
      - 429 Too Many Requests: rate limited after 5 consecutive failures.
    Returns: { "token": str, "expires_at": str (ISO 8601) }
    """

@router.post("/logout")
async def logout(token: str = Depends(get_auth_token), db: AsyncSession) -> dict:
    """
    Invalidates the current session.
    Precondition: valid session token in Authorization header.
    Postcondition: session deleted from DB.
    Returns: { "ok": true }
    """
```

**Service: `backend/services/auth.py`**

```python
class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.session_repo = SessionRepository(db)

    async def account_exists(self) -> bool: ...

    async def create_account(self, username: str, password: str) -> tuple[User, Session]:
        """
        Precondition: no user exists.
        Postcondition: user with hashed password stored; session created.
        Raises: AccountExistsError if a user already exists.
        """

    async def authenticate(self, username: str, password: str, remember_me: bool) -> Session:
        """
        Validates credentials, creates a session.
        Raises: InvalidCredentialsError on bad username/password.
        Raises: RateLimitedError after 5 consecutive failures.
        """

    async def validate_session(self, token: str) -> User:
        """
        Looks up session by token, checks expiry.
        Raises: InvalidSessionError if not found or expired.
        """

    async def invalidate_session(self, token: str) -> None: ...

    async def invalidate_all_sessions(self) -> None:
        """Used by CLI password reset."""

    async def reset_password(self, new_password: str) -> None:
        """Updates password hash, invalidates all sessions."""
```

#### 4.1.b Internal Design

**Login rate limiting state:**

```python
# In-memory (resets on restart — acceptable for single-user)
_failed_attempts: int = 0
_lockout_until: datetime | None = None

LOCKOUT_THRESHOLD = 5
LOCKOUT_DURATION = timedelta(seconds=30)
```

On each failed login: increment `_failed_attempts`. When it reaches `LOCKOUT_THRESHOLD`, set `_lockout_until = now + LOCKOUT_DURATION`. On successful login: reset both to 0/None. On login attempt while locked out: raise `RateLimitedError` with remaining seconds.

**Session token generation:**

```python
import secrets
token = secrets.token_urlsafe(32)  # 256-bit entropy, URL-safe base64
```

**Password hashing:**

```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Cost factor: 12 (default). Produces ~$2b$12$... strings.

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hash: str) -> bool:
    return pwd_context.verify(password, hash)
```

#### 4.1.c Code Snippets

**FastAPI dependency for auth:**

```python
# backend/core/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer_scheme = HTTPBearer(auto_error=False)

async def get_auth_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return credentials.credentials

async def get_current_user(
    token: str = Depends(get_auth_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    service = AuthService(db)
    try:
        return await service.validate_session(token)
    except InvalidSessionError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
```

**Session expiry logic:**

```python
# In AuthService.authenticate()
if remember_me:
    expires_at = datetime.utcnow() + timedelta(days=30)
else:
    expires_at = datetime.utcnow() + timedelta(days=7)

session = Session(
    id=str(uuid4()),
    user_id=user.id,
    token=secrets.token_urlsafe(32),
    created_at=datetime.utcnow(),
    expires_at=expires_at,
)
```

#### 4.1.d Edge Cases

| Edge Case | Expected Behavior | Test |
|-----------|-------------------|------|
| Setup called when account already exists | 409 Conflict | `test_setup_duplicate_account` |
| Login with wrong password | 401; `_failed_attempts` incremented | `test_login_invalid_password` |
| 5 consecutive failed logins | 429 with `retry_after: 30` | `test_login_rate_limit` |
| Login attempt during lockout | 429; lockout timer not extended | `test_login_during_lockout` |
| Successful login resets lockout counter | `_failed_attempts` = 0 | `test_login_resets_lockout` |
| Expired session token used | 401 | `test_expired_session` |
| Tampered/random token | 401 | `test_invalid_token` |
| Logout with invalid token | 401 | `test_logout_invalid_token` |
| Multiple active sessions (different browsers) | Each has its own token; logout invalidates only the current one | `test_multiple_sessions` |

---

### 4.2 Wallet Management

#### 4.2.a Interface and Contract

**Router: `backend/routers/wallets.py`**

```python
router = APIRouter(prefix="/api/wallets", tags=["wallets"], dependencies=[Depends(get_current_user)])

@router.get("/")
async def list_wallets(db: AsyncSession) -> WalletListResponse:
    """
    Returns all wallets with current balance and USD value.
    Returns: { "wallets": [...], "count": int, "limit": 50 }
    """

@router.post("/", status_code=201)
async def add_wallet(body: WalletCreate, db: AsyncSession) -> WalletResponse:
    """
    Adds a new wallet. Triggers background history import.
    Precondition: wallet count < 50; address valid; no duplicate (network, address).
    Postcondition: wallet stored; history import task spawned; balance fetch attempted.
    Errors:
      - 400: invalid address format, duplicate address, duplicate tag.
      - 409: wallet limit reached (50).
      - 422: validation error.
    Returns: { "id": uuid, "network": str, "address": str, "tag": str, ... }
    """

@router.patch("/{wallet_id}")
async def update_wallet_tag(wallet_id: str, body: WalletTagUpdate, db: AsyncSession) -> WalletResponse:
    """
    Updates the tag of an existing wallet.
    Errors:
      - 404: wallet not found.
      - 400: duplicate tag.
    """

@router.delete("/{wallet_id}", status_code=204)
async def remove_wallet(wallet_id: str, db: AsyncSession) -> None:
    """
    Removes the wallet and all associated snapshots and transactions (cascade).
    Errors:
      - 404: wallet not found.
    """

@router.post("/{wallet_id}/retry-history")
async def retry_history_import(wallet_id: str, db: AsyncSession) -> dict:
    """
    Retries a failed history import for a wallet.
    Errors:
      - 404: wallet not found.
    Returns: { "ok": true, "message": "History import started." }
    """
```

#### 4.2.b Internal Design

**Address validation (in `backend/services/wallet.py`):**

```python
import re

def validate_btc_address(address: str) -> str | None:
    """Returns None if valid, error message string if invalid."""
    address = address.strip().replace("\n", "").replace(" ", "")

    # P2PKH (Legacy) — starts with '1'
    if address.startswith("1"):
        if 25 <= len(address) <= 34 and re.fullmatch(r"[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]+", address):
            return None
        return "Invalid Bitcoin address format."

    # P2SH — starts with '3'
    if address.startswith("3"):
        if 25 <= len(address) <= 34 and re.fullmatch(r"[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]+", address):
            return None
        return "Invalid Bitcoin address format."

    # Bech32 SegWit v0 — starts with 'bc1q'
    if address.lower().startswith("bc1q"):
        address = address.lower()
        bech32_chars = r"[023456789acdefghjklmnpqrstuvwxyz]"
        if len(address) in (42, 62) and re.fullmatch(f"bc1q{bech32_chars}+", address):
            return None
        return "Invalid Bitcoin address format."

    # Bech32m Taproot — starts with 'bc1p'
    if address.lower().startswith("bc1p"):
        address = address.lower()
        bech32_chars = r"[023456789acdefghjklmnpqrstuvwxyz]"
        if len(address) == 62 and re.fullmatch(f"bc1p{bech32_chars}+", address):
            return None
        return "Invalid Bitcoin address format."

    return "Invalid Bitcoin address format."


def validate_kas_address(address: str) -> str | None:
    """Returns None if valid, error message string if invalid."""
    address = address.strip().replace("\n", "").replace(" ", "")

    if not address.startswith("kaspa:"):
        return "Invalid Kaspa address format. Kaspa addresses start with 'kaspa:'."

    remainder = address[6:]  # after "kaspa:"
    bech32_chars = r"[023456789acdefghjklmnpqrstuvwxyz]"
    if 61 <= len(remainder) <= 63 and re.fullmatch(bech32_chars + "+", remainder):
        return None

    return "Invalid Kaspa address format. Kaspa addresses start with 'kaspa:'."
```

**Duplicate detection:**
- BTC: case-insensitive comparison (`address.lower()`).
- KAS: exact match (addresses are always lowercase).
- Query: `SELECT id FROM wallets WHERE network = :net AND lower(address) = :addr AND user_id = :uid`

**Default tag generation:**

```python
async def generate_default_tag(network: str, db: AsyncSession) -> str:
    prefix = "BTC" if network == "BTC" else "KAS"
    n = 1
    while True:
        candidate = f"{prefix} Wallet #{n}"
        exists = await wallet_repo.tag_exists(candidate)
        if not exists:
            return candidate
        n += 1
```

#### 4.2.c Code Snippets

**Add wallet flow (service layer):**

```python
# backend/services/wallet.py
class WalletService:
    MAX_WALLETS = 50

    async def add_wallet(self, network: str, address: str, tag: str | None) -> Wallet:
        # 1. Check wallet limit
        count = await self.wallet_repo.count_by_user(self.user_id)
        if count >= self.MAX_WALLETS:
            raise WalletLimitReachedError("Wallet limit reached (50). Remove a wallet to add a new one.")

        # 2. Normalize address
        address = address.strip().replace("\n", "").replace(" ", "")

        # 3. Validate address format
        if network == "BTC":
            error = validate_btc_address(address)
        elif network == "KAS":
            error = validate_kas_address(address)
        else:
            raise ValueError(f"Unsupported network: {network}")
        if error:
            raise AddressValidationError(error)

        # 4. Check duplicate
        normalized = address.lower() if network == "BTC" else address
        exists = await self.wallet_repo.exists_by_address(network, normalized)
        if exists:
            raise DuplicateWalletError("This wallet address is already being tracked.")

        # 5. Handle tag
        if not tag or not tag.strip():
            tag = await self._generate_default_tag(network)
        else:
            tag = tag.strip()
            if len(tag) > 50:
                raise TagValidationError("Tag must be 50 characters or fewer.")
            if await self.wallet_repo.tag_exists(tag):
                raise TagValidationError("A wallet with this tag already exists.")

        # 6. Persist wallet
        wallet = Wallet(
            id=str(uuid4()),
            user_id=self.user_id,
            network=network,
            address=address,
            tag=tag,
            created_at=datetime.utcnow(),
        )
        await self.wallet_repo.create(wallet)
        await self.db.commit()

        # 7. Trigger background tasks (non-blocking)
        asyncio.create_task(self._fetch_initial_data(wallet))

        return wallet

    async def _fetch_initial_data(self, wallet: Wallet) -> None:
        """Fetch current balance + start history import. Runs as background task."""
        try:
            await self.refresh_service.refresh_single_wallet(wallet)
        except Exception:
            logger.warning(f"Could not fetch initial balance for {wallet.tag}")
        # History import (separate, longer-running)
        try:
            await self.history_service.full_import(wallet)
        except Exception:
            logger.warning(f"History import failed for {wallet.tag}")
        # Notify connected WebSocket clients
        await self.ws_manager.broadcast("wallet:added", {"wallet_id": wallet.id})
```

#### 4.2.d Edge Cases

| Edge Case | Expected Behavior | Test |
|-----------|-------------------|------|
| Address with leading/trailing whitespace | Trimmed before validation | `test_add_wallet_whitespace` |
| Address with embedded newlines | Stripped before validation | `test_add_wallet_newlines` |
| Empty address | 400: "Please enter a wallet address." | `test_add_wallet_empty_address` |
| Wallet #51 | 409: limit message | `test_add_wallet_limit` |
| Duplicate (network, address) | 400: "This wallet address is already being tracked." | `test_add_wallet_duplicate` |
| Duplicate BTC address, different case | Detected as duplicate (case-insensitive) | `test_add_wallet_btc_case_insensitive` |
| Tag > 50 chars | 400: "Tag must be 50 characters or fewer." | `test_add_wallet_long_tag` |
| Duplicate tag (case-insensitive) | 400: "A wallet with this tag already exists." | `test_add_wallet_duplicate_tag` |
| Remove last wallet | Succeeds; dashboard shows empty state | `test_remove_last_wallet` |
| API unreachable on initial balance fetch | Wallet saved; balance shows "Pending" | `test_add_wallet_api_unreachable` |

---

### 4.3 External API Clients

#### 4.3.a Base Client

```python
# backend/clients/base.py
import httpx
import logging

logger = logging.getLogger(__name__)

class BaseClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers={"User-Agent": "CryptoDash/1.0"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: dict | None = None) -> dict | list:
        response = await self._client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    async def _get_with_retry(self, path: str, params: dict | None = None) -> dict | list:
        """Single retry after 10 seconds on failure (per spec: 7.1 failure handling)."""
        try:
            return await self._get(path, params)
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.warning(f"First attempt failed for {path}: {e}. Retrying in 10s.")
            await asyncio.sleep(10)
            return await self._get(path, params)
```

#### 4.3.b Bitcoin Client (Mempool.space)

```python
# backend/clients/bitcoin.py
from decimal import Decimal

SATOSHI = Decimal("100000000")  # 1 BTC = 10^8 satoshis

class BitcoinClient(BaseClient):
    def __init__(self):
        super().__init__(base_url="https://mempool.space/api")

    async def get_balance(self, address: str) -> Decimal:
        """Returns confirmed balance in BTC."""
        data = await self._get_with_retry(f"/address/{address}")
        funded = data["chain_stats"]["funded_txo_sum"]
        spent = data["chain_stats"]["spent_txo_sum"]
        return Decimal(funded - spent) / SATOSHI

    async def get_transaction_summary(self, address: str) -> list[dict]:
        """
        Uses /txs/summary endpoint — returns signed net satoshi values per tx.
        Returns up to 5000 most recent transactions.
        Each entry: { "txid": str, "height": int, "value": int (signed satoshis), "time": int }
        """
        return await self._get(f"/address/{address}/txs/summary")

    async def get_transactions_paginated(self, address: str, after_txid: str | None = None) -> list[dict]:
        """
        Full transaction objects via /txs/chain with pagination.
        Returns 25 txs per page, newest first.
        Pass after_txid for next page.
        """
        path = f"/address/{address}/txs/chain"
        if after_txid:
            path += f"/{after_txid}"
        return await self._get(path)

    async def get_all_transactions(self, address: str) -> list[dict]:
        """
        Fetches ALL transactions for an address using the summary endpoint
        when tx count <= 5000, falling back to paginated full tx fetching
        with UTXO parsing for addresses with more transactions.
        Returns list of: { "tx_hash": str, "amount_sat": int (signed), "block_height": int, "timestamp": int }
        """
        # Strategy: try summary first (up to 5000 txs, much faster)
        summary = await self.get_transaction_summary(address)

        # Check if we got all transactions
        addr_info = await self._get(f"/address/{address}")
        total_txs = addr_info["chain_stats"]["tx_count"]

        if len(summary) >= total_txs or total_txs <= 5000:
            # Summary covers all transactions
            return [
                {
                    "tx_hash": tx["txid"],
                    "amount_sat": tx["value"],
                    "block_height": tx["height"],
                    "timestamp": tx["time"],
                }
                for tx in summary
            ]

        # Fallback: paginated full transaction fetch with UTXO parsing
        return await self._fetch_all_with_utxo_parsing(address)

    async def _fetch_all_with_utxo_parsing(self, address: str) -> list[dict]:
        """Paginate through /txs/chain and parse vin/vout for net amounts."""
        all_txs = []
        after_txid = None
        address_lower = address.lower()

        while True:
            page = await self.get_transactions_paginated(address, after_txid)
            if not page:
                break

            for tx in page:
                inflow = sum(
                    vout["value"]
                    for vout in tx.get("vout", [])
                    if vout.get("scriptpubkey_address", "").lower() == address_lower
                )
                outflow = sum(
                    vin["prevout"]["value"]
                    for vin in tx.get("vin", [])
                    if vin.get("prevout") and
                       vin["prevout"].get("scriptpubkey_address", "").lower() == address_lower
                )
                net = inflow - outflow
                status = tx.get("status", {})
                all_txs.append({
                    "tx_hash": tx["txid"],
                    "amount_sat": net,
                    "block_height": status.get("block_height"),
                    "timestamp": status.get("block_time"),
                })

            if len(page) < 25:
                break
            after_txid = page[-1]["txid"]

            # Rate-limit: small delay between pages
            await asyncio.sleep(0.2)

        return all_txs
```

#### 4.3.c Kaspa Client

```python
# backend/clients/kaspa.py
from decimal import Decimal

SOMPI = Decimal("100000000")  # 1 KAS = 10^8 sompi

class KaspaClient(BaseClient):
    def __init__(self):
        super().__init__(base_url="https://api.kaspa.org")

    async def get_balance(self, address: str) -> Decimal:
        """Returns balance in KAS."""
        data = await self._get_with_retry(f"/addresses/{address}/balance")
        return Decimal(str(data["balance"])) / SOMPI

    async def get_price_usd(self) -> Decimal:
        """Returns KAS/USD price from Kaspa's own API. Used as fallback."""
        data = await self._get("/info/price")
        return Decimal(str(data["price"]))

    async def get_transaction_count(self, address: str) -> int:
        data = await self._get(f"/addresses/{address}/transactions-count")
        return data["total"]

    async def get_transactions_page(
        self, address: str, limit: int = 500, before: int | None = None
    ) -> tuple[list[dict], int | None]:
        """
        Fetches a page of transactions using cursor-based pagination.
        Returns (transactions, next_before_cursor).
        next_before_cursor is None when no more pages.
        """
        params = {
            "limit": limit,
            "resolve_previous_outpoints": "light",  # REQUIRED for input address/amount
            "fields": "transaction_id,block_time,inputs,outputs,is_accepted",
        }
        if before is not None:
            params["before"] = before

        response = await self._client.get(
            f"/addresses/{address}/full-transactions-page",
            params=params,
        )
        response.raise_for_status()

        # Next page cursor from response header
        next_before = response.headers.get("X-Next-Page-Before")
        next_cursor = int(next_before) if next_before else None

        return response.json(), next_cursor

    async def get_all_transactions(self, address: str) -> list[dict]:
        """
        Fetches all transactions for a Kaspa address with UTXO-style parsing.
        Returns list of: { "tx_hash": str, "amount_sompi": int (signed), "timestamp": int }
        """
        all_txs = []
        cursor = None

        while True:
            page, next_cursor = await self.get_transactions_page(address, limit=500, before=cursor)
            if not page:
                break

            for tx in page:
                if not tx.get("is_accepted", False):
                    continue  # Skip rejected transactions

                inflow = sum(
                    int(out["amount"])
                    for out in tx.get("outputs", [])
                    if out.get("script_public_key_address") == address
                )
                outflow = sum(
                    int(inp["previous_outpoint_amount"])
                    for inp in tx.get("inputs", [])
                    if inp.get("previous_outpoint_address") == address
                )
                net = inflow - outflow

                all_txs.append({
                    "tx_hash": tx["transaction_id"],
                    "amount_sompi": net,
                    "timestamp": tx.get("block_time"),  # epoch milliseconds
                })

            if next_cursor is None:
                break
            cursor = next_cursor

            await asyncio.sleep(0.2)

        return all_txs
```

#### 4.3.d CoinGecko Client

```python
# backend/clients/coingecko.py
from decimal import Decimal

COIN_IDS = {"BTC": "bitcoin", "KAS": "kaspa"}

class CoinGeckoClient(BaseClient):
    # Free tier: 30 requests/minute, 10,000 credits/month
    MAX_HISTORY_DAYS = 365  # Free tier hard limit

    def __init__(self):
        super().__init__(base_url="https://api.coingecko.com/api/v3", timeout=30.0)

    async def get_current_prices(self) -> dict[str, Decimal]:
        """
        Returns current USD prices for BTC and KAS in a single API call.
        Returns: { "BTC": Decimal("71681"), "KAS": Decimal("0.03251085") }
        """
        data = await self._get_with_retry("/simple/price", params={
            "ids": "bitcoin,kaspa",
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_last_updated_at": "true",
        })
        result = {}
        for network, coin_id in COIN_IDS.items():
            if coin_id in data and "usd" in data[coin_id]:
                result[network] = Decimal(str(data[coin_id]["usd"]))
        return result

    async def get_price_history(self, network: str, days: int) -> list[tuple[int, Decimal]]:
        """
        Returns daily historical prices as [(timestamp_ms, price_usd), ...].
        Max 365 days on free tier.
        """
        days = min(days, self.MAX_HISTORY_DAYS)
        coin_id = COIN_IDS[network]
        data = await self._get(f"/coins/{coin_id}/market_chart", params={
            "vs_currency": "usd",
            "days": days,
            "interval": "daily",
        })
        return [
            (int(point[0]), Decimal(str(point[1])))
            for point in data.get("prices", [])
        ]

    async def get_price_at_date_range(
        self, network: str, from_ts: int, to_ts: int
    ) -> list[tuple[int, Decimal]]:
        """
        Returns prices in a Unix timestamp range (seconds).
        Limited to 365 days from today on the free tier.
        Returns: [(timestamp_ms, price_usd), ...]
        """
        coin_id = COIN_IDS[network]
        data = await self._get(f"/coins/{coin_id}/market_chart/range", params={
            "vs_currency": "usd",
            "from": from_ts,
            "to": to_ts,
        })
        return [
            (int(point[0]), Decimal(str(point[1])))
            for point in data.get("prices", [])
        ]
```

#### 4.3.e Edge Cases (All Clients)

| Edge Case | Expected Behavior | Test |
|-----------|-------------------|------|
| HTTP 429 (rate limited) | Log warning; wait `Retry-After` seconds (or 60s default); retry once | `test_rate_limit_handling` |
| HTTP 5xx | Log error; do not retry immediately; raise so caller handles | `test_server_error` |
| Request timeout (>30s) | `httpx.ReadTimeout` raised; logged as warning by caller | `test_request_timeout` |
| Network unreachable | `httpx.ConnectError` raised; logged by caller | `test_network_unreachable` |
| CoinGecko returns price = 0 | Treated as error; caller discards and uses cached price | `test_zero_price` |
| Mempool.space summary endpoint returns < total txs | Fallback to paginated UTXO parsing | `test_btc_large_address_fallback` |
| Kaspa tx with `is_accepted = false` | Skipped during parsing | `test_kaspa_rejected_tx` |
| Coinbase transaction (BTC, no prevout) | Inflow only; `vin[].is_coinbase = true` is handled | `test_btc_coinbase_tx` |

---

### 4.4 Refresh Service

#### 4.4.a Interface and Contract

```python
# backend/services/refresh.py
class RefreshService:
    def __init__(
        self,
        db: AsyncSession,
        btc_client: BitcoinClient,
        kas_client: KaspaClient,
        coingecko_client: CoinGeckoClient,
        ws_manager: ConnectionManager,
    ):
        self._lock = asyncio.Lock()
        ...

    async def run_full_refresh(self) -> RefreshResult:
        """
        Fetches balances for ALL wallets and prices for BTC+KAS.
        Stores balance and price snapshots.
        Precondition: acquires _lock; if already locked, returns immediately with skipped=True.
        Postcondition: new snapshots stored; WebSocket event broadcast.
        Returns: RefreshResult(success_count, failure_count, skipped, errors, timestamp)
        """

    async def refresh_single_wallet(self, wallet: Wallet) -> BalanceSnapshot | None:
        """
        Fetches balance for one wallet. Used for initial fetch after adding.
        Does NOT acquire _lock (runs independently).
        Returns: BalanceSnapshot or None on failure.
        """
```

#### 4.4.b Internal Design

**Full refresh flow (step by step):**

1. Attempt to acquire `_lock`. If already held: log "Refresh skipped — previous cycle still running", return `RefreshResult(skipped=True)`.
2. Broadcast `refresh:started` via WebSocket.
3. Fetch current prices from CoinGecko (`get_current_prices()`).
   - If CoinGecko fails: try Kaspa API for KAS price (`kas_client.get_price_usd()`).
   - If price = 0: discard, use cached.
   - Store successful prices as `PriceSnapshot` records.
4. For each wallet (in parallel, up to 5 concurrent):
   - Call `btc_client.get_balance()` or `kas_client.get_balance()` depending on network.
   - On success: store `BalanceSnapshot(source="live")`.
   - On failure: log warning, record failure in result.
   - Perform incremental transaction sync (see History Service).
5. Broadcast `refresh:completed` with result summary.
6. Release `_lock`.

**Parallel wallet fetching:**

```python
async def _fetch_all_wallets(self, wallets: list[Wallet]) -> list[WalletRefreshResult]:
    semaphore = asyncio.Semaphore(5)  # Max 5 concurrent API calls

    async def fetch_one(wallet: Wallet) -> WalletRefreshResult:
        async with semaphore:
            try:
                balance = await self._get_balance(wallet)
                snapshot = BalanceSnapshot(
                    id=str(uuid4()),
                    wallet_id=wallet.id,
                    balance=balance,
                    timestamp=datetime.utcnow(),
                    source="live",
                )
                await self.snapshot_repo.create(snapshot)
                return WalletRefreshResult(wallet_id=wallet.id, success=True, balance=balance)
            except Exception as e:
                logger.warning(f"Balance fetch failed for {wallet.tag}: {e}")
                return WalletRefreshResult(wallet_id=wallet.id, success=False, error=str(e))

    return await asyncio.gather(*[fetch_one(w) for w in wallets])
```

#### 4.4.c Code Snippets

**Balance consistency check (FR-028):**

```python
async def _verify_balance_consistency(self, wallet: Wallet, api_balance: Decimal) -> None:
    """Compare API-reported balance with computed-from-transactions balance."""
    computed = await self.transaction_repo.compute_balance(wallet.id)
    if computed is not None and abs(computed - api_balance) > Decimal("0.00000001"):
        logger.warning(
            f"Balance mismatch for {wallet.tag}: "
            f"computed={computed}, api={api_balance}. Using API balance as authoritative."
        )
```

---

### 4.5 History Service

#### 4.5.a Interface and Contract

```python
# backend/services/history.py
class HistoryService:
    async def full_import(self, wallet: Wallet) -> HistoryImportResult:
        """
        One-time full transaction history import for a newly added wallet.
        Fetches all available transactions from the blockchain API.
        Stores them in the transactions table, deduplicating by tx_hash.
        Computes and stores daily historical balance snapshots.
        Fetches historical prices from CoinGecko for USD value computation.
        Broadcasts progress events via WebSocket.
        """

    async def incremental_sync(self, wallet: Wallet) -> int:
        """
        Fetches only transactions newer than the most recent stored transaction.
        Called on each refresh cycle.
        Returns: number of new transactions stored.
        """
```

#### 4.5.b Internal Design

**Full import algorithm (step by step):**

1. Broadcast `wallet:history:progress` with `{ "wallet_id": ..., "status": "started" }`.
2. Fetch all transactions via the appropriate client (`btc_client.get_all_transactions()` or `kas_client.get_all_transactions()`).
3. For each transaction:
   - Check if `tx_hash` already exists in DB (deduplicate).
   - Create `Transaction` record with computed `amount` (net flow) and `timestamp`.
   - Set `balance_after` by maintaining a running sum during replay.
4. Batch-insert transactions (500 at a time for SQLite performance).
5. Compute daily end-of-day balances from the transaction list and store as `BalanceSnapshot(source="historical")`.
6. Fetch historical prices from CoinGecko (up to 365 days) and store as `PriceSnapshot` records.
7. Broadcast `wallet:history:completed`.

**Incremental sync algorithm:**

1. Find the most recent stored transaction for this wallet (by `block_height` or `timestamp`).
2. For **BTC**: Use `mempool.space /address/{addr}/txs/chain` paginated from newest; stop when we encounter a `txid` already in our DB.
3. For **KAS**: Use `full-transactions-page` with `after={last_stored_timestamp}` cursor.
4. Store new transactions, update `balance_after` fields.
5. If new transactions found, store a new `BalanceSnapshot(source="live")` with the updated balance.

**Timeout handling for large histories (>100k txs):**

```python
IMPORT_TIMEOUT = 300  # 5 minutes

async def full_import(self, wallet: Wallet) -> HistoryImportResult:
    try:
        result = await asyncio.wait_for(
            self._do_full_import(wallet),
            timeout=self.IMPORT_TIMEOUT,
        )
        return result
    except asyncio.TimeoutError:
        logger.warning(f"History import timed out for {wallet.tag}. Partial data stored.")
        await self.ws_manager.broadcast("wallet:history:completed", {
            "wallet_id": wallet.id,
            "partial": True,
            "message": "Import timed out. Incremental syncs will pick up remaining data.",
        })
        return HistoryImportResult(partial=True)
```

---

### 4.6 Scheduler

#### 4.6.a Interface and Contract

```python
# backend/core/scheduler.py
class Scheduler:
    def __init__(self, refresh_service: RefreshService, config_repo: ConfigRepository):
        self._task: asyncio.Task | None = None
        self._refresh_service = refresh_service
        self._config_repo = config_repo

    async def start(self) -> None:
        """Read interval from config and start the loop. Called at app startup."""

    async def restart(self, interval_minutes: int | None) -> None:
        """Cancel current loop (if any) and start a new one with the given interval.
        If interval_minutes is None, the scheduler is disabled (no auto-refresh)."""

    async def stop(self) -> None:
        """Cancel the loop. Called at app shutdown."""
```

#### 4.6.b Internal Design

```python
async def _loop(self, interval_minutes: int) -> None:
    """Main scheduler loop. Runs until cancelled."""
    logger.info(f"Scheduler started with interval={interval_minutes}m")
    while True:
        await asyncio.sleep(interval_minutes * 60)
        logger.info("Scheduled refresh starting")
        try:
            result = await self._refresh_service.run_full_refresh()
            logger.info(
                f"Scheduled refresh completed: "
                f"{result.success_count} ok, {result.failure_count} failed"
            )
        except Exception as e:
            logger.error(f"Scheduled refresh failed: {e}")

async def restart(self, interval_minutes: int | None) -> None:
    if self._task and not self._task.done():
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    if interval_minutes is not None:
        self._task = asyncio.create_task(self._loop(interval_minutes))
```

**Key behavior:**
- The sleep happens **before** the first refresh (the first auto-refresh is `interval_minutes` after startup, not immediately).
- If a cycle is still running when the next sleep ends, `run_full_refresh()` returns `skipped=True` because it can't acquire the lock (FR-047).
- When the user changes the interval, `restart()` cancels the current loop and starts fresh. The next refresh will occur `new_interval` minutes from now.

---

### 4.7 WebSocket Manager

#### 4.7.a Interface and Contract

```python
# backend/core/websocket_manager.py
class ConnectionManager:
    async def connect(self, websocket: WebSocket, token: str) -> bool:
        """
        Validates the token, accepts the WebSocket, adds to active list.
        Returns False if token is invalid (connection rejected).
        """

    def disconnect(self, websocket: WebSocket) -> None:
        """Removes a WebSocket from the active list."""

    async def broadcast(self, event: str, data: dict) -> None:
        """Sends a JSON message to all connected clients."""
```

#### 4.7.b Internal Design

```python
class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket, token: str) -> bool:
        # Validate token against DB
        async with get_db_session() as db:
            service = AuthService(db)
            try:
                await service.validate_session(token)
            except InvalidSessionError:
                await websocket.close(code=4001, reason="Invalid token")
                return False

        await websocket.accept()
        self._connections.append(websocket)
        return True

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast(self, event: str, data: dict) -> None:
        message = {"event": event, "data": data, "timestamp": datetime.utcnow().isoformat()}
        dead = []
        for ws in self._connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
```

**WebSocket endpoint:**

```python
# backend/routers/websocket.py
@router.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    connected = await ws_manager.connect(websocket, token)
    if not connected:
        return
    try:
        while True:
            # Keep connection alive; listen for client pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
```

**WebSocket events reference:**

| Event | Payload | Trigger |
|-------|---------|---------|
| `refresh:started` | `{}` | Manual or scheduled refresh begins |
| `refresh:completed` | `{ "success_count": int, "failure_count": int, "timestamp": str }` | Refresh cycle ends |
| `wallet:added` | `{ "wallet_id": str }` | New wallet created |
| `wallet:removed` | `{ "wallet_id": str }` | Wallet deleted |
| `wallet:updated` | `{ "wallet_id": str }` | Wallet tag edited |
| `wallet:history:progress` | `{ "wallet_id": str, "status": str, "progress_pct": int | null }` | During history import |
| `wallet:history:completed` | `{ "wallet_id": str, "partial": bool }` | History import done |
| `settings:updated` | `{ "key": str, "value": str }` | Settings changed |

---

## 5. Data Models

### 5.1 SQLAlchemy Models

All entity IDs are **UUIDv4** strings (per TECH_NOTES.md recommendation). Timestamps are stored as UTC.

```python
# backend/database.py
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

class Base(DeclarativeBase):
    pass

engine = create_async_engine("sqlite+aiosqlite:///data/cryptodash.db", echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

**User:**

```python
# backend/models/user.py
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)        # UUIDv4
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)  # bcrypt output
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
```

**Session:**

```python
class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
```

**Wallet:**

```python
class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (
        UniqueConstraint("user_id", "network", "address", name="uq_wallet_network_address"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    network: Mapped[str] = mapped_column(String(3), nullable=False)  # "BTC" or "KAS"
    address: Mapped[str] = mapped_column(String(128), nullable=False)
    tag: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="wallet", cascade="all, delete-orphan")
    balance_snapshots: Mapped[list["BalanceSnapshot"]] = relationship(back_populates="wallet", cascade="all, delete-orphan")
```

**Transaction:**

```python
class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("wallet_id", "tx_hash", name="uq_tx_wallet_hash"),
        Index("ix_tx_wallet_height", "wallet_id", "block_height"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    wallet_id: Mapped[str] = mapped_column(String(36), ForeignKey("wallets.id"), nullable=False)
    tx_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    amount: Mapped[str] = mapped_column(String(40), nullable=False)        # Decimal as string, signed
    balance_after: Mapped[str | None] = mapped_column(String(40))          # Running balance
    block_height: Mapped[int | None] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # On-chain confirmation time
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    wallet: Mapped["Wallet"] = relationship(back_populates="transactions")
```

> **Note on Decimal storage:** SQLite does not have a native DECIMAL type. Amounts are stored as strings to preserve full precision (18 decimal places). Converted to `Decimal` at the repository layer on read.

**BalanceSnapshot:**

```python
class BalanceSnapshot(Base):
    __tablename__ = "balance_snapshots"
    __table_args__ = (
        Index("ix_bs_wallet_timestamp", "wallet_id", "timestamp"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    wallet_id: Mapped[str] = mapped_column(String(36), ForeignKey("wallets.id"), nullable=False)
    balance: Mapped[str] = mapped_column(String(40), nullable=False)       # Decimal as string
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False)        # "live" or "historical"

    wallet: Mapped["Wallet"] = relationship(back_populates="balance_snapshots")
```

**PriceSnapshot:**

```python
class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    __table_args__ = (
        Index("ix_ps_coin_timestamp", "coin", "timestamp"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    coin: Mapped[str] = mapped_column(String(3), nullable=False)           # "BTC" or "KAS"
    price_usd: Mapped[str] = mapped_column(String(40), nullable=False)     # Decimal as string
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
```

**Configuration:**

```python
class Configuration(Base):
    __tablename__ = "configuration"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(256), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
```

### 5.2 Database Initialization

On startup, enable WAL mode and create tables:

```python
async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)

    # Seed default configuration if not present
    async with async_session() as session:
        config_repo = ConfigRepository(session)
        await config_repo.set_default("refresh_interval_minutes", "15")
        await session.commit()
```

### 5.3 API Request/Response Schemas

**Auth schemas:**

```python
# backend/schemas/auth.py
class SetupRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=8)
    password_confirm: str

    @model_validator(mode="after")
    def passwords_match(self) -> "SetupRequest":
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match.")
        return self

class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False

class LoginResponse(BaseModel):
    token: str
    expires_at: str  # ISO 8601

class AuthStatusResponse(BaseModel):
    account_exists: bool
    authenticated: bool
    username: str | None = None
```

**Wallet schemas:**

```python
# backend/schemas/wallet.py
class WalletCreate(BaseModel):
    network: Literal["BTC", "KAS"]
    address: str = Field(min_length=1)
    tag: str | None = Field(default=None, max_length=50)

class WalletTagUpdate(BaseModel):
    tag: str = Field(min_length=1, max_length=50)

class WalletResponse(BaseModel):
    id: str
    network: str
    address: str
    tag: str
    balance: str | None  # Decimal as string, None if pending
    balance_usd: str | None
    created_at: str
    last_updated: str | None
    warning: str | None  # e.g. "Last update failed."
    history_status: str  # "complete", "importing", "failed", "pending"

class WalletListResponse(BaseModel):
    wallets: list[WalletResponse]
    count: int
    limit: int = 50
```

**Dashboard schemas:**

```python
# backend/schemas/dashboard.py
class PortfolioSummary(BaseModel):
    total_value_usd: str | None          # Decimal as string
    total_btc: str                        # Decimal as string
    total_kas: str                        # Decimal as string
    btc_value_usd: str | None
    kas_value_usd: str | None
    change_24h_usd: str | None            # Signed
    change_24h_pct: str | None            # Signed
    btc_price_usd: str | None
    kas_price_usd: str | None
    last_updated: str | None              # ISO 8601

class HistoryDataPoint(BaseModel):
    timestamp: str  # ISO 8601
    value: str      # Decimal as string (USD or native coin)

class PortfolioHistoryResponse(BaseModel):
    data_points: list[HistoryDataPoint]
    range: str  # "7d", "30d", "90d", "1y", "all"
    unit: str   # "usd"

class WalletHistoryResponse(BaseModel):
    wallet_id: str
    data_points: list[HistoryDataPoint]
    range: str
    unit: str  # "usd" or "native"

class PriceHistoryResponse(BaseModel):
    btc: list[HistoryDataPoint]
    kas: list[HistoryDataPoint]
    range: str

class PortfolioComposition(BaseModel):
    segments: list[CompositionSegment]

class CompositionSegment(BaseModel):
    network: str      # "BTC" or "KAS"
    value_usd: str    # Decimal as string
    percentage: str   # e.g. "65.4"
```

**Settings schemas:**

```python
# backend/schemas/settings.py
class SettingsResponse(BaseModel):
    refresh_interval_minutes: int | None  # None = disabled

class SettingsUpdate(BaseModel):
    refresh_interval_minutes: int | None = Field(None)

    @field_validator("refresh_interval_minutes")
    @classmethod
    def validate_interval(cls, v: int | None) -> int | None:
        if v is not None and v not in (5, 15, 30, 60):
            raise ValueError("Refresh interval must be 5, 15, 30, or 60 minutes, or null to disable.")
        return v
```

### 5.4 API Error Response Shape

All errors return a consistent JSON shape:

```json
{
  "detail": "Human-readable error message."
}
```

For validation errors (422), FastAPI returns:

```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "String should have at least 8 characters",
      "type": "string_too_short"
    }
  ]
}
```

---

## 6. Configuration and CLI

### 6.1 Application Configuration

Configuration is loaded at startup from environment variables with sensible defaults. No config file is required.

| Env Variable | Type | Default | Description |
|-------------|------|---------|-------------|
| `CRYPTODASH_DB_PATH` | string | `data/cryptodash.db` | Path to the SQLite database file. |
| `CRYPTODASH_HOST` | string | `0.0.0.0` | Bind address for uvicorn. |
| `CRYPTODASH_PORT` | int | `8000` | Bind port. |
| `CRYPTODASH_LOG_LEVEL` | string | `info` | Logging level: debug, info, warning, error. |

```python
# backend/config.py
from dataclasses import dataclass
import os

@dataclass
class AppConfig:
    db_path: str = os.getenv("CRYPTODASH_DB_PATH", "data/cryptodash.db")
    host: str = os.getenv("CRYPTODASH_HOST", "0.0.0.0")
    port: int = int(os.getenv("CRYPTODASH_PORT", "8000"))
    log_level: str = os.getenv("CRYPTODASH_LOG_LEVEL", "info")

config = AppConfig()
```

### 6.2 CLI Entry Point

**`run.py`** — standalone entry point:

```python
#!/usr/bin/env python3
"""CryptoDash — self-hosted crypto portfolio dashboard."""
import sys
import os

def main():
    # Check Python version
    if sys.version_info < (3, 11):
        print("Error: Python 3.11+ is required.", file=sys.stderr)
        sys.exit(1)

    # Ensure data directory exists
    db_path = os.getenv("CRYPTODASH_DB_PATH", "data/cryptodash.db")
    os.makedirs(os.path.dirname(db_path) or "data", exist_ok=True)

    import uvicorn
    from backend.config import config

    uvicorn.run(
        "backend.app:create_app",
        factory=True,
        host=config.host,
        port=config.port,
        log_level=config.log_level,
    )

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "reset-password":
        from backend.cli import reset_password
        import asyncio
        asyncio.run(reset_password())
    else:
        main()
```

**Password reset CLI** (`backend/cli.py`):

```python
import asyncio
import getpass
from backend.database import async_session, init_db
from backend.services.auth import AuthService

async def reset_password():
    await init_db()
    pw = getpass.getpass("New password: ")
    pw2 = getpass.getpass("Confirm password: ")
    if pw != pw2:
        print("Passwords do not match.")
        return
    if len(pw) < 8:
        print("Password must be at least 8 characters.")
        return

    async with async_session() as db:
        service = AuthService(db)
        await service.reset_password(pw)
        await db.commit()

    print("Password updated. All sessions invalidated.")
```

**Usage:**
- Start server: `./run.py` (or `python run.py`)
- Reset password: `./run.py reset-password`

### 6.3 Startup Sequence

Ordered list from invocation to "ready to serve":

1. **`run.py`** validates Python version >= 3.11.
2. **`run.py`** creates the data directory if missing.
3. **uvicorn** starts and calls `create_app()`.
4. **`create_app()`** registers the lifespan context manager.
5. **Lifespan startup:**
   a. Initialize the database: enable WAL mode, enable foreign keys, run `create_all` (create tables if missing).
   b. Seed default configuration (`refresh_interval_minutes = 15`).
   c. Create shared `httpx.AsyncClient` instances for Bitcoin, Kaspa, CoinGecko.
   d. Create the `ConnectionManager` (WebSocket).
   e. Create the `RefreshService` and `HistoryService`.
   f. Create the `Scheduler` and call `scheduler.start()` — reads interval from DB, starts the loop.
   g. Clean up expired sessions from the database.
6. **Mount routers:** auth, wallets, dashboard, settings, websocket.
7. **Mount static files:** `frontend/dist/` at `/` with SPA fallback (serve `index.html` for unmatched routes).
8. **uvicorn** binds to `host:port` and begins accepting connections.
9. Log: `CryptoDash running at http://{host}:{port}`.

**Lifespan context manager:**

```python
# backend/app.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    app.state.btc_client = BitcoinClient()
    app.state.kas_client = KaspaClient()
    app.state.coingecko_client = CoinGeckoClient()
    app.state.ws_manager = ConnectionManager()
    app.state.refresh_service = RefreshService(...)
    app.state.scheduler = Scheduler(app.state.refresh_service, ...)
    await app.state.scheduler.start()
    logger.info("CryptoDash started")

    yield

    # Shutdown
    await app.state.scheduler.stop()
    await app.state.btc_client.close()
    await app.state.kas_client.close()
    await app.state.coingecko_client.close()
    logger.info("CryptoDash stopped")
```

---

## 7. Error Handling Strategy

### 7.1 Error Taxonomy

| Category | Examples | HTTP Status |
|----------|---------|-------------|
| **Client input** | Invalid address, duplicate wallet, bad credentials, missing field | 400, 401, 409, 422 |
| **Rate limiting** | Login lockout, external API 429 | 429 |
| **Not found** | Wallet ID doesn't exist | 404 |
| **External API failure** | Timeout, 5xx, network unreachable | (internal — not exposed as HTTP error; degraded mode) |
| **Internal** | DB write failure, unexpected exception | 500 |

### 7.2 Per-Layer Error Handling

| Layer | Behavior |
|-------|----------|
| **API (routers)** | Catches service-layer exceptions and maps them to HTTP responses. Logs nothing (logging is the service layer's job). Returns structured JSON errors. |
| **Service** | Raises domain-specific exceptions (`AddressValidationError`, `WalletLimitReachedError`, etc.). Logs warnings for external failures. Never catches exceptions it can't handle. |
| **Repository** | Raises `sqlalchemy` exceptions on DB errors. Does not log (caller logs). |
| **Clients** | Raises `httpx` exceptions on network errors. `_get_with_retry` handles one retry. Logs warnings on retry. |
| **Scheduler** | Catches all exceptions from `run_full_refresh()` and logs them as ERROR. Never crashes — always schedules the next cycle. |

### 7.3 Application Exceptions

```python
# backend/core/exceptions.py
class CryptoDashError(Exception):
    """Base exception for all application errors."""
    pass

class AccountExistsError(CryptoDashError): ...
class InvalidCredentialsError(CryptoDashError): ...
class RateLimitedError(CryptoDashError):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Too many failed attempts. Please wait {retry_after} seconds.")

class InvalidSessionError(CryptoDashError): ...
class AddressValidationError(CryptoDashError): ...
class DuplicateWalletError(CryptoDashError): ...
class WalletLimitReachedError(CryptoDashError): ...
class TagValidationError(CryptoDashError): ...
class WalletNotFoundError(CryptoDashError): ...
class ExternalAPIError(CryptoDashError): ...
```

**Exception handler registration:**

```python
# backend/app.py
@app.exception_handler(InvalidCredentialsError)
async def handle_invalid_credentials(request, exc):
    return JSONResponse(status_code=401, content={"detail": str(exc)})

@app.exception_handler(RateLimitedError)
async def handle_rate_limited(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": str(exc)},
        headers={"Retry-After": str(exc.retry_after)},
    )

@app.exception_handler(WalletNotFoundError)
async def handle_not_found(request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})

# ... similar handlers for 400, 409 errors
```

### 7.4 Logging

**Format:**

```
2026-04-12 14:30:05.123 [INFO] backend.services.refresh: Scheduled refresh completed: 3 ok, 0 failed
```

Pattern: `{timestamp} [{level}] {logger_name}: {message}`

**What gets logged at each level:**

| Level | What |
|-------|------|
| **DEBUG** | SQL queries (only in debug mode), raw API response bodies, WebSocket connection details |
| **INFO** | App startup/shutdown, scheduler start/stop, refresh cycle start/complete, wallet added/removed, history import start/complete |
| **WARNING** | Single API call failure with retry, balance mismatch (computed vs. API), rate limit hit, partial history import, CoinGecko price = 0 |
| **ERROR** | All API calls failed in a refresh cycle, database write failure, unhandled exception in scheduler |

### 7.5 Retry and Recovery

| Operation | Retry Strategy |
|-----------|---------------|
| Balance fetch (per wallet) | 1 retry after 10 seconds (in `_get_with_retry`). On second failure: give up, use cached data. |
| Price fetch (CoinGecko) | 1 retry after 10 seconds. Fallback: Kaspa API for KAS price. On total failure: use cached prices. |
| HTTP 429 from external API | Wait `Retry-After` header seconds (or 60s default). Single retry only. |
| History import failure | No automatic retry. User can trigger via "Retry" button (`POST /api/wallets/{id}/retry-history`). |
| Database write failure | No retry. Log ERROR. Return 500 to client. |
| Scheduler cycle failure | Log ERROR. Schedule next cycle normally. |

---

## 8. Security Considerations

### 8.1 Authentication Flow (Token-Based)

**Token lifecycle:**

1. **Creation:** On successful login or account setup, server generates `secrets.token_urlsafe(32)` (256-bit entropy), stores in `sessions` table with `expires_at`.
2. **Transmission:** Server returns `{ "token": "...", "expires_at": "..." }` in the login response body. Frontend stores in `localStorage` (if "Remember me") or `sessionStorage` (default).
3. **Usage:** Frontend sends `Authorization: Bearer <token>` header on every API request.
4. **Validation:** Server looks up token in `sessions` table, checks `expires_at > now()`.
5. **Expiry:** 7 days (default) or 30 days ("Remember me"). Expired sessions are cleaned up on app startup and periodically.
6. **Invalidation:** On logout: delete session record. On password reset: delete ALL session records.

**Why tokens over cookies:**
- No CSRF vulnerability (tokens are not auto-attached by the browser).
- Simpler implementation (no cookie flags, no CSRF middleware).
- Works naturally with the SPA + `Authorization` header pattern.
- Acceptable for a self-hosted, single-user app. XSS risk is minimal.

### 8.2 Password Storage

- **Algorithm:** bcrypt via `passlib`.
- **Cost factor:** 12 (default). Produces strings like `$2b$12$<22-char-salt><31-char-hash>`.
- **Salt:** Embedded in the bcrypt output. No separate column.
- **Plaintext:** Never stored, never logged, never included in API responses.

### 8.3 Input Validation

Every point where external input enters the system:

| Entry Point | Validation Applied |
|-------------|-------------------|
| `POST /api/auth/setup` | Username: non-empty, max 50 chars. Password: min 8 chars. Confirm matches. |
| `POST /api/auth/login` | Username and password: non-empty strings. |
| `POST /api/wallets` | Network: must be "BTC" or "KAS". Address: regex validation per network rules. Tag: max 50 chars, unique. |
| `PATCH /api/wallets/{id}` | Tag: non-empty, max 50 chars, unique. Wallet ID: UUID format. |
| `DELETE /api/wallets/{id}` | Wallet ID: UUID format. Must belong to the authenticated user. |
| `PUT /api/settings` | Interval: must be 5, 15, 30, 60, or null. |
| `GET` query params (range, unit) | Enum validation: range in `{"7d", "30d", "90d", "1y", "all"}`, unit in `{"usd", "native"}`. |
| `WS /api/ws?token=...` | Token validated against session table. |

All validation is performed **server-side** by Pydantic models and service-layer checks. Client-side validation is a UX convenience only.

### 8.4 Brute-Force Protection

- **Mechanism:** In-memory counter of consecutive failed login attempts.
- **Threshold:** 5 consecutive failures.
- **Lockout:** 30-second delay before the next attempt is accepted.
- **Reset:** Counter resets to 0 on successful login.
- **Scope:** Global (single-user app — no per-IP distinction needed).
- **Persistence:** Resets on app restart (acceptable for single-user; restarting the app to bypass lockout requires server access, which already implies ability to reset the password via CLI).

### 8.5 External API Security

- All outgoing API calls use **HTTPS**.
- No API keys or secrets are transmitted (free-tier, keyless APIs).
- No sensitive data is sent to external APIs — only public wallet addresses.

### 8.6 Data Sensitivity

| Data | Sensitivity | Protection |
|------|-------------|------------|
| Password hash | High | Stored as bcrypt hash; never exposed via API. |
| Session tokens | High | 256-bit entropy; stored hashed or as-is in DB. Never logged. |
| Wallet addresses | Low (public on blockchain) | No special protection needed. |
| Balance data | Medium (reveals holdings in aggregate) | Protected behind auth. DB file should be treated as sensitive. |
| SQLite file | Medium | Filesystem permissions. No encryption in this version. |

---

## 9. Testing Strategy

### 9.1 Backend Unit Tests

| Test File | Covers | Key Scenarios |
|-----------|--------|---------------|
| `test_auth.py` | Auth router + service | Setup creates account; duplicate setup fails; login success; login invalid credentials; rate limiting after 5 failures; lockout expires; logout invalidates session; expired session rejected. |
| `test_wallets.py` | Wallet router + service | Add valid BTC/KAS wallets; address validation for all 4 BTC types + KAS; reject invalid addresses; reject duplicates (case-insensitive BTC); reject duplicate tags; default tag generation; edit tag; remove wallet cascades snapshots; wallet limit (50). |
| `test_address_validation.py` | `validate_btc_address`, `validate_kas_address` | Valid P2PKH, P2SH, Bech32, Taproot, Kaspa; invalid variants; whitespace handling; multi-line; empty; boundary lengths. |
| `test_dashboard.py` | Dashboard router | Portfolio summary with wallets; empty portfolio; USD calculations; 24h change; history data points; time range filtering. |
| `test_settings.py` | Settings router | Get default (15min); update to valid values; reject invalid interval; scheduler restarts on update. |
| `test_refresh.py` | RefreshService | Full refresh stores snapshots; partial failure (some wallets fail); concurrent refresh skipped (lock); price fetch with CoinGecko fallback; zero price rejected. |
| `test_history.py` | HistoryService | Full import stores transactions; incremental sync (new txs only); deduplication; balance_after computation; timeout handling; partial import. |
| `test_bitcoin_client.py` | BitcoinClient | Balance parsing; summary endpoint parsing; paginated fallback; UTXO parsing (inflow, outflow, mixed); coinbase transaction. |
| `test_kaspa_client.py` | KaspaClient | Balance parsing; transaction page parsing; input/output parsing; cursor pagination; rejected tx filtering. |
| `test_coingecko_client.py` | CoinGeckoClient | Current prices; historical prices; zero price detection; rate limit handling. |
| `test_scheduler.py` | Scheduler | Starts with interval; restarts on config change; disabled state; no concurrent cycles; continues after error. |
| `test_security.py` | Password hashing, token gen | bcrypt round-trip; token entropy; expired session cleanup. |

### 9.2 Backend Integration Tests

| Scenario | Description |
|----------|-------------|
| **Full user journey** | Setup account → login → add wallet → refresh → view dashboard → edit tag → remove wallet → logout. |
| **Auth enforcement** | All protected endpoints return 401 without token; login page redirect logic. |
| **Background refresh** | Start server with wallets → wait for scheduler tick → verify new snapshots stored. |
| **History import + refresh coexistence** | Add wallet (triggers import) → trigger manual refresh → both complete without conflict. |
| **Stale data resilience** | Mock all external APIs to fail → verify cached data served → verify warning messages. |

### 9.3 Frontend Tests

| Test File | Covers |
|-----------|--------|
| `WalletTable.test.ts` | Renders wallet list; sortable columns; click navigates to detail; truncated addresses. |
| `AddWalletDialog.test.ts` | Form validation (client-side); network selector; submit triggers API call; error display. |
| `TimeRangeSelector.test.ts` | Emits correct range value; active state styling. |
| `auth.test.ts` | Login flow sets token in store; logout clears token; auth guard redirects. |
| `wallets.test.ts` | Add/remove wallet updates store; optimistic UI update. |

### 9.4 Test Fixtures

```python
# tests/backend/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from backend.app import create_app
from backend.database import engine, Base, async_session

@pytest_asyncio.fixture
async def db():
    """Create a fresh in-memory database for each test."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    TestSession = async_sessionmaker(test_engine, class_=AsyncSession)
    async with TestSession() as session:
        yield session
    await test_engine.dispose()

@pytest_asyncio.fixture
async def client(db):
    """HTTP test client with dependency overrides."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest_asyncio.fixture
async def auth_client(client):
    """Authenticated test client (account created + logged in)."""
    await client.post("/api/auth/setup", json={
        "username": "testuser",
        "password": "testpassword123",
        "password_confirm": "testpassword123",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "testpassword123",
    })
    token = resp.json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client
```

### 9.5 How to Run

```bash
# Backend tests
pip install -r requirements-dev.txt
pytest tests/backend/ -v

# Frontend tests
cd frontend
npm install
npm run test

# Full suite (both)
./run-tests.sh  # convenience script
```

---

## 10. Ambiguity Resolution Log

### AR-1: Frontend framework choice

> **Spec:** OQ-5: "vue.js? vanilla js? explore possibilities" — deferred to tech spec.

**Ambiguity:** No frontend framework specified.

**Decision:** Vue 3 with TypeScript, Vite, Pinia, Chart.js, Tailwind CSS.

**Justification:** See section 1.4 for full framework evaluation. Vue 3's fine-grained reactivity is ideal for independently updating dashboard widgets. User confirmed Vue direction.

### AR-2: Backend framework choice

> **Spec:** OQ-6: "maybe FastAPI?" — deferred to tech spec.

**Ambiguity:** No backend framework specified.

**Decision:** FastAPI.

**Justification:** Async-native (needed for concurrent API calls and WebSocket), automatic OpenAPI documentation, Pydantic integration for request validation, built-in WebSocket support. The most natural choice for a Python async web app.

### AR-3: Real-time dashboard updates

> **Spec (F2, 5.2.c):** "Automatic refresh: Happens silently in the background. Dashboard updates in place when new data arrives."

**Ambiguity:** Push vs. pull mechanism for live updates not specified.

**Decision:** WebSocket for push notifications. The server broadcasts events (`refresh:completed`, `wallet:added`, etc.) and the frontend re-fetches relevant data from REST endpoints.

**Justification:** User chose WebSocket. The hybrid approach (WS for notification, REST for data) keeps the WebSocket protocol simple and the REST API as the single source of truth.

### AR-4: Authentication mechanism

> **Spec (F8, 8.c):** "Session tokens are cryptographically random. Transmitted via secure, HTTP-only cookies."

**Ambiguity:** The functional spec says cookies, but for an SPA with a separate API, token-based auth is more natural and avoids CSRF.

**Decision:** Bearer tokens in `Authorization` header. Token stored in `localStorage` (remember me) or `sessionStorage` (default session).

**Justification:** User requested token-based auth. Eliminates CSRF risk entirely. Standard pattern for SPA + API architecture. Acceptable security posture for a self-hosted, single-user application.

### AR-5: Entity IDs

> **Spec (section 6):** "id: Integer (PK) — Auto-generated."

**Ambiguity:** Auto-increment integers vs. UUIDs.

**Decision:** UUIDv4 strings.

**Justification:** Per TECH_NOTES.md recommendation. Future-proofs for multi-user. Avoids exposing entity counts in API responses. Negligible storage overhead at this scale.

### AR-6: Password hashing algorithm

> **Spec (FR-051):** "secure, salted hash"

**Ambiguity:** Which algorithm and cost factor.

**Decision:** bcrypt via `passlib` with cost factor 12 (default).

**Justification:** Per TECH_NOTES.md. bcrypt is well-audited, embeds salt in output (no separate column), and cost 12 provides ~250ms hash time — good balance of security and UX.

### AR-7: Bitcoin transaction data retrieval

> **Spec (FR-023):** "perform a one-time full retrieval of the wallet's transaction history from the blockchain API."

**Ambiguity:** Mempool.space provides full transactions (vin/vout) requiring UTXO parsing. Is there a simpler approach?

**Decision:** Use the `/address/{addr}/txs/summary` endpoint (returns signed net values per transaction, up to 5000 txs) as the primary approach. Fall back to paginated `/txs/chain` with full UTXO parsing for addresses with >5000 transactions.

**Justification:** The summary endpoint is dramatically faster and simpler for the vast majority of wallets. Full UTXO parsing is only needed for very active addresses. User confirmed: prefer simpler endpoint, fall back to full parsing.

### AR-8: Kaspa `resolve_previous_outpoints` parameter

> **Spec:** Not mentioned in functional spec.

**Ambiguity:** Whether Kaspa API returns input addresses/amounts without the resolve parameter.

**Decision:** Always pass `resolve_previous_outpoints=light` when fetching Kaspa transactions.

**Justification:** Per TECH_NOTES.md: "The `resolve_previous_outpoints=light` param is required to populate `previous_outpoint_address` and `previous_outpoint_amount` on inputs. Without it, those fields are null."

### AR-9: KAS price source

> **Spec (F3):** "Fetch current BTC/USD and KAS/USD prices from CoinGecko."

**Ambiguity:** Kaspa API also provides a price endpoint (`/info/price`). Which to use?

**Decision:** CoinGecko as primary for both BTC and KAS (single API call). Kaspa `/info/price` as fallback for KAS if CoinGecko is unavailable.

**Justification:** Per TECH_NOTES.md suggestion. CoinGecko's `/simple/price` endpoint fetches both coins in one call. Kaspa API fallback adds resilience for KAS price with no extra complexity.

### AR-10: CoinGecko historical price depth

> **Spec (FR-030):** "Retrieve historical BTC/USD and KAS/USD prices from CoinGecko."

**Ambiguity:** CoinGecko free tier limits historical data to 365 days. Wallets may have transaction history older than 1 year.

**Decision:** Fetch up to 365 days of historical prices. For dates older than 365 days, USD values display as "N/A" on charts. Balance in native coin is still shown.

**Justification:** Free-tier API constraint. The spec already accommodates this in F4 edge cases: "USD values for those dates are shown as 'N/A' on charts."

### AR-11: Decimal storage in SQLite

> **Spec (section 6):** "High precision (18 decimal places)."

**Ambiguity:** SQLite has no native DECIMAL type. REAL loses precision; TEXT is safe but requires conversion.

**Decision:** Store all monetary values as TEXT (decimal strings). Convert to `decimal.Decimal` at the repository layer.

**Justification:** Preserves full precision for BTC (8 decimals) and KAS (8 decimals) and future-proofs for higher precision. The performance cost of string↔Decimal conversion is negligible at this scale.

### AR-12: Deployment model

> **Spec (section 9):** "self-hosted web app" — no packaging details.

**Ambiguity:** How the user launches the application.

**Decision:** `./run.py` standalone script with `#!/usr/bin/env python3` shebang. No pip packaging. User clones repo, installs dependencies via `pip install -r requirements.txt` and `cd frontend && npm install && npm run build`, then runs `./run.py`.

**Justification:** User confirmed clone-and-run approach. Simpler than pip packaging for a single-user self-hosted tool.

### AR-13: History import vs. scheduled refresh concurrency

> **Spec (FR-047):** "The scheduler shall not run concurrent refresh cycles."

**Ambiguity:** Does this restriction apply to history imports? If a user adds a wallet during a scheduled refresh, or vice versa, should one block the other?

**Decision:** History imports run independently of scheduled/manual refreshes. The "no concurrent refresh" rule applies only to the refresh cycle itself (balance + price fetch). History imports are separate `asyncio.Task`s.

**Justification:** User confirmed. History imports can take minutes for large wallets — blocking refreshes for that duration would degrade the dashboard experience for all other wallets.

### AR-14: Frontend static file serving

> **Spec:** Not addressed.

**Ambiguity:** How are frontend assets served in production?

**Decision:** FastAPI mounts `frontend/dist/` as static files at `/`. A catch-all route serves `index.html` for SPA client-side routing. API routes under `/api/` take precedence.

**Justification:** Single-process deployment (one `run.py` command). No nginx or separate file server needed. Standard pattern for FastAPI + SPA.

### AR-15: Session expiry — "inactivity" vs. absolute

> **Spec (FR-056):** "Sessions shall expire after 7 days of inactivity."

**Ambiguity:** "Inactivity" implies sliding expiry (reset on each request). The data model has a fixed `expires_at` field.

**Decision:** Fixed expiry. `expires_at` is set at login time (7 or 30 days from creation) and never updated. "Inactivity" is interpreted as "since login."

**Justification:** Simpler implementation. Updating `expires_at` on every API request would add a DB write to every request. For a single-user app with daily-to-weekly usage, fixed expiry is sufficient.

### AR-16: Dark/light mode

> **Spec (NFR 8.e):** "Nice-to-have. If the chosen frontend framework supports it easily, include it."

**Decision:** Include it. Tailwind CSS supports dark mode via the `dark:` variant with minimal effort. Respect `prefers-color-scheme` media query by default, with a manual toggle in the settings panel.

**Justification:** Near-zero implementation cost with Tailwind. Improves UX for evening/night usage.

### AR-17: Kaspa address length validation

> **Spec (F1 business rules):** "the remainder must be 61 characters of lowercase alphanumeric (Bech32 charset)."

**Ambiguity:** Kaspa addresses can have remainders of 61 to 63 characters depending on the address type (P2PK vs P2SH).

**Decision:** Accept remainders of 61–63 characters.

**Justification:** The Kaspa API's own regex pattern is `^kaspa:[a-z0-9]{61,63}$`. Being too strict would reject valid addresses.

---

*End of Technical Specification.*
