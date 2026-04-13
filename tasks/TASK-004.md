# T04: Core Infrastructure

**Status**: done
**Layer**: backend
**Assignee**: developer
**Depends on**: T03

## Context

Before any service or router can be written, the cross-cutting infrastructure must be in place:
application exception classes, password hashing and token generation utilities, FastAPI dependency
injection helpers, the WebSocket connection manager, and the Scheduler. These are consumed by
every other backend component.

> "Cross-cutting infrastructure: Scheduler, WebSocket Manager, dependencies, security helpers,
> exception classes."
> — specs/TECH_SPEC.md, Section 2.2 and Section 3

## Files owned

- `backend/core/exceptions.py` (create)
- `backend/core/security.py` (create)
- `backend/core/dependencies.py` (create)
- `backend/core/websocket_manager.py` (create)
- `backend/core/scheduler.py` (create)
- `backend/core/__init__.py` (modify — re-export public classes)
- `tests/backend/test_security.py` (create)
- `tests/backend/test_scheduler.py` (create)

## Subtasks

- [ ] ST1: Implement `backend/core/exceptions.py` — all exception classes from spec Section 7.3:
      `CryptoDashError`, `AccountExistsError`, `InvalidCredentialsError`, `RateLimitedError`
      (with `retry_after` attribute), `InvalidSessionError`, `AddressValidationError`,
      `DuplicateWalletError`, `WalletLimitReachedError`, `TagValidationError`,
      `WalletNotFoundError`, `ExternalAPIError`.
- [ ] ST2: Implement `backend/core/security.py` — `hash_password(password) -> str` and
      `verify_password(password, hash) -> bool` using passlib bcrypt (cost factor 12);
      `generate_token() -> str` using `secrets.token_urlsafe(32)`.
- [ ] ST3: Implement `backend/core/dependencies.py` — `get_db()` async generator yielding an
      `AsyncSession`; `get_auth_token()` extracting Bearer token from `Authorization` header
      (raises 401 if missing); `get_current_user()` calling `AuthService.validate_session()`
      (raises 401 on `InvalidSessionError`).
- [ ] ST4: Implement `backend/core/websocket_manager.py` — `ConnectionManager` class per spec
      Section 4.7: `connect(websocket, token)`, `disconnect(websocket)`, `broadcast(event, data)`.
      Token validation uses `AuthService.validate_session()`.
- [ ] ST5: Implement `backend/core/scheduler.py` — `Scheduler` class per spec Section 4.6:
      `start()`, `restart(interval_minutes)`, `stop()`, `_loop(interval_minutes)`. The loop
      sleeps first, then calls `refresh_service.run_full_refresh()`. On cancellation: clean stop.
      Disabled interval (None) = no loop running.
- [ ] ST6: Write `tests/backend/test_security.py` — test hash/verify round-trip, verify bcrypt
      prefix on hash output, test that `generate_token()` produces 43-character URL-safe strings.
- [ ] ST7: Write `tests/backend/test_scheduler.py` — test `start/stop` lifecycle, test that
      `restart()` with None does not start a loop, test that a running loop is cancelled on `stop()`.

## Acceptance criteria

- [ ] `pytest tests/backend/test_security.py tests/backend/test_scheduler.py -v` passes.
- [ ] `verify_password("correct", hash_password("correct"))` returns True.
- [ ] `verify_password("wrong", hash_password("correct"))` returns False.
- [ ] `hash_password("x")` output starts with `$2b$12$` (bcrypt cost 12).
- [ ] `generate_token()` returns a string of length 43 (32 bytes base64url-encoded).
- [ ] `RateLimitedError(retry_after=30).retry_after == 30` holds.
- [ ] `ruff check backend/core/` exits 0.

## Notes

- `get_db()` must use `async_session()` from `backend.database` and `yield` within a try/finally
  so the session is always closed.
- `dependencies.py` has a forward-dependency on `AuthService` (T05). Avoid circular imports by
  importing `AuthService` inside the dependency function body, not at module level.
- The `ConnectionManager` needs access to the DB to validate tokens. It should use
  `async_session()` directly (creating its own session) rather than receiving one as a parameter,
  since WebSocket connections arrive outside normal request lifecycle.
- Scheduler tests must mock `RefreshService` — do not make real API calls in unit tests.
