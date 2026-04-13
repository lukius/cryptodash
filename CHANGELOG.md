# Changelog

All notable changes to this project will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [1.0.0] — 2026-04-13

Initial release of CryptoDash.

### Added

**Backend**
- FastAPI async backend with SQLAlchemy + SQLite (WAL mode)
- Alembic migration infrastructure with initial schema (users, sessions, wallets, transactions, balance_snapshots, price_snapshots, configuration)
- Auth service: first-run account setup, login, logout, session management (7-day / 30-day "remember me"), bcrypt password hashing
- Wallet service: add/remove/tag wallets; regex-based address validation for Bitcoin (P2PKH, P2SH, Bech32, Taproot) and Kaspa
- History service: retroactive transaction import from blockchain + incremental sync on refresh
- Refresh service: orchestrates full balance + price refresh cycle with asyncio lock to prevent concurrent runs
- Price service: current and historical BTC/USD and KAS/USD prices via CoinGecko
- Background scheduler: configurable auto-refresh interval, starts with app lifecycle
- WebSocket manager: real-time broadcast of refresh events to connected clients
- External API clients for Mempool.space (Bitcoin), api.kaspa.org (Kaspa), CoinGecko — with retry and timeout handling
- Configuration persistence via key-value table (refresh interval and future settings)
- `python run.py reset-password` CLI command
- Environment variable configuration (host, port, DB path, log level)
- CORS for frontend dev server

**Frontend**
- Vue 3 + TypeScript + Pinia SPA
- Auth flow: setup page (first-run), login page with "Remember me" checkbox, guarded routes
- Dashboard with eight widgets:
  - W1: Total portfolio value in USD
  - W2: Total BTC balance
  - W3: Total KAS balance
  - W4: Wallet table with per-wallet balances and inline tag editing
  - W5: Portfolio composition pie chart
  - W6: Portfolio value over time (line chart)
  - W7: Per-wallet balance history (line chart on wallet detail page)
  - W8: BTC/USD and KAS/USD price charts
- Time range selector (7d / 30d / 90d / 1y / All) for history charts
- Wallet management: add wallet dialog, inline tag editor, remove confirmation dialog, address format validation
- Wallet detail view: balance history chart, transaction timeline, delete wallet
- Settings page: configurable refresh interval
- Header: manual refresh button, settings link, logout
- WebSocket composable with auto-reconnect; real-time portfolio updates without page reload
- Responsive Tailwind CSS design

**Tests**
- Backend: 20 pytest test modules covering auth, wallets, dashboard, settings, refresh, history, scheduler, security, repositories, models, database, exception handlers, and all three external API clients
- Frontend: Vitest component and store tests (WalletTable, AddWalletDialog, TimeRangeSelector, auth store, wallets store)

[Unreleased]: https://gitlab.com/lukius/cryptodash/-/compare/v1.0.0...HEAD
[1.0.0]: https://gitlab.com/lukius/cryptodash/-/tags/v1.0.0
