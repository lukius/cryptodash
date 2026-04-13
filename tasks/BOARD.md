# Task Board

Last updated: 2026-04-13

| ID   | Title                                          | Layer      | Status | Assignee  | Depends on       | Files owned (key files)                                                                                         |
|------|------------------------------------------------|------------|--------|-----------|------------------|-----------------------------------------------------------------------------------------------------------------|
| T01  | Backend Project Scaffolding                    | backend    | done   | developer | —                | backend/__init__.py, backend/config.py, backend/database.py, alembic.ini, run.py, requirements-dev.txt, tests/backend/conftest.py, CLAUDE.md |
| T02  | Database Models and Initial Migration          | backend    | done   | developer | T01              | backend/models/*.py, backend/migrations/versions/001_initial_schema.py, tests/backend/test_models.py           |
| T03  | Repository Layer                               | backend    | done   | developer | T02 ✓            | backend/repositories/*.py, tests/backend/test_repositories.py                                                  |
| T04  | Core Infrastructure                            | backend    | done   | developer | T03 ✓            | backend/core/exceptions.py, backend/core/security.py, backend/core/dependencies.py, backend/core/websocket_manager.py, backend/core/scheduler.py, tests/backend/test_security.py, tests/backend/test_scheduler.py |
| T05  | Authentication — Service, Schemas, Router      | backend    | done   | developer | T04 ✓            | backend/schemas/auth.py, backend/services/auth.py, backend/routers/auth.py, backend/cli.py, tests/backend/test_auth.py |
| T06  | External API Clients                           | backend    | done   | developer | T01              | backend/clients/base.py, backend/clients/bitcoin.py, backend/clients/kaspa.py, backend/clients/coingecko.py, tests/backend/test_*_client.py |
| T07  | Wallet Management — Service, Schemas, Router   | backend    | done   | developer | T05 ✓            | backend/schemas/wallet.py, backend/services/wallet.py, backend/routers/wallets.py, tests/backend/test_wallets.py, tests/backend/test_address_validation.py |
| T08  | History Service                                | backend    | done   | developer | T06 ✓, T07 ✓     | backend/services/history.py, tests/backend/test_history.py                                                     |
| T09  | Refresh Service, Dashboard Router, Settings Router | backend | done  | developer | T08 ✓            | backend/services/refresh.py, backend/schemas/dashboard.py, backend/schemas/settings.py, backend/routers/dashboard.py, backend/routers/settings.py, backend/routers/websocket.py, tests/backend/test_refresh.py, tests/backend/test_dashboard.py, tests/backend/test_settings.py |
| T10  | Application Factory and Entry Point            | backend    | done   | developer | T09 ✓            | backend/app.py, run.py (modify), CLAUDE.md (modify)                                                            |
| T11  | Frontend Foundation                            | frontend   | done   | developer | T01              | frontend/src/main.ts, frontend/src/App.vue, frontend/src/router/index.ts, frontend/src/composables/useApi.ts, frontend/src/types/*.ts, frontend/src/utils/*.ts, frontend/src/components/common/*.vue, frontend/src/components/layout/*.vue, frontend/src/stores/*.ts (shells), tests/frontend/setup.ts |
| T12  | Auth Views and Auth Store                      | frontend   | done   | developer | T11 ✓            | frontend/src/stores/auth.ts, frontend/src/views/SetupView.vue, frontend/src/views/LoginView.vue, tests/frontend/stores/auth.test.ts |
| T13  | Wallet Management Components and Wallets Store | frontend   | done   | developer | T12 ✓            | frontend/src/stores/wallets.ts, frontend/src/components/wallet/*.vue, tests/frontend/stores/wallets.test.ts, tests/frontend/components/AddWalletDialog.test.ts |
| T14  | Dashboard View and Widgets                     | frontend   | done   | developer | T13 ✓            | frontend/src/stores/dashboard.ts, frontend/src/views/DashboardView.vue, frontend/src/components/widgets/*.vue, tests/frontend/components/WalletTable.test.ts |
| T15  | Wallet Detail View and Settings View           | frontend   | done   | developer | T14 ✓            | frontend/src/views/WalletDetailView.vue, frontend/src/views/SettingsView.vue, frontend/src/stores/settings.ts  |
| T16  | WebSocket Integration and Real-Time Updates    | frontend   | done   | developer | T15 ✓            | frontend/src/composables/useWebSocket.ts, frontend/src/views/DashboardView.vue (modify), tests/frontend/composables/useWebSocket.test.ts |

---

## Dependency Graph

```
T01 ──┬──► T02 ──► T03 ──► T04 ──► T05 ──► T07 ──► T08 ──► T09 ──► T10
      │                                                                    
      └──► T06 ──────────────────────────────► T08
      │                                              
      └──► T11 ──► T12 ──► T13 ──► T14 ──► T15 ──► T16
```

**Parallelism opportunities:**
- T06 (API clients) can run in parallel with T02–T05 (backend models/repos/services).
- T11 (frontend foundation) can run in parallel with T02–T10 (all backend work).
- All frontend tasks (T11–T16) are independent of all backend tasks in terms of file ownership.

---

## Overlap Analysis

No two tasks with overlapping file ownership are schedulable concurrently:

- `CLAUDE.md`: T01 (initial update) → T10 (finalize). Serialized via T01→...→T10 chain.
- `run.py`: T01 (create stub) → T10 (finalize). Serialized.
- `backend/models/__init__.py`: T02 only.
- `backend/repositories/__init__.py`: T03 only.
- `backend/core/__init__.py`: T04 only.
- `frontend/src/views/DashboardView.vue`: T14 (create) → T16 (modify). Serialized via T14→T15→T16.
- `frontend/src/stores/*.ts`: Each store is owned by exactly one task (auth: T12, wallets: T13, dashboard: T14, settings: T15). T11 creates shell files which are then fully implemented in the respective tasks — no concurrent writes.
- Alembic migrations: only T02 creates a migration in this cycle.

---

## QA Cycle — 2026-04-13

QA testing completed. Three bugs found and fixed directly (no new tasks required — all fixes touched files already owned by existing done tasks).

| Bug | Severity | File(s) | Fix | Task |
|-----|----------|---------|-----|------|
| BUG-001 | CRITICAL | `backend/services/wallet.py` lines 116/119 | `price_snap.price` → `price_snap.price_usd`. `GET /api/wallets/` was returning 500 after any refresh cycle. | T07 |
| BUG-002 | HIGH | `backend/database.py` | Added `connect_args={"timeout": 30}` to `create_async_engine`. SQLite was failing with "database is locked" when background history imports and refresh ran concurrently. | T01 |
| BUG-003 | MEDIUM | `backend/services/wallet.py` line 76, `tests/backend/test_address_validation.py` | Kaspa validation minimum changed 61 → 60 chars (real Kaspa payloads are 60 chars). Test updated accordingly (1 new test added). | T07 |

All 332 backend tests pass after fixes.

---

## Spec Coverage Reference

| Spec Feature | Tasks |
|-------------|-------|
| F1: Wallet Management | T07, T13 |
| F2: Balance Retrieval | T06, T08, T09 |
| F3: Price Retrieval | T06, T09 |
| F4: Historical Data | T08 |
| F5: Dashboard | T09, T14 |
| F6: Configuration Panel | T09, T15 |
| F7: Background Scheduler | T04, T09, T10 |
| F8: Authentication | T05, T12 |
| Data models (Section 5) | T02, T03 |
| External API clients (Section 4.3) | T06 |
| WebSocket (Section 4.7) | T09, T16 |
| CLI / entry point (Section 6) | T05, T10 |
