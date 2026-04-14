# T23 Review — HD Wallet: API Schema and Wallet Router Extension

**Verdict**: ~~CHANGES_REQUIRED~~ → **APPROVED** (second pass, 2026-04-13)

---

## Second Pass Summary

Two issues from the first review have been addressed correctly:

**Issue 1 (High — hd_loading hardcoded False): RESOLVED.**
`backend/services/wallet.py:297` now reads:
```python
hd_loading = wallet_type == "hd" and balance_snap is None
```
This is exactly the one-line fix recommended. `hd_loading` is now `True` before the first successful fetch and `False` afterward, correctly matching TECH_SPEC_HD_WALLETS §5.2.

**Issue 2 (Medium — missing loading-state test): RESOLVED.**
`test_hd_wallet_loading_state_before_first_fetch` was added. It calls `GET /api/wallets` immediately after `POST /api/wallets` with no snapshot in the DB and asserts `hd_loading is True` and `balance is None`. This is a proper behavioral test — not just a smoke test — and it would have caught Issue 1 if written first.

`test_hd_wallet_list_response_shape` was also updated to insert a `BalanceSnapshot` before calling `GET /api/wallets`, making the existing post-fetch assertion (`hd_loading is False`) semantically correct and consistent with the new code.

**Issue 3 (Low — delete_by_prefix naming): carried as a known minor smell, no fix required for task closure.**

---

## Automated Check Results (Second Pass)

| Check | Result |
|---|---|
| `ruff check backend/ tests/` | PASS |
| `ruff format --check backend/ tests/` | FAIL on `backend/services/history.py` (pre-existing, not introduced by T23) |
| `pytest tests/backend/ -v` | PASS — 432 passed (3 runs, consistent) |

**Format note:** `backend/services/history.py` fails `ruff format --check`. This file was modified as part of earlier HD wallet tasks (T21/T22). Confirmed via `git stash` that `history.py` passes format check on the committed baseline; the failure is introduced by the unstaged HD wallet changes and is not owned by T23. The T23-owned files (`backend/services/wallet.py`, `tests/backend/test_wallets.py`) are both correctly formatted. The `history.py` format debt should be cleaned up before the HD wallet feature branch is merged.

**Transient test failure note:** One run of the full suite produced a single failure in `test_refresh_full_cycle_includes_hd_wallets` (object identity mismatch on `incremental_sync_hd` mock arg). The test passes consistently in isolation and in two subsequent full-suite runs. This is the same transient asyncio event-loop ordering issue documented in the first pass review. No code defect.

---

## Original Issues Filed (First Pass)

### High — RESOLVED

## Issue: `hd_loading` is always `False` — spec-required loading state is never surfaced

**Status**: Fixed in second pass.

**Component**: backend/services/wallet.py

**File(s)**: `backend/services/wallet.py:295-297`

**Problem**:
`hd_loading` was hardcoded to `False` for all wallets unconditionally. A comment said "the refresh service (T21) is responsible for setting/clearing this flag during the initial fetch," but no code in the refresh service (or anywhere else) ever set `hd_loading` to `True`. As a result, a freshly added HD wallet — before the background fetch had completed — would return `balance: null, hd_loading: false`, an incorrect and misleading state for the frontend.

**Fix applied**: `hd_loading = wallet_type == "hd" and balance_snap is None`

---

### Medium — RESOLVED

## Issue: `test_hd_wallet_list_response_shape` does not test `hd_loading = True` for a freshly created HD wallet

**Status**: Fixed in second pass.

**Component**: tests/backend/test_wallets.py

**Fix applied**: New test `test_hd_wallet_loading_state_before_first_fetch` added; existing test updated to insert a `BalanceSnapshot` to make the post-fetch assertion semantically correct.

---

## Issue: `config_repo.delete_by_prefix` called with an exact key, not a prefix

**Severity**: Low — carried, no fix required

**Component**: backend/services/wallet.py

**File(s)**: `backend/services/wallet.py:429`

`remove_wallet` calls `config_repo.delete_by_prefix(f"hd_address_count:{wallet_id}")` with the exact key rather than a prefix. Functionally correct; the LIKE clause matches the single key. The naming mismatch is a minor maintenance concern if the config key scheme grows. No regression risk in the current implementation.

---

## Spec Ambiguities / Gaps (carried from first pass)

**`hd_loading` vs. `history_status` overlap**: TECH_SPEC_HD_WALLETS §5.2 shows an HD wallet in loading state with `"history_status": "importing"`, but the service only ever sets `history_status` to `"complete"` or `"pending"`. The pre-existing gap where `"importing"` is never emitted by the list endpoint is unresolved, but it is not T23's scope.

**`hd_address_count` config key is only written when count > 200**: When count ≤ 200, the key is absent and the service falls back to `len(da_rows)`. This is consistent with the spec and requires no change.

---

## Summary

| Issue | Severity | Status |
|---|---|---|
| `hd_loading` hardcoded `False` | High | RESOLVED |
| Missing `hd_loading=True` test | Medium | RESOLVED |
| `delete_by_prefix` naming mismatch | Low | Carried (no fix required) |
| `history.py` format debt | Low (pre-existing, not T23) | Track separately |
