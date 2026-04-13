# T12: Auth Views and Auth Store

**Status**: done
**Layer**: frontend
**Assignee**: developer
**Depends on**: T11

## Context

Implements the two authentication screens (first-run setup and login) and fills in the auth Pinia
store with real API calls. These are the entry points every user sees before the dashboard.
The router guard from T11 depends on the auth store's `checkStatus()` action being implemented
here.

> "SetupView.vue: first-run account creation. LoginView.vue: login form."
> — specs/TECH_SPEC.md, Section 3
>
> "FR-048 through FR-060: setup, login, logout, session management, rate limiting."
> — specs/FUNC_SPEC.md, Section 5.8
>
> "01-login.html mockup is the visual source of truth."
> — specs/TECH_SPEC.md, Section (UI Mockups)

## Files owned

- `frontend/src/stores/auth.ts` (modify — implement fully)
- `frontend/src/views/SetupView.vue` (create)
- `frontend/src/views/LoginView.vue` (create)
- `tests/frontend/stores/auth.test.ts` (modify — implement fully)

## Subtasks

- [ ] ST1: Implement `frontend/src/stores/auth.ts` — Pinia store with:
      - State: `token: string | null`, `username: string | null`, `accountExists: boolean`,
        `isAuthenticated: boolean`.
      - Actions: `checkStatus()` (GET /api/auth/status), `setup(username, password, passwordConfirm)`,
        `login(username, password, rememberMe)`, `logout()`.
      - Token persistence: store in `localStorage` if "remember me", else `sessionStorage`.
      - On `logout()`: clear storage, reset state, call POST /api/auth/logout.
- [ ] ST2: Implement `frontend/src/views/SetupView.vue` — form with username, password, confirm password
      fields. Password strength meter (min 8 chars indicator). "Create Account" button. Inline
      validation errors (password mismatch, too short). On success: router.push('/').
      Match visual design from `specs/mockups/01-login.html`.
- [ ] ST3: Implement `frontend/src/views/LoginView.vue` — form with username, password, "Remember me"
      checkbox, "Log In" button. On 401: show "Invalid username or password", clear password field,
      preserve username. On 429: show rate-limit message with countdown. On success: router.push('/').
      Match visual design from `specs/mockups/01-login.html`.
- [ ] ST4: Implement full `tests/frontend/stores/auth.test.ts`:
      - `checkStatus()` with account_exists=false sets correct state.
      - `login()` success stores token in sessionStorage.
      - `login()` with rememberMe=true stores token in localStorage.
      - `logout()` clears token and state.
      - `setup()` success sets isAuthenticated=true.

## Acceptance criteria

- [ ] `cd frontend && npm run test` passes all auth store tests.
- [ ] `cd frontend && npm run build` succeeds with no TS errors.
- [ ] FR-049: SetupView shows username and password fields with confirm.
- [ ] FR-050: Password < 8 chars shows inline validation error before form submission.
- [ ] FR-052: After setup, user is redirected to dashboard (manually tested).
- [ ] FR-054: LoginView has "Remember me" checkbox.
- [ ] FR-053/FR-055: Successful login redirects to dashboard.
- [ ] FR-056: `rememberMe: true` stores token in localStorage; default uses sessionStorage.
- [ ] FR-057: Logout button (in AppHeader from T11) clears session and shows login page.
- [ ] Visual match: LoginView and SetupView match `specs/mockups/01-login.html` for layout and
      color scheme (manually inspected in browser).

## Notes

- Open `specs/mockups/01-login.html` in a browser before implementing the views — it is the
  authoritative visual reference.
- The rate-limit countdown timer (FR for 429 brute-force protection from F8) should display the
  `retry_after` seconds from the response header, counting down in the UI.
- After logout, the auth store should clear all state and the router should redirect to `/login`.
  The router guard handles the redirect — logout just clears state.
