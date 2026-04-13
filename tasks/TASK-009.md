# T09: Refresh Service, Dashboard Router, and Settings Router

**Status**: done
**Layer**: backend
**Assignee**: developer
**Depends on**: T08

## Context

The Refresh Service orchestrates a full balance+price refresh cycle (with concurrency lock, rate
limiting, and WebSocket broadcasting). The Dashboard Router exposes read-only aggregated data for
the frontend widgets. The Settings Router exposes the refresh interval setting and triggers
Scheduler restart on change. All three live here because they share the RefreshResult and the
SchedulerService pattern — a single developer can own all three without file conflicts.

> "RefreshService: orchestrate full refresh cycle."
> — specs/TECH_SPEC.md, Section 4.4
>
> "GET /api/dashboard/summary, /portfolio-history, /wallet-history, /prices, /composition"
> — specs/TECH_SPEC.md, Section 4 (implicitly from component table)
>
> "FR-019 through FR-022 (price retrieval), FR-043 through FR-047 (scheduler),
>  FR-038 through FR-042 (configuration panel)"

## Files owned

- `backend/services/refresh.py` (create)
- `backend/schemas/dashboard.py` (create)
- `backend/schemas/settings.py` (create)
- `backend/routers/dashboard.py` (create)
- `backend/routers/settings.py` (create)
- `backend/routers/websocket.py` (create)
- `tests/backend/test_refresh.py` (create)
- `tests/backend/test_dashboard.py` (create)
- `tests/backend/test_settings.py` (create)

## Subtasks

- [ ] ST1: Implement `backend/services/refresh.py` — `RefreshService` with `asyncio.Lock`,
      `run_full_refresh() -> RefreshResult` (lock check, price fetch, parallel wallet balance
      fetches with semaphore=5, incremental history sync call, WebSocket broadcasts), and
      `refresh_single_wallet(wallet) -> BalanceSnapshot | None` (no lock). Per spec Section 4.4.
- [ ] ST2: Implement `backend/schemas/dashboard.py` — `PortfolioSummary`, `HistoryDataPoint`,
      `PortfolioHistoryResponse`, `WalletHistoryResponse`, `PriceHistoryResponse`,
      `PortfolioComposition`, `CompositionSegment`. Per spec Section 5.3.
- [ ] ST3: Implement `backend/schemas/settings.py` — `SettingsResponse`, `SettingsUpdate` with
      `@field_validator` for allowed intervals (5, 15, 30, 60, None). Per spec Section 5.3.
- [ ] ST4: Implement `backend/routers/dashboard.py` — endpoints (all require `get_current_user`):
      - `GET /api/dashboard/summary` → `PortfolioSummary` (aggregate all wallets, latest balances,
        latest prices, 24h change).
      - `GET /api/dashboard/portfolio-history?range=30d` → `PortfolioHistoryResponse` (sum wallet
        balance snapshots over time × price snapshots for USD value).
      - `GET /api/dashboard/wallet-history/{wallet_id}?range=30d&unit=usd` → `WalletHistoryResponse`.
      - `GET /api/dashboard/prices?range=30d` → `PriceHistoryResponse`.
      - `GET /api/dashboard/composition` → `PortfolioComposition`.
      - `POST /api/dashboard/refresh` → triggers `run_full_refresh()`, returns 202 if skipped.
- [ ] ST5: Implement `backend/routers/settings.py` — `GET /api/settings` and `PUT /api/settings`,
      both require `get_current_user`. On PUT: save to DB via `ConfigRepository`, call
      `scheduler.restart(new_interval)`.
- [ ] ST6: Implement `backend/routers/websocket.py` — `WS /api/ws` endpoint per spec Section 4.7.b.
      Token from query param, `ConnectionManager.connect()`, keep-alive ping/pong loop.
- [ ] ST7: Write `tests/backend/test_refresh.py` — mock clients; test: successful full refresh stores
      balance and price snapshots, single wallet failure does not abort others, refresh skipped
      when lock is held, WebSocket events broadcast on start and completion.
- [ ] ST8: Write `tests/backend/test_dashboard.py` — seed test DB with wallets + snapshots; test:
      `GET /api/dashboard/summary` correct totals and 24h change, history range filtering,
      composition percentages, empty-state (no wallets).
- [ ] ST9: Write `tests/backend/test_settings.py` — test GET returns default interval (15),
      PUT with valid interval persists it, PUT with invalid interval returns 422.

## Acceptance criteria

- [ ] `pytest tests/backend/test_refresh.py tests/backend/test_dashboard.py tests/backend/test_settings.py -v` passes.
- [ ] FR-016/FR-021: Full refresh fetches balances for all wallets and prices in one cycle.
- [ ] FR-047: Concurrent refresh: second `run_full_refresh()` call while first is running returns
      `RefreshResult(skipped=True)` (verified by test).
- [ ] FR-035: `GET /api/dashboard/summary` includes `last_updated` timestamp.
- [ ] FR-039: `PUT /api/settings` with `refresh_interval_minutes: 999` returns 422.
- [ ] FR-040: `PUT /api/settings` with `refresh_interval_minutes: 5` is persisted across a new GET.
- [ ] FR-031: `GET /api/dashboard/summary` with no wallets returns zeros/nulls (not 500).
- [ ] `ruff check backend/services/refresh.py backend/routers/dashboard.py backend/routers/settings.py` exits 0.

## Notes

- Portfolio history: for each time bucket, compute `sum(wallet_balance_at_T * price_at_T)`. Use
  `BalanceSnapshotRepository.get_range()` and `PriceSnapshotRepository.get_nearest_before()`.
- 24h change: find the `PortfolioSummary` value from 24h ago using nearest balance snapshots.
  Return `null` if no snapshot exists from ~24h ago.
- The Scheduler reference for `settings.py` router: inject via `request.app.state.scheduler` (set
  in `app.py` lifespan — T10). This avoids circular imports.
- Time range parameter `range` maps to: "7d"→7 days, "30d"→30, "90d"→90, "1y"→365, "all"→no limit.
