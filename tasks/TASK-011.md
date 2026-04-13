# T11: Frontend Foundation

**Status**: done
**Layer**: frontend
**Assignee**: developer
**Depends on**: T01

## Context

The frontend skeleton (Vite + Vue scaffold) needs to be replaced with the real application
structure: router setup with auth navigation guards, Pinia store shells, the `useApi` composable,
TypeScript types for all API responses, utility functions for formatting and address validation,
and the `App.vue`/`main.ts` bootstrap. This is the prerequisite for all frontend feature tasks
(T12–T16) — nothing can be built until the composables, types, and router are in place.

> "Vue 3 SPA: Views, Stores, Composables, Router."
> — specs/TECH_SPEC.md, Section 2.1
>
> "Frontend file structure: router/index.ts, stores/*.ts, composables/*.ts, types/*.ts, utils/*.ts"
> — specs/TECH_SPEC.md, Section 3

## Files owned

- `frontend/src/main.ts` (modify — add Pinia + vue-router)
- `frontend/src/App.vue` (modify — replace HelloWorld with RouterView)
- `frontend/src/router/index.ts` (create)
- `frontend/src/stores/auth.ts` (create — shell, filled in T12)
- `frontend/src/stores/dashboard.ts` (create — shell, filled in T14)
- `frontend/src/stores/wallets.ts` (create — shell, filled in T13)
- `frontend/src/stores/settings.ts` (create — shell, filled in T15)
- `frontend/src/composables/useApi.ts` (create)
- `frontend/src/types/api.ts` (create)
- `frontend/src/types/websocket.ts` (create)
- `frontend/src/utils/format.ts` (create)
- `frontend/src/utils/validation.ts` (create)
- `frontend/src/components/common/LoadingSpinner.vue` (create)
- `frontend/src/components/common/EmptyState.vue` (create)
- `frontend/src/components/common/TimeRangeSelector.vue` (create)
- `frontend/src/components/layout/AppHeader.vue` (create)
- `frontend/src/components/layout/AppFooter.vue` (create)
- `frontend/src/style.css` (modify — replace Vite defaults with Tailwind directives)
- `frontend/src/env.d.ts` (modify if needed)
- `tests/frontend/setup.ts` (create)
- `tests/frontend/stores/auth.test.ts` (create — shell, tested in T12)

## Subtasks

- [ ] ST1: Modify `frontend/src/main.ts` — create app, install Pinia and vue-router, mount.
- [ ] ST2: Replace `frontend/src/App.vue` with `<RouterView />` (no HelloWorld).
- [ ] ST3: Implement `frontend/src/router/index.ts` — define routes:
      `/setup` → SetupView, `/login` → LoginView, `/` → DashboardView, `/wallet/:id` →
      WalletDetailView, `/settings` → SettingsView. Add navigation guard: check auth status;
      redirect unauthenticated users to `/login`; redirect authenticated users away from `/login`
      and `/setup`; handle first-run (no account) by redirecting to `/setup`.
- [ ] ST4: Implement `frontend/src/composables/useApi.ts` — typed fetch wrapper using `fetch()`:
      base URL from `import.meta.env.VITE_API_BASE` (default `/api`), attaches
      `Authorization: Bearer <token>` from auth store, handles 401 → redirect to login,
      typed `get<T>()`, `post<T>()`, `patch<T>()`, `put<T>()`, `delete<T>()`.
- [ ] ST5: Implement `frontend/src/types/api.ts` — TypeScript interfaces for all API response shapes
      per spec Section 5.3: `WalletResponse`, `WalletListResponse`, `PortfolioSummary`,
      `PortfolioHistoryResponse`, `WalletHistoryResponse`, `PriceHistoryResponse`,
      `PortfolioComposition`, `SettingsResponse`, `AuthStatusResponse`, `LoginResponse`.
- [ ] ST6: Implement `frontend/src/types/websocket.ts` — `WebSocketEvent` discriminated union type
      covering all events from spec Section 4.7: `refresh:started`, `refresh:completed`,
      `wallet:added`, `wallet:removed`, `wallet:updated`, `wallet:history:progress`,
      `wallet:history:completed`, `settings:updated`.
- [ ] ST7: Implement `frontend/src/utils/format.ts` — `formatUsd(value)`, `formatBtc(value)`,
      `formatKas(value)`, `formatPercent(value)`, `formatTimestamp(iso)`,
      `truncateAddress(address, start=6, end=4)`. USD to 2dp, BTC to 8dp, KAS to 2dp, thousands
      separators. Return "N/A" for null/undefined inputs.
- [ ] ST8: Implement `frontend/src/utils/validation.ts` — client-side mirrors of server address
      validation per spec Section 5.1.d (same regex rules as `backend/services/wallet.py`).
- [ ] ST9: Replace `frontend/src/style.css` with Tailwind CSS directives (`@tailwind base/components/utilities`).
- [ ] ST10: Implement `LoadingSpinner.vue`, `EmptyState.vue` (accepts message prop), `TimeRangeSelector.vue`
       (emits selected range: "7d"|"30d"|"90d"|"1y"|"all"; default "30d"), `AppHeader.vue`
       (logo, refresh button, settings icon, logout), `AppFooter.vue` (last-updated timestamp).
- [ ] ST11: Create `tests/frontend/setup.ts` — Vitest global setup.
- [ ] ST12: Write `tests/frontend/stores/auth.test.ts` shell (expanded in T12) and
       `tests/frontend/components/TimeRangeSelector.test.ts` — test that all 5 range options emit
       correct values and the default is "30d".

## Acceptance criteria

- [ ] `cd frontend && npm run build` succeeds with no TypeScript errors.
- [ ] `cd frontend && npm run lint` exits 0.
- [ ] `cd frontend && npm run test` passes (TimeRangeSelector tests).
- [ ] Navigating to `http://localhost:5173/` in the browser redirects to `/setup` (when no account)
      or `/login` (when account exists) — manually verified after `npm run dev`.
- [ ] `formatUsd("12345.6789")` returns `"$12,345.68"`.
- [ ] `formatBtc("0.00000001")` returns `"0.00000001 BTC"`.
- [ ] `truncateAddress("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", 6, 4)` returns `"bc1qar...mdq"`.

## Notes

- Store shells (auth.ts, wallets.ts, dashboard.ts, settings.ts) should only define the Pinia store
  with empty/stub state and action stubs — full implementation follows in T12–T15. This allows the
  router guard and App.vue to import them without errors.
- `useApi.ts` should NOT use Axios — use the native `fetch()` API per the spec's intent (no Axios
  in the dependency list).
- The router auth guard calls `GET /api/auth/status` to determine the initial state. This should
  only happen once per app load — store the result in the auth store.
