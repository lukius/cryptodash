# T14: Dashboard View and Widgets

**Status**: done
**Layer**: frontend
**Assignee**: developer
**Depends on**: T13

## Context

The main screen of the application. Implements all 8 dashboard widgets (W1–W8) and the dashboard
Pinia store. The dashboard is the most visually complex part of the frontend — it must be
responsive from 360px to 1920px, populate from cached data immediately, and support manual
refresh. The mockup at `specs/mockups/02-dashboard.html` is the authoritative visual reference.

> "FR-031 through FR-037: dashboard widgets W1–W8, responsive, last updated, manual refresh."
> — specs/FUNC_SPEC.md, Section 5.5
>
> "02-dashboard.html mockup is the visual source of truth."
> — specs/TECH_SPEC.md, Section (UI Mockups)

## Files owned

- `frontend/src/stores/dashboard.ts` (modify — implement fully)
- `frontend/src/views/DashboardView.vue` (create)
- `frontend/src/components/widgets/TotalPortfolioValue.vue` (create)
- `frontend/src/components/widgets/TotalBtcBalance.vue` (create)
- `frontend/src/components/widgets/TotalKasBalance.vue` (create)
- `frontend/src/components/widgets/WalletTable.vue` (create)
- `frontend/src/components/widgets/PortfolioComposition.vue` (create)
- `frontend/src/components/widgets/PortfolioValueChart.vue` (create)
- `frontend/src/components/widgets/WalletBalanceChart.vue` (create)
- `frontend/src/components/widgets/PriceChart.vue` (create)
- `tests/frontend/components/WalletTable.test.ts` (create)

## Subtasks

- [ ] ST1: Implement `frontend/src/stores/dashboard.ts` — Pinia store with:
      - State: `summary: PortfolioSummary | null`, `portfolioHistory: PortfolioHistoryResponse | null`,
        `priceHistory: PriceHistoryResponse | null`, `composition: PortfolioComposition | null`,
        `selectedRange: "7d"|"30d"|"90d"|"1y"|"all"`, `isRefreshing: boolean`.
      - Actions: `fetchSummary()`, `fetchPortfolioHistory(range)`, `fetchPriceHistory(range)`,
        `fetchComposition()`, `triggerRefresh()` (POST /api/dashboard/refresh).
- [ ] ST2: Implement `DashboardView.vue` — layout container for all widgets:
      - On mount: load summary, portfolio history (default "30d"), composition, price history.
      - Show EmptyState when no wallets.
      - Manual refresh button (shows LoadingSpinner while refreshing).
      - Responsive grid layout matching `specs/mockups/02-dashboard.html`.
      - Uses AppHeader (with refresh button wired) and AppFooter (last-updated).
- [ ] ST3: Implement `TotalPortfolioValue.vue` (W1) — large USD value, 24h change amount+percentage,
      color-coded (green/red). Show "N/A" when no price data.
- [ ] ST4: Implement `TotalBtcBalance.vue` (W2) and `TotalKasBalance.vue` (W3) — native balance
      with USD equivalent below. Use `formatBtc` / `formatKas` / `formatUsd` from utils.
- [ ] ST5: Implement `WalletTable.vue` (W4) — sortable table:
      - Columns: Tag, Network, Address (truncated with full on hover), Balance (native), Balance (USD).
      - Sort by any column (click header). Default sort by tag.
      - Clicking a row navigates to `/wallet/:id`.
      - Shows `WalletStatusBadge` per wallet.
      - "Add Wallet" button (opens `AddWalletDialog`) in table header.
      - Empty state message when no wallets.
- [ ] ST6: Implement `PortfolioComposition.vue` (W5) — Chart.js Pie chart:
      - Segments by network (BTC, KAS), sized by USD value.
      - Labels: percentage + USD value.
      - Single-network case: full circle with label.
      - No data: empty state.
- [ ] ST7: Implement `PortfolioValueChart.vue` (W6) — Chart.js Line chart:
      - Time on X-axis (using `chartjs-adapter-date-fns`), USD on Y-axis.
      - TimeRangeSelector component wired to dashboard store.
      - Hover tooltips with formatted USD + date.
      - "Not enough data" message when empty.
- [ ] ST8: Implement `WalletBalanceChart.vue` (W7) — line chart per wallet, used in detail view and
      optionally dashboard. Toggle between native coin and USD. TimeRangeSelector.
- [ ] ST9: Implement `PriceChart.vue` (W8) — dual-axis or side-by-side BTC/USD and KAS/USD line
      charts. TimeRangeSelector. Hover tooltips.
- [ ] ST10: Write `tests/frontend/components/WalletTable.test.ts`:
      - Renders wallet rows correctly.
      - Clicking a column header changes sort order.
      - Empty state is shown when `wallets` is empty.
      - Clicking a row emits navigation to correct wallet detail URL.

## Acceptance criteria

- [ ] `cd frontend && npm run test` passes all WalletTable tests.
- [ ] `cd frontend && npm run build` succeeds.
- [ ] FR-031: DashboardView is the default route (`/`).
- [ ] FR-032: All 8 widgets (W1–W8) are visible on the dashboard.
- [ ] FR-033: Dashboard is functional at 375px mobile width (manually tested in browser devtools).
- [ ] FR-034: USD values show 2dp, BTC values show 8dp, KAS values show 2dp.
- [ ] FR-035: "Last updated" timestamp is displayed via AppFooter.
- [ ] FR-036: Refresh button triggers `triggerRefresh()` and shows loading state.
- [ ] FR-037: Empty state is shown when no wallets (with "Add Wallet" CTA).
- [ ] W6: TimeRangeSelector changes the chart date range.
- [ ] Visual match: DashboardView matches `specs/mockups/02-dashboard.html` for layout, colors,
      widget arrangement (inspected in browser).

## Notes

- Open `specs/mockups/02-dashboard.html` in a browser before implementing — it is the authoritative
  visual reference. Pay attention to the grid layout, color tokens, and widget card styles.
- Chart.js requires `chartjs-adapter-date-fns` for time axes — ensure it is imported in the chart
  component files.
- `WalletTable` imports `AddWalletDialog` and owns the modal open/close state locally. The dialog
  emits `wallet-added` on success; the table calls `wallets.fetchWallets()` to refresh the list.
- `WalletBalanceChart` is shared between DashboardView and WalletDetailView (T15). Make it
  reusable via props for `walletId` and `unit`.
