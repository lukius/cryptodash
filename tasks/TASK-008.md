# T08: History Service

**Status**: done
**Layer**: backend
**Assignee**: developer
**Depends on**: T06, T07

## Context

The history service orchestrates two workflows: (1) a one-time full transaction import when a wallet
is first added, and (2) an incremental sync on every refresh cycle. It fetches raw transactions from
the API clients (T06), deduplicates against the local DB, reconstructs daily historical balances,
fetches historical prices from CoinGecko, and broadcasts progress events via WebSocket. This task
depends on T07 (needs Wallet model and wallet service patterns) and T06 (API clients).

> "HistoryService: full_import + incremental_sync."
> — specs/TECH_SPEC.md, Section 4.5
>
> "FR-023 through FR-030: one-time full retrieval, local storage, balance reconstruction,
> incremental sync, no re-fetching of stored transactions."
> — specs/FUNC_SPEC.md, Section 5.4

## Files owned

- `backend/services/history.py` (create)
- `tests/backend/test_history.py` (create)

## Subtasks

- [ ] ST1: Implement `HistoryService.__init__` — accepts `db: AsyncSession`, `btc_client`,
      `kas_client`, `coingecko_client`, `ws_manager`.
- [ ] ST2: Implement `full_import(wallet) -> HistoryImportResult`:
      - Broadcast `wallet:history:progress` with status "started".
      - Fetch all transactions via appropriate client.
      - Deduplicate by `tx_hash` using `TransactionRepository.exists_by_hash()`.
      - Build `Transaction` records with signed `amount` and running `balance_after`.
      - Batch-insert in chunks of 500.
      - Compute daily end-of-day balances and store as `BalanceSnapshot(source="historical")`.
      - Fetch historical prices via `CoinGeckoClient.get_price_history()` and store as
        `PriceSnapshot` records (deduplicate by coin+timestamp).
      - Broadcast `wallet:history:completed`.
      - Wrap the whole operation in `asyncio.wait_for(..., timeout=300)` — on timeout, log warning,
        broadcast partial completion, return `HistoryImportResult(partial=True)`.
- [ ] ST3: Implement `incremental_sync(wallet) -> int`:
      - Find the most recent stored transaction via `TransactionRepository.get_latest_for_wallet()`.
      - For BTC: paginate `btc_client.get_transactions_paginated()` newest-first, stop when we
        encounter a `txid` already stored.
      - For KAS: use `kas_client.get_transactions_page()` with cursor after last stored timestamp.
      - Store new transactions, updating `balance_after`.
      - If new transactions found, store a new `BalanceSnapshot(source="live")`.
      - Return count of new transactions stored.
- [ ] ST4: Write `tests/backend/test_history.py` — mock API clients and WebSocket manager; test:
      - `full_import` with 3 transactions stores them, computes correct daily balances.
      - `full_import` deduplicates: re-running with same transactions does not create duplicates.
      - `full_import` timeout: if import takes > 300s, returns `partial=True`.
      - `incremental_sync` with 2 new transactions: stores them, creates a new live snapshot.
      - `incremental_sync` with no new transactions: no DB writes, returns 0.
      - `incremental_sync` stops when it encounters an already-stored tx_hash (BTC path).

## Acceptance criteria

- [ ] `pytest tests/backend/test_history.py -v` passes with no failures.
- [ ] FR-024: Transactions are stored with wallet_id, tx_hash, signed amount, timestamp.
- [ ] FR-025: Daily end-of-day balances are stored as `BalanceSnapshot(source="historical")`.
- [ ] FR-026: Incremental sync only fetches transactions newer than the most recent stored one.
- [ ] FR-027: Re-running `full_import` on an already-imported wallet does not create duplicate
      transaction records.
- [ ] FR-028: `balance_after` running total is computed correctly during import.
- [ ] Timeout test: `full_import` with `asyncio.wait_for` raises `TimeoutError` when mocked import
      exceeds 300s, and the partial result is returned.
- [ ] `ruff check backend/services/history.py` exits 0.

## Notes

- Daily balance computation: sort transactions by timestamp ASC, track running total, emit one
  `BalanceSnapshot` per calendar day (the end-of-day value after all that day's transactions).
- For the BTC incremental sync, stop condition is: when the page contains a txid already in DB,
  discard that txid and all older ones on the page, then stop paginating.
- Historical price fetching for the initial import: call `coingecko_client.get_price_history()`
  for the full range from the wallet's earliest transaction to today. Store each daily price as a
  `PriceSnapshot`. Use `INSERT OR IGNORE` semantics to avoid duplicates with existing prices.
