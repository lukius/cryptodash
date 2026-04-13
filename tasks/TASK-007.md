# T07: Wallet Management — Service, Schemas, and Router

**Status**: done
**Layer**: backend
**Assignee**: developer
**Depends on**: T05

## Context

Wallet management is the foundational user-facing feature. It implements address validation, CRUD
for wallets, tag uniqueness enforcement, duplicate detection, the 50-wallet limit, default tag
generation, and the trigger that spawns background balance and history imports. The router depends
on `get_current_user` (T04/T05). The wallet service depends on repositories (T03) and will call
into RefreshService and HistoryService (T08/T09) for the background fetch — those are injected as
dependencies and can be stubbed for tests.

> "FR-001 through FR-010: add/remove/edit wallets, address validation, duplicate detection, limit."
> — specs/FUNC_SPEC.md, Section 5.1
>
> "Router: GET/POST /api/wallets, PATCH/DELETE /api/wallets/{id}, POST /{id}/retry-history"
> — specs/TECH_SPEC.md, Section 4.2.a

## Files owned

- `backend/schemas/wallet.py` (create)
- `backend/services/wallet.py` (create)
- `backend/routers/wallets.py` (create)
- `tests/backend/test_wallets.py` (create)
- `tests/backend/test_address_validation.py` (create)

## Subtasks

- [ ] ST1: Implement `backend/schemas/wallet.py` — `WalletCreate`, `WalletTagUpdate`, `WalletResponse`,
      `WalletListResponse` per spec Section 5.3.
- [ ] ST2: Implement address validation functions `validate_btc_address(address) -> str | None` and
      `validate_kas_address(address) -> str | None` in `backend/services/wallet.py` per spec Section
      4.2.b (exact regex rules for P2PKH, P2SH, Bech32 SegWit v0, Bech32m Taproot, Kaspa Bech32).
- [ ] ST3: Implement `WalletService` with: `add_wallet(network, address, tag) -> Wallet` (full
      pipeline: limit check, normalize, validate, duplicate check, tag handling, persist, spawn
      background `asyncio.create_task` for balance + history); `update_tag(wallet_id, new_tag) -> Wallet`;
      `remove_wallet(wallet_id)`.
- [ ] ST4: Implement `backend/routers/wallets.py` — five endpoints per spec Section 4.2.a:
      `GET /api/wallets/`, `POST /api/wallets/`, `PATCH /api/wallets/{id}`,
      `DELETE /api/wallets/{id}`, `POST /api/wallets/{id}/retry-history`.
      All routes require `get_current_user`. Map `WalletLimitReachedError` → 409,
      `AddressValidationError`/`DuplicateWalletError`/`TagValidationError` → 400,
      `WalletNotFoundError` → 404.
- [ ] ST5: Write `tests/backend/test_address_validation.py` — exhaustive test of all valid/invalid
      address formats per spec Section 5.1.d:
      - BTC P2PKH (starts "1"), P2SH (starts "3"), Bech32 SegWit (bc1q, 42 and 62 chars),
        Bech32m Taproot (bc1p, 62 chars). Both valid examples and invalid (wrong length, bad chars,
        mixed case Bech32).
      - KAS valid (starts "kaspa:", 61-char remainder), invalid (wrong prefix, wrong length,
        invalid chars).
      - Whitespace/newline stripping.
- [ ] ST6: Write `tests/backend/test_wallets.py` — test all edge cases from spec Section 4.2.d:
      whitespace trimming, empty address, wallet limit (50), duplicate detection (including BTC
      case-insensitive), long tag, duplicate tag, successful add/remove/update, remove cascades
      snapshots.

## Acceptance criteria

- [ ] `pytest tests/backend/test_wallets.py tests/backend/test_address_validation.py -v` passes.
- [ ] FR-002: Invalid BTC address returns 400 with "Invalid Bitcoin address format."
- [ ] FR-003: Duplicate wallet returns 400 with "This wallet address is already being tracked."
- [ ] FR-005: Adding wallet with no tag assigns default "BTC Wallet #1" (or next available).
- [ ] FR-007: DELETE wallet returns 204; subsequent GET returns empty list.
- [ ] FR-009: Adding a 51st wallet returns 409.
- [ ] FR-010: GET /api/wallets/ returns all wallets with balance and USD fields.
- [ ] BTC address case-insensitive duplicate detection works (same address in different case is
      rejected).
- [ ] `ruff check backend/schemas/wallet.py backend/services/wallet.py backend/routers/wallets.py` exits 0.

## Notes

- `add_wallet` spawns background tasks via `asyncio.create_task(self._fetch_initial_data(wallet))`.
  The background task must catch all exceptions so a failure does not affect the HTTP response.
- `WalletService` takes `RefreshService` and `HistoryService` as constructor arguments (injected).
  In tests, pass in stubs/mocks.
- The `GET /api/wallets/` endpoint must join the latest `BalanceSnapshot` and `PriceSnapshot` to
  compute `balance` and `balance_usd` fields. Use the `BalanceSnapshotRepository.get_latest_for_wallet`
  and `PriceSnapshotRepository.get_latest` methods (T03).
