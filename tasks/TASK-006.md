# T06: External API Clients

**Status**: done
**Layer**: backend
**Assignee**: developer
**Depends on**: T01

## Context

Three external API clients fetch blockchain and price data. They are pure I/O adapters — no
business logic, no DB access. They are isolated behind a typed interface so the provider can be
swapped (e.g., Mempool.space → Blockchair for BTC). This task can run in parallel with T02–T05
because clients do not depend on models or repositories.

> "Bitcoin Client: Mempool.space endpoints. Kaspa Client: api.kaspa.org. CoinGecko Client:
> price endpoints."
> — specs/TECH_SPEC.md, Section 4.3

## Files owned

- `backend/clients/base.py` (create)
- `backend/clients/bitcoin.py` (create)
- `backend/clients/kaspa.py` (create)
- `backend/clients/coingecko.py` (create)
- `backend/clients/__init__.py` (modify — re-export client classes)
- `tests/backend/test_bitcoin_client.py` (create)
- `tests/backend/test_kaspa_client.py` (create)
- `tests/backend/test_coingecko_client.py` (create)

## Subtasks

- [ ] ST1: Implement `backend/clients/base.py` — `BaseClient` with `httpx.AsyncClient`, `_get()`,
      `_get_with_retry()` (single retry after 10s), `close()`. Per spec Section 4.3.a.
- [ ] ST2: Implement `backend/clients/bitcoin.py` — `BitcoinClient(BaseClient)`:
      `get_balance(address) -> Decimal`, `get_transaction_summary(address) -> list[dict]`,
      `get_transactions_paginated(address, after_txid) -> list[dict]`,
      `get_all_transactions(address) -> list[dict]` (summary-first, UTXO fallback),
      `_fetch_all_with_utxo_parsing(address) -> list[dict]`. Per spec Section 4.3.b.
- [ ] ST3: Implement `backend/clients/kaspa.py` — `KaspaClient(BaseClient)`:
      `get_balance(address) -> Decimal`, `get_price_usd() -> Decimal`,
      `get_transaction_count(address) -> int`,
      `get_transactions_page(address, limit, before) -> tuple[list[dict], int | None]`,
      `get_all_transactions(address) -> list[dict]`. Per spec Section 4.3.c.
- [ ] ST4: Implement `backend/clients/coingecko.py` — `CoinGeckoClient(BaseClient)`:
      `get_current_prices() -> dict[str, Decimal]`, `get_price_history(network, days) -> list`,
      `get_price_at_date_range(network, from_ts, to_ts) -> list`. Per spec Section 4.3.d.
- [ ] ST5: Write `tests/backend/test_bitcoin_client.py` — mock `httpx.AsyncClient` responses; test:
      `get_balance` satoshi conversion, `get_all_transactions` summary-path happy path,
      `get_all_transactions` fallback-to-UTXO-parsing when total_txs > summary count,
      HTTP 429 triggers retry logic, HTTP 5xx raises, `is_coinbase=true` transactions handled.
- [ ] ST6: Write `tests/backend/test_kaspa_client.py` — mock responses; test: `get_balance` sompi
      conversion, `get_all_transactions` cursor pagination, `is_accepted=false` txs are skipped,
      cursor exhaustion halts pagination.
- [ ] ST7: Write `tests/backend/test_coingecko_client.py` — mock responses; test: `get_current_prices`
      parses BTC and KAS correctly, price=0 is returned as-is (caller handles zero check),
      `get_price_history` respects `MAX_HISTORY_DAYS=365` cap.

## Acceptance criteria

- [ ] `pytest tests/backend/test_bitcoin_client.py tests/backend/test_kaspa_client.py tests/backend/test_coingecko_client.py -v` passes.
- [ ] BTC balance conversion: `(funded_txo_sum - spent_txo_sum) / 10^8` = correct BTC decimal.
- [ ] KAS balance conversion: `sompi / 10^8` = correct KAS decimal.
- [ ] `_get_with_retry` makes exactly two HTTP calls when the first fails and succeeds on retry.
- [ ] Kaspa `is_accepted=false` transactions are excluded from `get_all_transactions` output.
- [ ] BTC `get_all_transactions` uses summary path when total_txs ≤ 5000.
- [ ] BTC `get_all_transactions` falls back to UTXO-parsing when total_txs > summary count.
- [ ] `ruff check backend/clients/` exits 0.

## Acceptance criteria (edge cases)

Per spec Section 4.3.e:
- [ ] HTTP 429: `_get_with_retry` logs warning, waits `Retry-After` (or 60s), retries once.
- [ ] HTTP 5xx: `_get_with_retry` raises `httpx.HTTPStatusError` to the caller.
- [ ] CoinGecko price=0: returned to caller without error; caller (PriceService) handles the
      zero-price guard.

## Notes

- Tests MUST mock the HTTP layer (use `respx` or `unittest.mock` to patch `httpx.AsyncClient`).
  No real network calls in tests.
- `SATOSHI = Decimal("100000000")` — do not use floats for currency math anywhere.
- The `get_transactions_paginated` for BTC and the Kaspa cursor pagination must include a
  `asyncio.sleep(0.2)` between pages for rate-limit courtesy (per spec code snippets).
