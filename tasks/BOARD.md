# Task Board

Last updated: 2026-04-13

---

## QA Bug Fixes — Active Sprint

| ID  | Title                                                                               | Layer    | Status | Assignee  | Depends on | Files owned                                                                           |
|-----|-------------------------------------------------------------------------------------|----------|--------|-----------|------------|---------------------------------------------------------------------------------------|
| T27 | Fix BUG-01 — GET /api/wallets returns empty arrays instead of nulls in loading state | backend  | todo   | developer | —          | `backend/routers/wallets.py`, `tests/backend/test_wallets.py`                         |
| T28 | Fix BUG-02 — WalletDetailView uses wrong truncation call for HD wallet address      | frontend | todo   | developer | —          | `frontend/src/views/WalletDetailView.vue`                                             |
| T29 | Fix BUG-03 — Delete confirmation dialog body text not HD-aware                      | frontend | todo   | developer | —          | `frontend/src/components/wallet/RemoveWalletDialog.vue`                               |
| T30 | Fix BUG-04 — XpubClient includes n_tx=0 entries in derived address list            | backend  | todo   | developer | —          | `backend/clients/xpub.py`, `tests/backend/test_xpub_client.py`                        |

All four fix tasks are independent of each other and can run in parallel. No shared file ownership conflicts exist between them.

**Overlap check:**
- T27 touches `backend/routers/wallets.py` and `tests/backend/test_wallets.py`. T23 (done) also owned these files, but T23 is complete — no concurrent conflict.
- T28 touches `frontend/src/views/WalletDetailView.vue`. T26 (done) also owned this file, but T26 is complete — no concurrent conflict.
- T29 touches `frontend/src/components/wallet/RemoveWalletDialog.vue`. No other task in this cycle touches it.
- T30 touches `backend/clients/xpub.py` and `tests/backend/test_xpub_client.py`. T18 (done) owned these files, but T18 is complete — no concurrent conflict.

---

## HD Wallet Feature — Completed Sprint

| ID  | Title                                                       | Layer      | Status | Assignee  | Depends on    | Files owned                                                                                                                                                                                                                                 |
|-----|-------------------------------------------------------------|------------|--------|-----------|---------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| T17 | HD Wallet — Database Migration and DerivedAddress Model     | backend    | done   | developer | —             | `backend/models/wallet.py`, `backend/models/derived_address.py`, `backend/models/__init__.py`, `backend/migrations/versions/002_hd_wallet_support.py`, `tests/backend/test_models.py`                                                       |
| T18 | HD Wallet — XpubClient (blockchain.info API)                | backend    | done   | developer | T17           | `backend/clients/xpub.py`, `tests/backend/test_xpub_client.py`                                                                                                                                                                             |
| T19 | HD Wallet — DerivedAddressRepository                        | backend    | done   | developer | T17           | `backend/repositories/derived_address.py`, `backend/repositories/__init__.py`, `tests/backend/test_repositories.py`                                                                                                                         |
| T20 | HD Wallet — Extended Key Validation and WalletService Ext.  | backend    | done   | developer | T17, T19      | `backend/services/wallet.py`, `backend/core/exceptions.py`, `tests/backend/test_hd_wallets.py`, `tests/backend/test_wallets.py`                                                                                                             |
| T21 | HD Wallet — RefreshService Extension                        | backend    | done   | developer | T18, T19, T20 | `backend/services/refresh.py`, `tests/backend/test_refresh.py`                                                                                                                                                                              |
| T22 | HD Wallet — HistoryService Extension                        | backend    | done   | developer | T18, T20      | `backend/services/history.py`, `tests/backend/test_history.py`                                                                                                                                                                              |
| T23 | HD Wallet — API Schema and Wallet Router Extension          | backend    | done   | developer | T19, T20      | `backend/schemas/wallet.py`, `backend/routers/wallets.py`, `tests/backend/test_wallets.py`                                                                                                                                                  |
| T24 | HD Wallet — Frontend TypeScript Types and Utility Functions | frontend   | done   | developer | T23           | `frontend/src/types/api.ts`, `frontend/src/utils/validation.ts`, `frontend/src/utils/format.ts`                                                                                                                                             |
| T25 | HD Wallet — HdBadge and DerivedAddressList Components       | frontend   | done   | developer | T24           | `frontend/src/components/wallet/HdBadge.vue`, `frontend/src/components/wallet/DerivedAddressList.vue`, `tests/frontend/components/HdBadge.test.ts`, `tests/frontend/components/DerivedAddressList.test.ts`                                  |
| T26 | HD Wallet — AddWalletDialog, WalletTable, WalletDetailView  | frontend   | done   | developer | T25           | `frontend/src/components/wallet/AddWalletDialog.vue`, `frontend/src/components/widgets/WalletTable.vue`, `frontend/src/views/WalletDetailView.vue`, `frontend/src/stores/wallets.ts`, `tests/frontend/components/AddWalletDialog.test.ts`   |

---

## Dependency Graph — HD Wallet Feature

```
T17 ──┬──► T18 ──────────────────────────────► T21
      │                                          ▲
      ├──► T19 ──┬──► T20 ──┬──────────────────►┤
      │          │           │                   │
      │          └──────────►├──► T21            │
      │                      │                   │
      │                      └──► T22 ◄──── T18  │
      │                      │                   │
      │                      └──► T23            │
      └──────────────────────────► T23           │
                                    │            │
                                    └──► T24 ──► T25 ──► T26
```

Simplified linear view of critical path:

```
T17 → T19 → T20 → T23 → T24 → T25 → T26   (longest path / frontend unblock)
T17 → T18                                   (parallel with T19)
T18 + T19 + T20 → T21                      (all three must complete first)
T18 + T20 → T22                            (parallel with T21 after T20)
```

---

## Parallelism Opportunities

- **T18 and T19** can run in parallel after T17 completes (no shared files).
- **T21 and T22** can run in parallel after their respective prerequisites complete (no shared files).
- **T24, T25, T26** are a strictly sequential frontend chain (each depends on the previous).
- The frontend chain (T24 onward) can begin as soon as T23 is done. The backend chain (T21, T22) can finish concurrently.

---

## Overlap Analysis — HD Wallet Feature

All file ownership conflicts are serialized via explicit dependencies:

| File | Tasks | Resolution |
|------|-------|------------|
| `backend/models/wallet.py` | T17 only | No conflict |
| `backend/models/derived_address.py` | T17 only | No conflict |
| `backend/models/__init__.py` | T17 only | No conflict |
| `backend/migrations/versions/002_*` | T17 only | No conflict — only one migration in this cycle |
| `backend/repositories/__init__.py` | T19 only | No conflict |
| `backend/repositories/derived_address.py` | T19 only | No conflict |
| `backend/services/wallet.py` | T20 only | No conflict |
| `backend/core/exceptions.py` | T20 only | No conflict |
| `backend/services/refresh.py` | T21 only | No conflict |
| `backend/services/history.py` | T22 only | No conflict |
| `backend/schemas/wallet.py` | T23 only | No conflict |
| `backend/routers/wallets.py` | T23 only | No conflict |
| `tests/backend/test_wallets.py` | T20 (adds 2 cases) + T23 (adds 2 cases) | **Serialized**: T23 depends on T20, so T20 runs first |
| `tests/backend/test_repositories.py` | T19 only | No conflict |
| `tests/backend/test_hd_wallets.py` | T20 only | No conflict |
| `tests/backend/test_xpub_client.py` | T18 only | No conflict |
| `tests/backend/test_refresh.py` | T21 only | No conflict |
| `tests/backend/test_history.py` | T22 only | No conflict |
| `tests/backend/test_models.py` | T17 only | No conflict |
| `frontend/src/types/api.ts` | T24 only | No conflict |
| `frontend/src/utils/validation.ts` | T24 only | No conflict |
| `frontend/src/utils/format.ts` | T24 only | No conflict |
| `frontend/src/components/wallet/HdBadge.vue` | T25 only | No conflict |
| `frontend/src/components/wallet/DerivedAddressList.vue` | T25 only | No conflict |
| `frontend/src/components/wallet/AddWalletDialog.vue` | T26 only | No conflict |
| `frontend/src/components/widgets/WalletTable.vue` | T26 only | No conflict |
| `frontend/src/views/WalletDetailView.vue` | T26 only | No conflict |
| `frontend/src/stores/wallets.ts` | T26 only | No conflict |
| `tests/frontend/components/AddWalletDialog.test.ts` | T26 only | No conflict |
| `tests/frontend/components/HdBadge.test.ts` | T25 only | No conflict |
| `tests/frontend/components/DerivedAddressList.test.ts` | T25 only | No conflict |

**`tests/backend/test_wallets.py`** is the only file touched by two tasks (T20 and T23). T23 explicitly depends on T20, so they are serialized. T20 adds its cases first; T23 adds its cases second.

---

## Spec Coverage — HD Wallet Feature

| Requirement | Task |
|-------------|------|
| FR-H01: Add HD wallet via xpub/ypub/zpub | T20 |
| FR-H02: Auto-detect extended key vs. individual address | T20, T26 |
| FR-H03: Validate prefix + length + Base58Check | T20 |
| FR-H04: Reject testnet keys (tpub/upub/vpub) | T20 |
| FR-H05: Reject unrecognized prefix | T20 |
| FR-H06: Reject duplicate HD wallet key | T20 |
| FR-H07: Tag rules apply; default "BTC HD Wallet #n" | T20, T23 |
| FR-H08: "HD" badge in wallet list | T26 |
| FR-H09: Truncated key display (10+...+6), full on hover | T24, T26 |
| FR-H10: HD wallet counts as 1 toward 50-wallet limit | T20 |
| FR-H11: HD and individual wallets coexist | T20 |
| FR-H12: Expandable derived address sub-list | T25, T26 |
| FR-H13: Active derived address definition (n_tx > 0) | T18, T19 |
| FR-H14: Derived addresses sorted by balance descending | T19 |
| FR-H15: 200-address cap with "Showing top 200 of N" | T19, T25 |
| FR-H16: Remove HD wallet cascades all data | T17, T20, T23 |
| FR-H17: Aggregate balance fetched via xpub API | T18, T21 |
| FR-H18: Derived address individual balances fetched | T18, T21 |
| FR-H19: Aggregate balance stored as snapshot | T21 |
| FR-H20: HD wallets in same refresh cycle | T21 |
| FR-H21: Failure handling identical to individual wallets | T21 |
| FR-H22: Full history import on first add | T22 |
| FR-H23: Historical balance reconstruction (running sum) | T22 |
| FR-H24: Incremental sync on subsequent refreshes | T21, T22 |
| FR-H25: No per-derived-address history stored | T22 |
| FR-H26: HD wallet in portfolio totals and charts | T26 (via wallets store) |
| FR-H27: Aggregate balance chart on wallet detail page | T26 |
| FR-H28: No individual balance history charts per address | T25, T26 (by omission) |
| FR-H29: Derived address list on wallet detail page | T26 |
| FR-H30: "HD" badge wherever wallet tag appears | T25, T26 |
| ypub/zpub → xpub conversion (normalize_to_xpub) | T20 |
| XpubClient (blockchain.info multiaddr) | T18 |
| DerivedAddress ORM model | T17 |
| DerivedAddressRepository | T19 |
| Alembic migration 002 | T17 |
| API schema extensions (DerivedAddressResponse, WalletResponse) | T23, T24 |
| Trezor helper text in Add Wallet form | T26 |
| Client-side xpub detection (detectBtcInputType) | T24, T26 |
| Input label dynamic update | T26 |
| hd_address_count config key management | T21, T20 |
| Partial-success path: balance OK but no address breakdown (FUNC_SPEC §5.2.d / TECH_SPEC §10.7) | T21 |
| Remove HD wallet during active refresh — discard in-flight result (FUNC_SPEC §5.1.e / TECH_SPEC §10.8) | T21 |
| `hasCommitted` flag: label updates only on paste/blur, not on every keystroke (TECH_SPEC §10.4) | T26 |
| `hd_loading` exact derivation: `wallet_type=="hd" AND last_updated is None AND history_status=="importing"` (TECH_SPEC §10.10) | T23 |

---

## Completed Tasks (prior sprint — base CryptoDash)

| ID  | Title                                          | Layer      | Status | Assignee  | Depends on |
|-----|------------------------------------------------|------------|--------|-----------|------------|
| T01 | Backend Project Scaffolding                    | backend    | done   | developer | —          |
| T02 | Database Models and Initial Migration          | backend    | done   | developer | T01        |
| T03 | Repository Layer                               | backend    | done   | developer | T02        |
| T04 | Core Infrastructure                            | backend    | done   | developer | T03        |
| T05 | Authentication — Service, Schemas, Router      | backend    | done   | developer | T04        |
| T06 | External API Clients                           | backend    | done   | developer | T01        |
| T07 | Wallet Management — Service, Schemas, Router   | backend    | done   | developer | T05        |
| T08 | History Service                                | backend    | done   | developer | T06, T07   |
| T09 | Refresh Service, Dashboard Router, Settings    | backend    | done   | developer | T08        |
| T10 | Application Factory and Entry Point            | backend    | done   | developer | T09        |
| T11 | Frontend Foundation                            | frontend   | done   | developer | T01        |
| T12 | Auth Views and Auth Store                      | frontend   | done   | developer | T11        |
| T13 | Wallet Management Components and Wallets Store | frontend   | done   | developer | T12        |
| T14 | Dashboard View and Widgets                     | frontend   | done   | developer | T13        |
| T15 | Wallet Detail View and Settings View           | frontend   | done   | developer | T14        |
| T16 | WebSocket Integration and Real-Time Updates    | frontend   | done   | developer | T15        |
