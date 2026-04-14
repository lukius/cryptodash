# T18 Review: HD Wallet — XpubClient (blockchain.info API)

**Verdict**: APPROVED (with one low-severity issue to fix)

**Reviewer**: Tech Lead
**Date**: 2026-04-13

---

## Automated Check Results

| Check | Result |
|---|---|
| `ruff check backend/ tests/` | PASS |
| `ruff format --check backend/ tests/` | PASS |
| `pytest tests/backend/ -v` | PASS — 357 passed, 0 failures |
| `pytest tests/backend/test_xpub_client.py -v` | PASS — 12 passed |

---

## Issues Filed

### Issue 1 (Low): `XpubTransaction.timestamp` typed `int | None` but `_parse_txs` never produces `None`

**Severity**: Low

**Component**: backend/clients/xpub.py

**File(s)**: `backend/clients/xpub.py:31-33`

**Problem**:
The `XpubTransaction` dataclass declares `timestamp: int | None`, and the field comment reads "None for unconfirmed". But `_parse_txs` always converts a `None` raw `time` value to an integer via `int(datetime.now(tz=timezone.utc).timestamp())`. No consumer of this dataclass will ever receive `timestamp=None`. The `int | None` annotation overstates the contract, introduces dead-code None-guards downstream (`if tx.timestamp is not None else 0` in three sort lambdas), and contradicts both the spec dataclass definition and the actual runtime behavior.

**Spec reference**:
> "`timestamp: int  # Unix epoch seconds (block confirmation time)`"
> — TECH_SPEC_HD_WALLETS.md §4.3.b

> "handle `time=None` (unconfirmed) by using `datetime.utcnow()` as timestamp approximation"
> — T18.md, ST6

The spec's dataclass declares `timestamp: int` (not `int | None`). The implementation's conversion logic in `_parse_txs` is correct (fulfills ST6), but the type annotation was not updated to reflect it.

**Steps to reproduce / evidence**:

```python
# xpub.py:31-33 — type says Optional
timestamp: (
    int | None
)  # Unix epoch seconds (block confirmation time); None for unconfirmed

# xpub.py:170-175 — but _parse_txs always resolves to int
raw_time = tx.get("time")
if raw_time is None:
    timestamp = int(datetime.now(tz=timezone.utc).timestamp())
else:
    timestamp = raw_time
```

Three sort lambdas guard against `None` unnecessarily:
- Line 118: `t.timestamp if t.timestamp is not None else 0`
- Line 153: `t.timestamp if t.timestamp is not None else 0`
- Line 159: `t.timestamp if t.timestamp is not None else 0`

**Expected**:
`XpubTransaction.timestamp: int` — the None-handling lives inside `_parse_txs` (correct) and the public field type reflects the guarantee: it is always an `int`.

**Actual**:
`XpubTransaction.timestamp: int | None` — the comment says "None for unconfirmed" even though the code never produces `None`. Three sort lambdas include dead None-guards.

**Suggested fix**:
Change the dataclass field to `timestamp: int`, remove the misleading comment, and simplify the three sort lambdas to use `t.timestamp` directly (or `t.timestamp or 0` as a scalar for the two-tuple key).

---

## Spec Compliance Walkthrough

### ST1 — Dataclasses

`DerivedAddressData`, `XpubSummary`, and `XpubTransaction` are all defined with the correct fields as specified in §4.3.b. The sole deviation is `XpubTransaction.timestamp: int | None` vs spec `int`, covered in Issue 1 above.

### ST2 — Class structure

`XpubClient(BaseClient)` with `base_url="https://blockchain.info"` and `timeout=30.0`. Matches spec §4.3.a exactly.

### ST3 — `get_xpub_summary`

- Calls `/multiaddr` with `n=1, offset=0`. Correct.
- Reads `wallet.final_balance` for `balance_sat`. Correct.
- Reads `info.n_tx` for `n_tx`. Correct per §1.2 ("info.n_tx: total transaction count").
- Iterates `addresses[]` for full derived address list. Correct.
- Computes `balance_btc = Decimal(balance_sat) / SATOSHI`. Correct.

### ST4 — `get_xpub_transactions_all`

- First call with `n=50, offset=0`. Correct.
- Loop condition `while offset < total`. Correct.
- Also breaks on empty `txs` page. Correct.
- `asyncio.sleep(0.2)` placed before each subsequent page fetch (sleep is *between* pages, not after the last page). Correct.
- Sorts oldest-first. Correct.
- n_tx=125 produces exactly 3 requests (offsets 0, 50, 100) — verified by `test_get_xpub_transactions_all_multi_page`.

### ST5 — `get_xpub_transactions_since`

- Iterates pages from offset 0.
- Stops mid-page when `tx.timestamp <= after_timestamp`. Correct (returns immediately).
- Stops on empty page. Correct.
- `asyncio.sleep(0.2)` placed after processing a full page, before the next offset. Correct.
- Sorts result oldest-first. Correct.

### ST6 — `_parse_txs` and unconfirmed transactions

- `time=None` → assigns `int(datetime.now(tz=timezone.utc).timestamp())`. Correct per ST6.
- Uses timezone-aware `datetime.now(tz=timezone.utc)` instead of deprecated `datetime.utcnow()`. Positive deviation — preferred over spec's example.
- Returns `XpubTransaction` for every raw tx. Correct.

### ST7 — Tests

All 9 tests from TECH_SPEC_HD_WALLETS.md §9.2 are present and pass:

| Test | Present | Passes |
|---|---|---|
| `test_get_xpub_summary_parses_response` | Yes | Yes |
| `test_get_xpub_summary_empty_addresses` | Yes | Yes |
| `test_get_xpub_transactions_all_single_page` | Yes | Yes |
| `test_get_xpub_transactions_all_multi_page` | Yes | Yes |
| `test_get_xpub_transactions_since` | Yes | Yes |
| `test_xpub_client_rate_limit_handling` | Yes | Yes |
| `test_xpub_client_server_error` | Yes | Yes |
| `test_xpub_client_unconfirmed_tx` | Yes | Yes |
| `test_xpub_client_zero_n_tx` | Yes | Yes |

Three additional tests beyond the 9 required: `test_get_xpub_summary_uses_n1_param`, `test_get_xpub_transactions_all_stops_on_empty_page`, `test_get_xpub_transactions_since_all_new`. All pass and add genuine coverage.

### Architecture

- `XpubClient` is in the `clients` layer, extends `BaseClient`, uses `_get_with_retry` for all HTTP calls. Correct.
- No business logic, no HTTP concepts leak into the client. Correct.
- All methods are `async`. Correct.
- No external dependencies added (only stdlib + already-present `httpx`). Correct.

### Security

- No secrets or credentials in code. The xpub key is passed as a query parameter — no logging of the parameter is done (BaseClient logs `path` only, not params). Acceptable.
- No hard-coded credentials or API keys. Correct.

---

## Spec Ambiguities Discovered

1. **T18.md AC vs BaseClient behavior for 5xx**: The acceptance criteria states "HTTP 5xx raises on **second failure**", but `BaseClient._get_with_retry` raises on the **first** failure for 5xx (only 429 and `RequestError` are retried). The test correctly reflects actual behavior (`call_count == 1`). The AC text is misleading. The spec/AC should be corrected.

2. **§4.3.b `XpubTransaction.timestamp` type vs §4.3.c `_parse_txs` code**: The spec's own dataclass definition says `timestamp: int`, but the spec's `_parse_txs` code passes `timestamp=tx.get("time")` which can be `None`. The prose at §4.3.c (end of section) clarifies "stored with `timestamp = datetime.utcnow()`", making `int` the correct type. The spec code snippet is inconsistent with both the type annotation and the prose — the implementation chose the correct interpretation.

3. **§4.3.d edge case tests `test_xpub_over_200_addresses` and `test_xpub_timeout`**: The §4.3.d edge case table assigns test names to these scenarios, but the §9.2 required test table (which ST7 references) omits them. The implementation does not include these tests. Given §9.2 is the authoritative list for ST7, this is not a defect — but the §4.3.d table names are dead references and should be removed or reconciled.

---

## Overall Assessment

**APPROVED** with one low-severity issue (Issue 1: misleading type annotation on `XpubTransaction.timestamp`). The implementation is functionally correct, complete per spec, architecturally sound, and well-tested. All 9 required test scenarios pass. Automated checks pass cleanly.

The type annotation defect does not affect correctness or runtime behavior — `_parse_txs` never produces `None` for `timestamp`. However it should be fixed to avoid misleading future consumers of the dataclass.
