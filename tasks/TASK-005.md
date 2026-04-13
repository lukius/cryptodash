# T05: Authentication — Service, Schemas, and Router

**Status**: done
**Layer**: backend
**Assignee**: developer
**Depends on**: T04

## Context

Authentication is the gateway to the entire application. It implements first-run setup, login,
logout, and session validation. Specifically: account creation (one-time), credential validation,
session lifecycle with expiry, login rate-limiting (5 failures → 30-second lockout), and a CLI
password reset. All other authenticated endpoints depend on the `get_current_user` dependency,
which depends on `AuthService.validate_session()`.

> "POST /api/auth/setup, /login, /logout; GET /api/auth/status"
> — specs/TECH_SPEC.md, Section 4.1
>
> "FR-048 through FR-060: first-run setup, login, logout, session management, rate limiting,
> password reset."
> — specs/FUNC_SPEC.md, Section 5.8

## Files owned

- `backend/schemas/auth.py` (create)
- `backend/services/auth.py` (create)
- `backend/routers/auth.py` (create)
- `backend/cli.py` (create)
- `tests/backend/test_auth.py` (create)

## Subtasks

- [ ] ST1: Implement `backend/schemas/auth.py` — `SetupRequest` (username, password min 8, password_confirm
      with `@model_validator` checking match), `LoginRequest` (username, password, remember_me bool),
      `LoginResponse` (token, expires_at ISO 8601), `AuthStatusResponse` (account_exists, authenticated,
      username | None).
- [ ] ST2: Implement `backend/services/auth.py` — `AuthService` class with:
      - `account_exists() -> bool`
      - `create_account(username, password) -> tuple[User, Session]` — raises `AccountExistsError` if user exists; hashes password; creates UUID session token; `expires_at = now + 7 days`.
      - `authenticate(username, password, remember_me) -> Session` — validates credentials, rate-limits (module-level `_failed_attempts`/`_lockout_until`); `remember_me` sets 30-day expiry.
      - `validate_session(token) -> User` — raises `InvalidSessionError` if not found or expired.
      - `invalidate_session(token) -> None`
      - `invalidate_all_sessions() -> None`
      - `reset_password(new_password) -> None` — updates hash, invalidates all sessions.
- [ ] ST3: Implement `backend/routers/auth.py` — four endpoints per spec Section 4.1.a:
      `GET /api/auth/status`, `POST /api/auth/setup` (201), `POST /api/auth/login`,
      `POST /api/auth/logout`. Register exception handlers for `AccountExistsError` (409),
      `InvalidCredentialsError` (401), `RateLimitedError` (429 + Retry-After header).
- [ ] ST4: Implement `backend/cli.py` — `reset_password()` async function: prompts for new password
      twice, validates length >= 8, calls `AuthService.reset_password()`, prints confirmation.
- [ ] ST5: Write `tests/backend/test_auth.py` — cover all edge cases from spec Section 4.1.d:
      - Setup creates account and returns token.
      - Setup returns 409 if account already exists.
      - Login with correct credentials returns token.
      - Login with wrong credentials returns 401.
      - 5 consecutive failed logins trigger 429.
      - Successful login resets the failure counter.
      - Expired session token returns 401.
      - Logout invalidates the session.
      - GET /api/auth/status returns correct `account_exists` and `authenticated` flags.

## Acceptance criteria

- [ ] `pytest tests/backend/test_auth.py -v` passes with no failures.
- [ ] FR-048: `GET /api/auth/status` returns `{"account_exists": false, ...}` on a fresh DB.
- [ ] FR-049/FR-050: `POST /api/auth/setup` with password `"short"` (< 8 chars) returns 422.
- [ ] FR-051: Password is stored as a bcrypt hash — plaintext never appears in the DB.
- [ ] FR-052: Setup response includes a valid `token` and `expires_at`.
- [ ] FR-055/FR-056: Login with `remember_me: true` produces a session expiring in 30 days; without
      it, 7 days.
- [ ] FR-059: `POST /api/auth/setup` when an account already exists returns 409.
- [ ] Login rate limit: 5th failure returns 429 with `retry_after: 30`.
- [ ] `ruff check backend/schemas/auth.py backend/services/auth.py backend/routers/auth.py` exits 0.

## Notes

- Rate-limiting state (`_failed_attempts`, `_lockout_until`) is module-level in `services/auth.py`.
  It resets on application restart — this is acceptable per spec Section 4.1.b.
- The router must NOT import exception handlers inline — register them on the FastAPI `app` in
  `backend/app.py` (T10). The router itself only raises the domain exceptions.
- Tests must use the in-memory DB fixture from `tests/backend/conftest.py` (T01).
