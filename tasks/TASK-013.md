# T13: Wallet Management Components and Wallets Store

**Status**: done
**Layer**: frontend
**Assignee**: developer
**Depends on**: T12

## Context

Implements the wallet CRUD UI components and the wallets Pinia store. The AddWalletDialog,
EditTagInput, RemoveWalletDialog, and WalletStatusBadge components implement FR-001 through FR-010
on the client side. The wallets store manages API calls for wallet CRUD and is used by WalletTable
(T14) and WalletDetailView (T15).

> "AddWalletDialog, EditTagInput, RemoveWalletDialog, WalletStatusBadge."
> — specs/TECH_SPEC.md, Section 3
>
> "FR-001 through FR-010: add/edit/remove wallets, validation, duplicate detection, limit."
> — specs/FUNC_SPEC.md, Section 5.1

## Files owned

- `frontend/src/stores/wallets.ts` (modify — implement fully)
- `frontend/src/components/wallet/AddWalletDialog.vue` (create)
- `frontend/src/components/wallet/EditTagInput.vue` (create)
- `frontend/src/components/wallet/RemoveWalletDialog.vue` (create)
- `frontend/src/components/wallet/WalletStatusBadge.vue` (create)
- `tests/frontend/stores/wallets.test.ts` (create)
- `tests/frontend/components/AddWalletDialog.test.ts` (create)

## Subtasks

- [ ] ST1: Implement `frontend/src/stores/wallets.ts` — Pinia store with:
      - State: `wallets: WalletResponse[]`, `isLoading: boolean`, `error: string | null`.
      - Actions: `fetchWallets()`, `addWallet(payload: WalletCreate) -> WalletResponse`,
        `updateTag(walletId, tag)`, `removeWallet(walletId)`.
      - Getters: `btcWallets`, `kasWallets`, `totalBtcBalance`, `totalKasBalance`, `walletCount`.
      - Error handling: parse server `{detail}` and surface as `error`.
- [ ] ST2: Implement `AddWalletDialog.vue` — modal dialog with:
      - Network selector (BTC/KAS dropdown).
      - Address input with client-side validation on blur (using `utils/validation.ts`).
      - Tag input (optional, shows placeholder with default tag preview).
      - "Add" and "Cancel" buttons. Loading state during submission.
      - Show wallet limit message (FR-009) when `walletCount >= 50`.
      - Inline error messages from server (duplicate address, duplicate tag, invalid format).
      - Per mockup in `specs/mockups/02-dashboard.html`.
- [ ] ST3: Implement `EditTagInput.vue` — inline editable text field:
      - Shows tag as text normally; becomes an `<input>` on click.
      - Confirm on Enter key or blur, cancel on Escape.
      - Inline error if tag already exists (from server 400).
- [ ] ST4: Implement `RemoveWalletDialog.vue` — confirmation modal:
      - Shows message: "Remove '{tag}'? All historical data for this wallet will be deleted."
      - "Confirm" and "Cancel" buttons (FR-008).
- [ ] ST5: Implement `WalletStatusBadge.vue` — small indicator component:
      - Renders appropriate icon/badge for `history_status`: "importing" (spinner), "failed" (warning
        icon + tooltip), "pending" (clock icon), "complete" (nothing or checkmark).
      - Shows warning tooltip if `warning` field is set on the wallet.
- [ ] ST6: Write `tests/frontend/stores/wallets.test.ts`:
      - `fetchWallets()` populates the store.
      - `addWallet()` appends to the list on success.
      - `removeWallet()` removes the wallet from the list.
      - `totalBtcBalance` getter sums BTC wallets only.
- [ ] ST7: Write `tests/frontend/components/AddWalletDialog.test.ts`:
      - Form submission with empty address shows validation error.
      - Form submission with invalid BTC address shows correct error message.
      - Cancel button emits `close` event.
      - Loading state disables the "Add" button.

## Acceptance criteria

- [ ] `cd frontend && npm run test` passes all wallet store and AddWalletDialog tests.
- [ ] `cd frontend && npm run build` succeeds.
- [ ] FR-002: AddWalletDialog shows inline validation error for invalid address (no submit).
- [ ] FR-003: After adding a duplicate, dialog shows "This wallet address is already being tracked."
- [ ] FR-008: RemoveWalletDialog shows confirmation message with wallet tag name.
- [ ] FR-009: "Add Wallet" button is visually disabled and shows limit message at 50 wallets.
- [ ] EditTagInput: pressing Escape reverts the tag to its original value.
- [ ] WalletStatusBadge: "importing" status shows a spinner.
- [ ] Visual design matches `specs/mockups/02-dashboard.html` add-wallet modal (inspected in browser).

## Notes

- Client-side validation in AddWalletDialog is a UX aid only — the server also validates. Both
  validations must use the same rules (from `utils/validation.ts`).
- `WalletStatusBadge` maps `history_status` from the API: "importing" means a background import is
  running; "failed" means it failed; "pending" means not yet started; "complete" means done.
- The `wallets` store interacts with the `useWebSocket` composable (T16) to react to
  `wallet:added`, `wallet:removed`, and `wallet:updated` events. Leave hooks for this in the store;
  T16 will wire them.
