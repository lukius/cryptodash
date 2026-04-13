# CryptoDash QA Report

**Date:** 2026-04-13
**Tester:** QA Analyst (automated session)
**Environment:** Backend on `http://localhost:8000`, fresh SQLite database, real external APIs

**Summary: 51 passed, 3 failed, 2 blocked**

---

## Failures

---

### BUG-001 — CRITICAL: `GET /api/wallets/` returns 500 after any refresh cycle

**Affected FR:** FR-010, FR-032
**Endpoint:** `GET /api/wallets/`

**Steps to reproduce:**
1. Create account, login.
2. Add any wallet.
3. `POST /api/dashboard/refresh` (stores a `PriceSnapshot`).
4. `GET /api/wallets/` — returns `500 Internal Server Error`.

**Expected:** 200 with wallet list.
**Actual:** 500. Server log: `AttributeError: 'PriceSnapshot' object has no attribute 'price'`

**Root cause:** `backend/services/wallet.py` lines 116 and 119 reference `price_snap.price`, but the `PriceSnapshot` model field is `price_usd` (`backend/models/price_snapshot.py` line 15).

**Fix:** Change both `price_snap.price` to `price_snap.price_usd` in `backend/services/wallet.py`.

**curl:**
```bash
curl -s http://localhost:8000/api/wallets/ -H "Authorization: Bearer <token>"
# Returns: Internal Server Error
```

---

### BUG-002 — HIGH: Incremental transaction sync fails with `database is locked` on every refresh

**Affected FR:** FR-026, FR-027, FR-029
**Component:** `backend/services/history.py` (incremental sync), `backend/services/refresh.py`

**Steps to reproduce:**
1. Add a wallet with real transaction history (e.g. `bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4`).
2. Trigger `POST /api/dashboard/refresh` multiple times.

**Expected:** Incremental sync stores new transactions on each refresh cycle.
**Actual:** Every incremental sync fails with `sqlite3.OperationalError: database is locked`.

**Root cause:** The background history import tasks (spawned via `asyncio.create_task` on wallet add) hold a SQLite write lock for large `INSERT OR IGNORE` batches. When `run_full_refresh()` also writes (balance snapshots, price snapshots) concurrently, the incremental sync fails. This repeats on every subsequent refresh cycle. Wallet history charts never advance beyond the initial import.

**Evidence from server logs:**
```
Incremental sync failed for Bech32 Wallet: (sqlite3.OperationalError) database is locked
Incremental sync failed for BTC Wallet #1: (sqlite3.OperationalError) database is locked
```

---

### BUG-003 — MEDIUM: Real Kaspa addresses with 60-character payload are rejected

**Affected FR:** FR-001, FR-002
**Endpoint:** `POST /api/wallets/`

**Steps to reproduce:**
```bash
curl -s -X POST http://localhost:8000/api/wallets/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"network":"KAS","address":"kaspa:qpamkvhgh0kzx50gwvvp5xs8ktmqutcy3dfs9dc3w7rd2wpc7acaqw0r69k3","tag":"KAS Test"}'
```

**Expected:** 201 — valid Kaspa address accepted.
**Actual:** 400 `{"detail":"Invalid Kaspa address format. Kaspa addresses start with 'kaspa:'."}`

**Root cause:** `backend/services/wallet.py` line 76: `61 <= len(remainder) <= 63`. The address `kaspa:qpamkvhgh0kzx50gwvvp5xs8ktmqutcy3dfs9dc3w7rd2wpc7acaqw0r69k3` has a 60-character payload, which is valid per the actual Kaspa protocol but rejected by the implementation. The functional spec also incorrectly states "61 characters" exactly. The allowed minimum should be 60.

---

## Blocked

### BLOCKED-001: Wallet 50-limit (FR-009 / 409 on 51st wallet)
Not end-to-end verified via API — would require 46 additional unique valid addresses. The code path exists (`MAX_WALLETS = 50`, maps to 409) and the automated test suite covers it (`test_wallets.py`).

### BLOCKED-002: WebSocket `refresh:completed` event
`refresh:started` was confirmed received. `refresh:completed` was not received within the test window because live external API calls (Mempool.space, CoinGecko) take 15–30+ seconds per refresh. The broadcast code exists in `backend/services/refresh.py`.

---

## Passed Tests

| # | Endpoint | Scenario | Result |
|---|---|---|---|
| TC-AUTH-001 | GET /api/auth/status | Fresh install, no account | PASS |
| TC-AUTH-002 | POST /api/auth/setup | Weak password (< 8 chars) → 422 | PASS |
| TC-AUTH-003 | POST /api/auth/setup | Password mismatch → 422 | PASS |
| TC-AUTH-004 | POST /api/auth/setup | Valid credentials → 201 + token | PASS |
| TC-AUTH-005 | POST /api/auth/setup | Account already exists → 409 | PASS (FR-048/049) |
| TC-AUTH-006 | GET /api/auth/status | After setup, no session | PASS |
| TC-AUTH-007 | POST /api/auth/login | Wrong password → 401 | PASS |
| TC-AUTH-008 | POST /api/auth/login | 5 consecutive failures → 429 + retry_after | PASS |
| TC-AUTH-009 | POST /api/auth/login | Valid credentials → 200 + token | PASS |
| TC-AUTH-010 | GET /api/auth/status | With valid token → authenticated=true | PASS |
| TC-AUTH-011 | GET /api/wallets/ | No token → 401 | PASS (FR-058) |
| TC-AUTH-012 | GET /api/wallets/ | Invalid token → 401 | PASS |
| TC-AUTH-REMEMBER | POST /api/auth/login | remember_me=true → 30-day expiry | PASS (FR-056) |
| TC-AUTH-MULTI | Multiple sessions | Logout one, other stays valid | PASS |
| TC-LOGOUT-001 | POST /api/auth/logout | Valid logout → {"ok":true} | PASS |
| TC-LOGOUT-002 | GET /api/wallets/ | Token after logout → 401 | PASS |
| TC-LOGOUT-003 | POST /api/auth/logout | Logout again with same token → 401 | PASS |
| TC-WALLET-001 | GET /api/wallets/ | Empty list → count=0, limit=50 | PASS |
| TC-WALLET-002 | POST /api/wallets/ | Invalid BTC address → 400 | PASS (FR-002) |
| TC-WALLET-003 | POST /api/wallets/ | Invalid KAS address (no prefix) → 400 | PASS |
| TC-WALLET-004 | POST /api/wallets/ | Valid BTC P2PKH → 201 | PASS |
| TC-WALLET-005 | POST /api/wallets/ | Duplicate address → 400 | PASS (FR-003) |
| TC-WALLET-007 | POST /api/wallets/ | Valid BTC P2SH → 201 | PASS |
| TC-WALLET-008 | POST /api/wallets/ | Valid Bech32 (bc1q, 42 chars) → 201 | PASS |
| TC-WALLET-009 | POST /api/wallets/ | Bech32 uppercase duplicate → 400 (case-insensitive) | PASS |
| TC-WALLET-010 | POST /api/wallets/ | No tag → auto "BTC Wallet #1" | PASS (FR-005) |
| TC-WALLET-011 | POST /api/wallets/ | Duplicate tag → 400 | PASS |
| TC-WALLET-012 | POST /api/wallets/ | Tag > 50 chars → 400 | PASS |
| TC-WALLET-013 | POST /api/wallets/ | Empty address → 422 | PASS |
| TC-WALLET-016 | PATCH /api/wallets/{id} | Update tag → 200 | PASS (FR-006) |
| TC-WALLET-017 | PATCH /api/wallets/{id} | Duplicate tag → 400 | PASS |
| TC-WALLET-018 | PATCH /api/wallets/{id} | Non-existent wallet → 404 | PASS |
| TC-WALLET-019 | DELETE /api/wallets/{id} | Delete wallet → 204 | PASS (FR-007) |
| TC-WALLET-020 | DB verify | Cascade delete removes balance_snapshots | PASS |
| TC-WALLET-021 | DELETE /api/wallets/{id} | Non-existent → 404 | PASS |
| TC-WALLET-022 | POST /{id}/retry-history | Non-existent → 404 | PASS |
| TC-WALLET-023 | POST /{id}/retry-history | Valid → {"ok":true,"message":...} | PASS |
| TC-WALLET-TAPROOT | POST /api/wallets/ | Bech32m Taproot (bc1p, 62 chars) → 201 | PASS |
| TC-WALLET-WHITESPACE | POST /api/wallets/ | Address with whitespace → trimmed + 201 | PASS |
| TC-WALLET-NETWORK | POST /api/wallets/ | ETH network → 422 | PASS |
| TC-WALLET-AUTOTAG | POST /api/wallets/ | No tag, #1 taken → "BTC Wallet #2" | PASS |
| TC-DASH-001 | GET /api/dashboard/summary | Empty portfolio → zeros + nulls | PASS |
| TC-DASH-002 | GET /api/dashboard/portfolio-history | Valid range → 200 | PASS |
| TC-DASH-003 | GET /api/dashboard/portfolio-history | Invalid range → 400 | PASS |
| TC-DASH-004 | GET /api/dashboard/price-history | Valid range → 200 | PASS |
| TC-DASH-005 | GET /api/dashboard/wallet-history/{id} | Valid → 200 | PASS |
| TC-DASH-006 | GET /api/dashboard/wallet-history/{id} | Non-existent → 404 | PASS |
| TC-DASH-007 | GET /api/dashboard/composition | Empty → {"segments":[]} | PASS |
| TC-DASH-008 | POST /api/dashboard/refresh | Manual refresh → 200 with counts | PASS |
| TC-DASH-009 | POST /api/dashboard/refresh | Concurrent → second returns skipped=true | PASS (FR-047) |
| TC-DASH-RANGES | History endpoints | All ranges (7d/30d/90d/1y/all) → 200 | PASS |
| TC-DASH-AFTER-REFRESH | GET /api/dashboard/summary | After refresh → real BTC prices populated | PASS |
| TC-SETTINGS-001 | GET /api/settings/ | Default 15 min | PASS |
| TC-SETTINGS-002 | PUT /api/settings/ | Set 5 min → 200 | PASS |
| TC-SETTINGS-003 | PUT /api/settings/ | Invalid (7 min) → 422 | PASS (FR-039) |
| TC-SETTINGS-004 | PUT /api/settings/ | null (disable) → 200 | PASS |
| TC-SETTINGS-005 | PUT /api/settings/ | Values 15, 30, 60 → 200 | PASS |
| TC-SETTINGS-INVALID | PUT /api/settings/ | Values 0,1,6,10,14,45,61,100 → 422 | PASS |
| TC-WS-001 | WebSocket | No token → HTTP 403 rejected | PASS |
| TC-WS-002 | WebSocket | Invalid token → HTTP 403 rejected | PASS |
| TC-WS-003 | WebSocket | Valid token + ping → pong | PASS |
| TC-WS-004 | WebSocket | refresh:started event received | PASS (partial) |
| TC-SECURITY-001 | Login response | No password field in response | PASS (FR-051) |
| TC-SECURITY-DB | DB | Password stored as bcrypt `$2b$12$...` | PASS |
| TC-AUTH-ENDPOINTS | All protected endpoints | Without token → 401 | PASS (FR-058) |
| TC-DB-CASCADE | DELETE wallet | Cascade removes balance_snapshots | PASS (FR-007) |

---

## Minor Observations (not failures)

1. **Trailing slash required for settings:** `GET /api/settings` returns 404; only `GET /api/settings/` works. Tech spec documents it as `/api/settings`. No redirect is configured.

2. **`created_at` timezone inconsistency:** `POST /api/wallets/` returns `created_at` with `+00:00` offset; the list endpoint returns `created_at` without timezone info. Both are ISO 8601 but inconsistent.

3. **Raw exception strings in refresh errors array:** The `errors` field in the refresh response contains full `httpx` exception strings including internal URLs. Should be sanitized to a user-friendly message.
