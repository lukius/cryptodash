# T19 Review: HD Wallet — DerivedAddressRepository

**Reviewer**: Tech Lead
**Date**: 2026-04-13
**Verdict**: APPROVED (pass 2 of 2)

---

## Automated Checks

### Pass 1 (initial review)

| Check | Result |
|---|---|
| `ruff check backend/ tests/` | PASS |
| `ruff format --check backend/ tests/` | PASS |
| `pytest tests/backend/ -v` | PASS — 357 passed, 0 failed |

### Pass 2 (after developer fixes)

| Check | Result |
|---|---|
| `ruff check backend/ tests/` | PASS |
| `ruff format --check backend/ tests/` | PASS |
| `pytest tests/backend/ -v` | PASS — 359 passed, 0 failed |

All T19-specific tests pass:
- `test_derived_address_repo_replace_all` PASSED
- `test_derived_address_repo_cap_200` PASSED
- `test_derived_address_repo_get_by_wallet_empty` PASSED
- `test_derived_address_repo_replace_all_idempotent` PASSED
- `test_derived_address_repo_replace_all_empty` PASSED (new)
- `test_derived_address_repo_replace_all_atomicity` PASSED (new)

---

## Issues

### Pass 1 issues (all resolved)

| # | Severity | Description | Status |
|---|---|---|---|
| 1 | Medium | No test for `replace_all` with 0 addresses | RESOLVED — `test_derived_address_repo_replace_all_empty` added |
| 2 | Medium | Atomicity of `replace_all` not tested under simulated mid-insert failure | RESOLVED — `test_derived_address_repo_replace_all_atomicity` added |
| 3 | Low | `make_derived_address_entries` docstring said "descending" but generates ascending values | RESOLVED — docstring corrected to "ascending" |

### Pass 2 issues

None.

---

## Pass 2 Test Quality Notes

Both new tests are correct and well-constructed.

**`test_derived_address_repo_replace_all_empty`**: Exercises `replace_all(wallet_id, [], _now())` against a real wallet, flushes, asserts return value is 0 and `get_by_wallet` returns `[]`. Covers the edge case cleanly.

**`test_derived_address_repo_replace_all_atomicity`**: Uses `async with db_session.begin_nested() as savepoint` to isolate the failing `replace_all` call. A `failing_add` closure raises `RuntimeError` on the second call to `db_session.add`, simulating a crash mid-insert. The `RuntimeError` is caught inside the `async with` block, `await savepoint.rollback()` is called explicitly before block exit. SQLAlchemy's `SessionTransaction.__exit__` checks `_transaction_is_active()` before attempting a commit — since the savepoint was already rolled back, it calls `close()` instead and does not attempt a spurious commit. The outer transaction remains intact, and the initial two rows survive. The test structure is sound and the assertions are specific: it checks both count and the exact address set of surviving rows.

---

## Correctness Assessment

### Does `replace_all` atomically delete + insert in one transaction?

**Effectively yes, with a caveat.** The delete and all `self.db.add()` calls are buffered in the SQLAlchemy async session's pending state. No explicit flush is issued inside `replace_all`. Because `replace_all` is not `async with self.db.begin()` scoped, the atomicity guarantee depends on the caller not flushing between the call and any subsequent rollback. In practice all callers own the session lifecycle and flush after the full call, so this holds. However, it is implicit and untested (Issue 2 above). The implementation does not misuse the session — it correctly avoids calling `commit()` or `flush()` inside the repository, leaving transaction control to the service layer, consistent with the project's existing repository patterns (see `snapshot.py`).

### Is the 200-address cap applied before insert, top 200 by `balance_sat` desc?

**Yes.** Lines 34–36 of `derived_address.py`:
```python
top = sorted(addresses, key=lambda x: x["balance_sat"], reverse=True)[
    :_MAX_DERIVED_ADDRESSES
]
```
Python's `sorted()` with a `reverse=True` key produces descending order. The slice `[:200]` takes the top 200. Cap is applied in-memory before any DB writes.

### Does the return value from `replace_all` correctly reflect the pre-cap total count?

**Yes.** `total = len(addresses)` is captured at line 32, before the sort and cap. It is returned at line 53 after all inserts.

### Does `get_by_wallet` return rows ordered by `balance_sat` desc?

**Yes.** The query uses `.order_by(DerivedAddress.balance_sat.desc())`, ordering on the integer column, not on the string `current_balance_native`. This correctly avoids the SQLite string-sort pitfall documented in TECH_SPEC_HD_WALLETS.md §4.6.

### Does `replace_all` handle 0 addresses correctly?

**Yes — confirmed by test.** With an empty list: `total=0`, `top=[]`, the DELETE executes, the loop body never runs, `0` is returned. Now covered by `test_derived_address_repo_replace_all_empty`.

---

## Architecture Assessment

**Conforms to the repository pattern.** The class:
- Takes `AsyncSession` as constructor argument (consistent with all other repositories).
- Uses `sqlalchemy.delete` and `select` via `await self.db.execute(...)` — no blocking I/O.
- Contains no business logic, no HTTP concepts, no external API calls.
- Leaves transaction control (flush/commit/rollback) entirely to the caller.

The `__init__.py` export is correct and alphabetically consistent with the existing list.

---

## Security Assessment

No SQL injection risk. All queries use SQLAlchemy ORM expressions with parameterized bindings. No raw string interpolation into SQL. No sensitive data handled. No auth concerns (repository layer, called from authenticated service layer).

---

## Spec Alignment

The implementation aligns with the **revised** spec in TECH_SPEC_HD_WALLETS.md §4.6 (the note that adds `balance_sat` for ordering and revises both `replace_all` and `get_by_wallet`). The earlier paragraph in §4.6 shows a draft using `balance_btc` for sorting — the implementation correctly uses `balance_sat` per the revised decision, matching T19.md's notes.

FR-H15 (200-address cap) is enforced in the repository layer as required.

---

## Summary

All three issues from pass 1 have been correctly resolved. No new issues found in pass 2. The implementation and test suite are complete and correct. T19 is approved.
