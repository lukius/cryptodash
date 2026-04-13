# T16: WebSocket Integration and Real-Time Updates

**Status**: done
**Layer**: frontend
**Assignee**: developer
**Depends on**: T15

## Context

The `useWebSocket` composable manages the persistent WebSocket connection to the server, handles
auto-reconnect, and dispatches events to the appropriate Pinia stores so the dashboard updates
in real-time without a page reload. This is the final frontend task — it can only be implemented
once all stores and views are in place.

> "useWebSocket.ts: WebSocket connection, auto-reconnect, event dispatch."
> — specs/TECH_SPEC.md, Section 3
>
> "WebSocket events: refresh:started/completed, wallet:added/removed/updated,
>  wallet:history:progress/completed, settings:updated."
> — specs/TECH_SPEC.md, Section 4.7

## Files owned

- `frontend/src/composables/useWebSocket.ts` (create)

## Subtasks

- [ ] ST1: Implement `frontend/src/composables/useWebSocket.ts`:
      - Accepts `token: string` parameter.
      - Connects to `WS /api/ws?token=<token>`.
      - Auto-reconnect on disconnect: exponential backoff starting at 1s, max 30s.
      - Parses incoming messages as `WebSocketEvent` (typed union from `types/websocket.ts`).
      - Dispatches events to stores:
        - `refresh:started` → set `dashboard.isRefreshing = true`.
        - `refresh:completed` → call `dashboard.fetchSummary()`, set `isRefreshing = false`.
        - `wallet:added` / `wallet:removed` / `wallet:updated` → call `wallets.fetchWallets()`.
        - `wallet:history:progress` / `wallet:history:completed` → update wallet's `history_status`
          in wallets store.
        - `settings:updated` → call `settings.fetchSettings()`.
      - Send "ping" every 30s to keep connection alive (server responds "pong").
      - Expose: `isConnected: Ref<boolean>`, `connect()`, `disconnect()`.
- [ ] ST2: Wire `useWebSocket` in `DashboardView.vue` (T14): call `connect()` on mount with the
      auth token; call `disconnect()` on unmount. This modifies `DashboardView.vue`.
      File ownership note: `DashboardView.vue` is owned by T14, so this subtask must coordinate
      with T14's implementation. Since T16 depends on T14 (done), it can modify the file.
- [ ] ST3: Write a basic unit test (in `tests/frontend/`) that mocks the WebSocket and verifies:
      - `refresh:completed` event triggers `dashboard.fetchSummary()`.
      - `wallet:added` event triggers `wallets.fetchWallets()`.
      - Auto-reconnect is attempted after disconnect.

## Files owned (full list)

- `frontend/src/composables/useWebSocket.ts` (create)
- `frontend/src/views/DashboardView.vue` (modify — add WebSocket wiring)
- `tests/frontend/composables/useWebSocket.test.ts` (create)

## Acceptance criteria

- [ ] `cd frontend && npm run test` passes WebSocket composable tests.
- [ ] `cd frontend && npm run build` succeeds.
- [ ] After a manual refresh from another browser tab, the dashboard in the first tab updates
      automatically without a page reload (manually tested with a running backend).
- [ ] After adding a wallet from the AddWalletDialog, the wallet list updates via WebSocket event
      (not just via the form response).
- [ ] WebSocket reconnects automatically after a brief server restart (observed in browser devtools
      network tab within ~5s).
- [ ] `isConnected` becomes false immediately after WebSocket disconnects, and true after
      reconnecting.

## Notes

- The WebSocket URL should be derived from the current window origin: replace `http://` with
  `ws://` and `https://` with `wss://` when constructing the URL.
- Auto-reconnect must NOT reconnect if the user is logged out (token cleared). Check
  `auth.isAuthenticated` before each reconnect attempt.
- The `ping` keepalive and auto-reconnect must be cleaned up when `disconnect()` is called or when
  the component unmounts.
- `DashboardView.vue` already exists from T14. The modification here (wiring WebSocket) is an
  additive change — add `onMounted`/`onUnmounted` hooks for WebSocket lifecycle only.
