# T15: Wallet Detail View and Settings View

**Status**: done
**Layer**: frontend
**Assignee**: developer
**Depends on**: T14

## Context

Two secondary views: (1) per-wallet detail page (balance chart for one wallet, transaction
timeline, delete wallet), and (2) configuration panel (refresh interval setting). The settings
view also implements the settings Pinia store. Both views are linked from the dashboard (wallet
table row click and gear icon respectively).

> "WalletDetailView.vue: per-wallet detail. SettingsView.vue: configuration panel."
> — specs/TECH_SPEC.md, Section 3
>
> "03-wallet-detail.html mockup is the visual source of truth for wallet detail."
> — specs/TECH_SPEC.md, Section (UI Mockups)
>
> "FR-038 through FR-042: configuration panel, refresh interval."
> — specs/FUNC_SPEC.md, Section 5.6

## Files owned

- `frontend/src/views/WalletDetailView.vue` (create)
- `frontend/src/views/SettingsView.vue` (create)
- `frontend/src/stores/settings.ts` (modify — implement fully)

## Subtasks

- [ ] ST1: Implement `frontend/src/stores/settings.ts` — Pinia store with:
      - State: `refreshIntervalMinutes: number | null`, `isLoading: boolean`, `savedMessage: string | null`.
      - Actions: `fetchSettings()`, `saveSettings(interval: number | null)` — PUT /api/settings.
      - On save success: show "Settings saved." for 3 seconds.
      - On save failure: revert to previous value + show error message.
- [ ] ST2: Implement `frontend/src/views/WalletDetailView.vue`:
      - Route param: `walletId` from `/wallet/:id`.
      - On mount: fetch wallet data from wallets store (or GET /api/wallets/{id}).
      - Show `WalletBalanceChart` (W7 reused from T14) for this wallet's history.
      - Show transaction timeline: list of transactions with date, amount (+ or -), running balance.
      - Show wallet metadata: tag (editable via `EditTagInput`), network, full address.
      - "Delete Wallet" button → opens `RemoveWalletDialog`; on confirm → delete and navigate back
        to dashboard.
      - "Retry History Import" button (shown only when `history_status === "failed"`).
      - Match visual design from `specs/mockups/03-wallet-detail.html`.
- [ ] ST3: Implement `frontend/src/views/SettingsView.vue`:
      - On mount: fetch settings from store.
      - Refresh interval control: radio buttons or dropdown with options: Disabled, 5m, 15m, 30m, 60m.
      - Current value pre-selected.
      - "Save" button. On click: call `saveSettings()`, show "Settings saved." confirmation.
      - Error state: "Could not save settings. Please try again."
      - FR-042: display current value.
      - Link back to dashboard.

## Acceptance criteria

- [ ] `cd frontend && npm run build` succeeds with no TS errors.
- [ ] FR-038: Settings view is accessible from the dashboard (gear icon in AppHeader).
- [ ] FR-039: All 5 refresh interval options are present (5m, 15m, 30m, 60m, Disabled).
- [ ] FR-040: Saved interval persists across page reload (fetched from server).
- [ ] FR-042: Currently saved interval is shown as selected in the UI.
- [ ] WalletDetailView shows the balance chart for the correct wallet (matched by route param).
- [ ] WalletDetailView shows transaction timeline with date, amount, balance.
- [ ] Delete wallet from detail view navigates back to `/`.
- [ ] "Retry History Import" button only visible when `history_status === "failed"`.
- [ ] Visual match: WalletDetailView matches `specs/mockups/03-wallet-detail.html` (inspected in browser).

## Notes

- Open `specs/mockups/03-wallet-detail.html` in a browser before implementing WalletDetailView.
- `WalletBalanceChart` is imported from the widgets directory (built in T14). Pass `walletId` and
  initial `unit` as props.
- The transaction timeline does not need its own Chart.js chart — a simple list/timeline component
  is sufficient (per mockup).
- Settings view can be a modal overlay or a dedicated page at `/settings` (already in the router
  from T11). Use the dedicated page approach for simplicity.
