# T06 Review: External API Clients

**Verdict**: APPROVED (after re-review of fixes — 2026-04-12)

---

## Automated Check Results (re-review)

| Check | Result |
|---|---|
| `ruff check backend/clients/ tests/backend/` | PASS |
| `ruff format --check backend/clients/ tests/backend/` | PASS |
| `pytest` (33 tests) | PASS |

All automated checks pass.

---

## Fix Verification

### Issue 1 — RESOLVED: `_get_with_retry` no longer retries HTTP 5xx

`backend/clients/base.py` now uses two separate except clauses:

```python
except httpx.HTTPStatusError:
    raise
except httpx.RequestError as e:
    logger.warning(...)
    await asyncio.sleep(10)
    ...retry...
```

`HTTPStatusError` (any 4xx/5xx after the 429 branch) is re-raised immediately. Only `RequestError` (timeout, network failure) triggers the 10s retry. This is correct per spec 4.3.e.

### Issue 2 — RESOLVED: `test_get_with_retry_raises_on_5xx` now asserts `call_count == 1`

`tests/backend/test_bitcoin_client.py:365` asserts `call_count == 1`, enforcing the no-retry contract for 5xx. The test is now a meaningful behavioral guard.

### Issue 3 — RESOLVED: New file `tests/backend/test_base_client.py` added

Three new tests cover all remaining spec 4.3.e cases:
- `test_request_timeout` — `httpx.ReadTimeout` propagates after one retry; asserts `call_count == 2` and `sleep(10)`.
- `test_network_unreachable` — `httpx.ConnectError` propagates after one retry; asserts `call_count == 2` and `sleep(10)`.
- `test_server_error_no_retry` — HTTP 503 raises immediately; asserts `call_count == 1` and sleep not called.

All three tests are meaningful, use `respx` for HTTP mocking, and patch `asyncio.sleep` to avoid real delays.

---

## Original Issues (Round 1)

### Issue 1: `_get_with_retry` retried HTTP 5xx — FIXED

### Issue 2: `test_get_with_retry_raises_on_5xx` did not assert `call_count == 1` — FIXED

### Issue 3: Missing `test_request_timeout` and `test_network_unreachable` — FIXED

---

## Findings (not developer issues)

**Spec ambiguity — `_get_with_retry` base snippet vs edge case table conflict**: The pseudocode in Section 4.3.a shows `_get_with_retry` catching all `HTTPStatusError | RequestError` and retrying after 10s with no 5xx distinction. The edge case table in 4.3.e says 5xx must not be retried. The implementation now matches 4.3.e (correct), but the spec's 4.3.a pseudocode remains misleading. The spec should be updated to make 4.3.a consistent with 4.3.e.

---

## Overall Assessment

**APPROVED.** All three issues from the first review are correctly resolved. The full implementation is now correct: Decimal math throughout, clean architecture (no DB/service dependencies), 429/Retry-After handling, 5xx immediate raise, timeout/network-error retry, coinbase tx UTXO parsing, Kaspa `is_accepted` filtering, cursor pagination, BTC summary/UTXO fallback, all URLs HTTPS, no secrets in code, `respx==0.23.1` compatible with `httpx==0.28.1`.
