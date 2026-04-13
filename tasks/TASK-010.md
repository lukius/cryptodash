# T10: Application Factory and Entry Point

**Status**: todo
**Layer**: backend
**Assignee**: developer
**Depends on**: T09

## Context

This task wires all backend components together into a runnable application. It implements the
FastAPI app factory with lifespan (startup/shutdown), registers all routers and exception handlers,
mounts the static frontend build, and finalizes `run.py` for production startup. It also updates
CLAUDE.md with the final run/test commands. This is the last backend task.

> "create_app() factory, lifespan, middleware, static mount."
> — specs/TECH_SPEC.md, Section 3 (Project Structure)
>
> "Startup sequence: init_db → seed config → create clients → WebSocket manager → RefreshService
>  → Scheduler → mount routers → mount static files."
> — specs/TECH_SPEC.md, Section 6.3

## Files owned

- `backend/app.py` (create)
- `run.py` (modify — finalize from T01 stub)
- `CLAUDE.md` (modify — finalize Build/Run/Test/Lint commands)

## Subtasks

- [ ] ST1: Implement `backend/app.py` — `create_app() -> FastAPI`:
      - Define `lifespan` context manager: `init_db()`, seed default config, instantiate all
        clients (BTC, Kaspa, CoinGecko), `ConnectionManager`, `RefreshService`, `HistoryService`,
        `Scheduler`; call `scheduler.start()`; clean up expired sessions; yield; shutdown sequence
        (stop scheduler, close clients).
      - Register exception handlers for all `CryptoDashError` subclasses → appropriate HTTP codes.
      - Include all routers (auth, wallets, dashboard, settings, websocket) under appropriate prefixes.
      - Mount `frontend/dist/` as static files at `/` with HTML fallback for SPA routing.
      - Configure CORS if needed (for local dev with Vite dev server on a different port).
- [ ] ST2: Finalize `run.py`:
      - Python 3.11 version check.
      - Ensure `data/` directory exists.
      - Dispatch `reset-password` CLI command if `sys.argv[1] == "reset-password"`.
      - Start uvicorn with `backend.app:create_app` factory mode.
- [ ] ST3: Update `CLAUDE.md`:
      - Build: `cd frontend && npm run build`
      - Run: `python run.py`
      - Test: `pytest tests/backend/ -v` and `cd frontend && npm run test`
      - Lint: `ruff check backend/` and `cd frontend && npm run lint`
- [ ] ST4: Run the full backend test suite as a smoke check: `pytest tests/backend/ -v`. Fix any
      import or wiring issues surfaced by this integration.

## Acceptance criteria

- [ ] `python run.py` starts the server without error (requires a built frontend, or the static
      mount handles the missing directory gracefully).
- [ ] `GET /api/auth/status` returns 200 from the running server.
- [ ] `pytest tests/backend/ -v` passes with no failures (full suite smoke check).
- [ ] All routers accessible at correct prefixes: `/api/auth/*`, `/api/wallets/*`,
      `/api/dashboard/*`, `/api/settings`, `/api/ws`.
- [ ] Exception handlers correctly convert `InvalidCredentialsError` → 401, `WalletNotFoundError`
      → 404, `RateLimitedError` → 429, `AccountExistsError` → 409.
- [ ] `ruff check backend/app.py` exits 0.

## Notes

- The static files mount must use `html=True` on `StaticFiles` to enable SPA fallback (returning
  `index.html` for unmatched routes). This is required for Vue Router's history mode.
- During development (before frontend build), the server should not crash — handle the case where
  `frontend/dist/` does not exist (skip the mount or serve an info page).
- All `app.state.*` references in routers (e.g., `request.app.state.scheduler` in the settings
  router) are initialized here in lifespan. This is the single source of truth for shared singletons.
