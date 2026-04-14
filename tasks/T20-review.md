# T20 Review: HD Wallet — Extended Key Validation and WalletService Extension

**Verdict (pass 1)**: CHANGES_REQUIRED
**Verdict (pass 2)**: APPROVED

**Reviewer**: Tech Lead
**Date**: 2026-04-13

---

## Pass 2 Summary (2026-04-13)

All five issues from pass 1 are correctly resolved. 419 backend tests pass (one new test added). Ruff lint and format checks are clean. No new issues found. The implementation is approved.

**Changes verified:**

| Issue | Fix | Result |
|---|---|---|
| Issue 1 — race condition | `await self.db.commit()` added before `create_task` in `_add_hd_wallet` | Correct. Commit is now at line 481, before line 484. |
| Issue 2 — case-insensitive dedup | `exists_by_address_exact()` added to `WalletRepository`; `_add_hd_wallet` uses it | Correct. New method uses `Wallet.address == address` (no `func.lower()`). |
| Issue 3 — config key test | `test_hd_wallet_remove_cascades` now inserts `hd_address_count:{wallet_id}` and asserts it's gone after delete | Correct. Both the ORM cascade and `delete_by_prefix` paths are verified. |
| Issue 4 — wrong chars test | `test_validate_extended_public_key_invalid_base58_char` added | Correct. Replaces char at position 50 with `'0'`; asserts "checksum verification failed". |
| Issue 5 — `ExtendedKeyValidationError` | `_add_hd_wallet` now raises `ExtendedKeyValidationError(error)` instead of `AddressValidationError(error)` | Correct. `test_service_add_hd_wallet_invalid_raises` asserts `ExtendedKeyValidationError` specifically and also verifies the parent-class catch still works. |

**One observation (no action required):** The service-layer tests for `_add_hd_wallet` (e.g., `test_service_add_hd_wallet_creates_hd_type`) call `await db.commit()` after the method returns. Since `_add_hd_wallet` now commits internally, the test's `await db.commit()` is a redundant no-op. This is harmless and requires no change.

---

## Automated Check Results (Pass 2)

| Check | Result |
|---|---|
| `ruff check backend/ tests/` | PASS |
| `ruff format --check backend/ tests/` | PASS |
| `pytest tests/backend/ -v` | PASS — 419 passed |
| `pytest tests/backend/test_hd_wallets.py -v` | PASS — 58 passed |

---

## Original Assessment (Pass 1)

The implementation was largely correct and all 418 backend tests passed. The core logic — Base58Check helpers, `detect_input_type`, `validate_extended_public_key`, `normalize_to_xpub`, `_add_hd_wallet`, `_generate_hd_default_tag`, `_fetch_initial_hd_data`, config key cleanup on remove — was present and functional.

Four issues required fixes: one high-severity race condition in the background-task dispatch flow (violating the spec's explicit `commit-before-create_task` ordering), one medium-severity spec deviation in the duplicate-detection query (case-insensitive vs. case-sensitive), one medium-severity gap in the `test_hd_wallet_remove_cascades` test (config key cleanup not verified), and one medium-severity test coverage gap (the "wrong chars" validation case absent).

---

## Automated Check Results

| Check | Result |
|---|---|
| `ruff check backend/ tests/` | PASS |
| `ruff format --check backend/ tests/` | PASS |
| `pytest tests/backend/ -v` | PASS — 418 passed |
| `pytest tests/backend/test_hd_wallets.py -v` | PASS — 57 passed |
| `pytest tests/backend/test_wallets.py -v` | PASS — includes 2 new HD routing tests |

---

## Issues

---

### Issue 1: Background task fired before DB commit — race condition per spec

**Severity**: High

**Component**: backend/services/wallet.py

**File(s)**: `backend/services/wallet.py:471–474`

**Problem**:
`_add_hd_wallet` calls `asyncio.create_task(self._fetch_initial_hd_data(wallet))` and returns without committing the database transaction. The router (`backend/routers/wallets.py:96`) calls `await db.commit()` after `add_wallet` returns. In CPython's single-threaded asyncio, the scheduled task will not run until the current coroutine yields — and the next yield after `create_task` is the `await db.commit()` in the router — so in practice the wallet IS committed before the task runs. However:

1. This relies on an implicit event-loop scheduling guarantee that is not part of asyncio's public contract.
2. The spec explicitly specifies `await self.db.commit()` **inside** `_add_hd_wallet`, before `create_task` (TECH_SPEC_HD_WALLETS.md §4.7.b).
3. Any future refactor that adds an `await` between `create_task` and the router's `await db.commit()` — or that runs the task in a different executor — would produce a real race where `_fetch_initial_hd_data` executes against an uncommitted wallet, causing the refresh service to find no wallet in the DB.

The same pattern exists in the individual-wallet `add_wallet` path, but this review is scoped to T20 changes.

**Spec reference**:
> ```python
> await self.wallet_repo.create(wallet)
> await self.db.commit()
>
> # 6. Trigger background tasks
> asyncio.create_task(self._fetch_initial_hd_data(wallet))
> ```
> — TECH_SPEC_HD_WALLETS.md §4.7.b

**Expected**:
`_add_hd_wallet` calls `await self.db.commit()` immediately after `wallet_repo.create(wallet)`, before scheduling the background task. The router's `await db.commit()` after `add_wallet` becomes a no-op for the HD path (committing a clean session is harmless).

**Actual**:
`_add_hd_wallet` schedules `create_task` without committing. The commit happens later in the router.

**Suggested fix**:
Add `await self.db.commit()` after `await self.wallet_repo.create(wallet)` in `_add_hd_wallet`, immediately before `asyncio.create_task(...)`. This matches the spec's ordering and removes the implicit reliance on event-loop scheduling.

---

### Issue 2: HD wallet duplicate check uses case-insensitive comparison — contradicts FR-H06

**Severity**: Medium

**Component**: backend/repositories/wallet.py

**File(s)**: `backend/repositories/wallet.py:51–60`

**Problem**:
`exists_by_address` compares addresses using `func.lower(Wallet.address) == normalized_address.lower()`, making the duplicate check case-insensitive. `_add_hd_wallet` calls this with the raw key (not lowercased). As a result, if a user added `xpub6abc...` and then attempted to add `XPUB6abc...` (hypothetically), they would get a duplicate error even though these are not the same key string. FR-H06 specifies exact-match, case-sensitive comparison.

In practice the impact is low — `validate_extended_public_key` rejects uppercase prefixes before the duplicate check ever runs (because `XPUB` is not in `_XPUB_VERSIONS`). However, the case-insensitive path violates the spec's stated contract and creates a subtle correctness gap if the validation logic ever changes.

**Spec reference**:
> "FR-H06: The system shall reject a duplicate HD wallet (same extended public key already registered) with the message: 'This HD wallet key is already being tracked.' Comparison is exact-match (case-sensitive)."
> — specs/FUNC_SPEC_HD_WALLETS.md §5.1.b

> "Check duplicate (exact string match, case-sensitive per FR-H06)"
> — TECH_SPEC_HD_WALLETS.md §4.7.b (code comment)

**Expected**:
The duplicate check for HD wallets uses an exact-string comparison. Either the repository gets a separate method (e.g., `exists_by_address_exact`) or `_add_hd_wallet` compares against the stored `address` column directly without case-folding.

**Actual**:
`exists_by_address` applies `func.lower()` on both sides, making HD wallet duplicate detection case-insensitive.

**Suggested fix**:
In `_add_hd_wallet`, perform the duplicate check with a case-sensitive query. The simplest approach is to add a separate `exists_by_address_exact(user_id, network, address)` method to `WalletRepository` that omits the `func.lower()` wrapping.

---

### Issue 3: `test_hd_wallet_remove_cascades` does not verify config key deletion

**Severity**: Medium

**Component**: tests/backend/test_hd_wallets.py

**File(s)**: `tests/backend/test_hd_wallets.py:481–511`

**Problem**:
The test verifies that `DerivedAddress` rows are deleted on HD wallet removal (cascade via ORM) but does NOT verify that the `hd_address_count:{wallet_id}` config key is deleted via `config_repo.delete_by_prefix`. This is the behavior added in ST10, and it is completely untested. If the `delete_by_prefix` call were removed from `remove_wallet`, no test would fail.

**Spec reference**:
> "ST10: Extend `remove_wallet()` to call `config_repo.delete_by_prefix(f"hd_address_count:{wallet_id}")` after deleting the wallet"
> — tasks/T20.md, Subtask ST10

> "These keys are deleted automatically when the parent wallet is deleted (cascade via the wallet delete flow — call `config_repo.delete_by_prefix(...)` in `WalletService.remove_wallet()`)."
> — TECH_SPEC_HD_WALLETS.md §6.1

**Expected**:
`test_hd_wallet_remove_cascades` (or a new test) sets a `hd_address_count:{wallet_id}` config entry, deletes the wallet, and asserts the config key is gone.

**Actual**:
No test exercises the config key cleanup path.

**Suggested fix**:
In `test_hd_wallet_remove_cascades`, after inserting the `DerivedAddress` row, also insert a `Configuration` row with key `f"hd_address_count:{wallet_id}"` and value `"250"`. After the wallet DELETE, assert that the config key no longer exists in the database.

---

### Issue 4: No test for "wrong chars" (invalid Base58 characters) validation path

**Severity**: Medium

**Component**: tests/backend/test_hd_wallets.py

**Problem**:
The review spec requires 9 validation cases: valid xpub, valid ypub, valid zpub, testnet, bad prefix, bad length, bad checksum, wrong chars, and duplicate. The "wrong chars" case is absent. An xpub-prefixed 111-char string containing an invalid Base58 character (e.g., `'0'`, `'O'`, `'I'`, `'l'`) would pass the prefix and length checks, then fail in `_b58decode` with `ValueError("Invalid Base58 character: ...")`, which is caught by the blanket `except ValueError` in `validate_extended_public_key` and returned as the "checksum verification failed" message. This conflation is an acceptable UX trade-off, but the path needs a test.

**Expected**:
A test covering a string with the `xpub` prefix, length 111, but containing an invalid Base58 character (e.g., `"0"` in position 50). The test should assert `validate_extended_public_key` returns a non-None error string, and the HTTP endpoint returns 400.

**Actual**:
No such test exists. `test_validate_extended_public_key_bad_checksum` covers a similar code path (wrong final bytes) but not the "invalid character" path.

---

### Issue 5: `_b58decode` off-by-one for all-"1" strings — latent correctness defect

**Severity**: Low

**Component**: backend/services/wallet.py

**File(s)**: `backend/services/wallet.py:37–46`

**Problem**:
`_b58decode("1")` returns `b"\x00\x00"` (2 zero bytes) instead of `b"\x00"` (1 zero byte). The cause: when `num == 0` (string is `"1"`), `byte_len = 1`, so `num.to_bytes(1, "big")` = `b"\x00"`. Combined with `leading_zeros = 1`, the result is `b"\x00" * 1 + b"\x00" = b"\x00\x00"`. The reference spec implementation uses `(num.bit_length() + 7) // 8 or 1` which produces the same bug (0//8 = 0, 0 or 1 = 1). So the implementation faithfully reproduces the spec's bug.

This does not affect real xpub/ypub/zpub keys (they have no leading `"1"` characters in Base58 encoding, as confirmed by checking test vectors). Round-trip encode/decode of all real extended keys works correctly.

**Expected**:
For a string of k consecutive `"1"` characters, `_b58decode` should return exactly k zero bytes.

**Actual**:
For a string of k consecutive `"1"` characters, `_b58decode` returns k+1 zero bytes.

**Note**: This defect exists in the spec's reference implementation as well. It is not introduced by the developer. No behavior is broken today. File this as a known technical debt item.

---

### Issue 6: `ExtendedKeyValidationError` is defined but never raised

**Severity**: Low

**Component**: backend/core/exceptions.py, backend/services/wallet.py

**File(s)**: `backend/core/exceptions.py:30`

**Problem**:
`ExtendedKeyValidationError` is defined as a subclass of `AddressValidationError` per the spec. However, it is never raised anywhere — the service raises `AddressValidationError(error)` directly. The class exists solely as a structural artifact. It is correctly defined (so the router's `except AddressValidationError` would catch it if raised), but as dead code at the raise site it reduces intent clarity. Future callers reading the code have no signal to distinguish HD validation errors from general address validation errors without checking the exception message string.

**Spec reference**:
> "class ExtendedKeyValidationError(AddressValidationError): ... Subclasses AddressValidationError so the existing 400 handler catches it without modification."
> — TECH_SPEC_HD_WALLETS.md §4.11

The spec note clarifies: "validate_extended_public_key returns strings (not exceptions). The service raises AddressValidationError(error_message)." — so the spec itself does not raise `ExtendedKeyValidationError`. This is a spec gap, not an implementation mistake.

**Suggested fix** (optional):
Change `_add_hd_wallet` to raise `ExtendedKeyValidationError(error)` instead of `AddressValidationError(error)`. This uses the class as intended and gives callers a richer exception hierarchy to work with.

---

### Issue 7: `hd_loading` flag is always `False` — spec field semantics not implemented

**Severity**: Low

**Component**: backend/services/wallet.py, backend/routers/wallets.py

**File(s)**: `backend/services/wallet.py:294`, `backend/routers/wallets.py:113`

**Problem**:
The `WalletResponse.hd_loading` field is specified to be `True` while the initial HD wallet fetch is in progress (TECH_SPEC_HD_WALLETS.md §5.2, "HD wallet loading state" example). The implementation always returns `False` for this field. There is no mechanism to track whether `_fetch_initial_hd_data` is running.

**Spec reference**:
> ```json
> {
>   "balance": null,
>   "history_status": "importing",
>   "hd_loading": true,
>   "derived_addresses": null,
>   "derived_address_count": null
> }
> ```
> — TECH_SPEC_HD_WALLETS.md §5.2 (HD wallet loading state)

**Note**: The spec does not specify the mechanism for tracking this state — no DB flag, no in-memory store. T20 does not own the refresh service, so implementing a real `hd_loading=True` state likely requires cross-task coordination (a process-level set of in-flight wallet IDs, or a DB flag set in the service). This may be a spec gap rather than a T20 deliverable. The field is included in the schema (correctly), but without a mechanism to set it, the frontend can never see `hd_loading=True`. File this as a follow-up for whoever owns the refresh/WS state in T21.

---

## Spec Ambiguities Discovered

1. **Spec §4.1.e note vs. edge case table for uppercase XPUB**: The note says `"XPUB6..."` (uppercase) falls through to `"unknown"` → "Invalid Bitcoin address format." But if `XPUB` is followed by enough characters to make the string 107–115 chars, the length heuristic fires first and routes to `"hd_wallet"` → "Unrecognized key format." The implementation and tests handle the length-triggered case correctly. The spec note only applies to short uppercase inputs.

2. **Acceptance criteria count mismatch**: T20.md AC states "all 29 tests" for `test_hd_wallets.py`, but the implementation delivers 57 tests. Two spec-listed tests (`test_hd_wallet_history_import`, `test_hd_wallet_incremental_sync`) are absent because they depend on T21/T22. The AC count in T20.md is incorrect — it should either say "at least 27 of the 29 spec tests (2 deferred to T21/T22)" or be updated to 57.

3. **`hd_loading` implementation mechanism**: The spec defines `hd_loading: true` as a response field but provides no mechanism for setting it. T20 cannot implement this without a cross-task state store. The spec should specify the mechanism (e.g., a `Configuration` key `"hd_loading:{wallet_id}"` set before `create_task` and cleared at the end of `_fetch_initial_hd_data`) and assign it to T20 or T21.

4. **`exists_by_address` signature divergence**: The spec's `_add_hd_wallet` code snippet calls `self.wallet_repo.exists_by_address("BTC", key)` (2 args: network, key), but the actual repository method takes 3 args: `(user_id, network, address)`. This is a spec typo — the implementation correctly passes `user_id`.

---

## Summary of Issues

| # | Title | Severity |
|---|---|---|
| 1 | Background task fired before DB commit | High |
| 2 | HD wallet duplicate check is case-insensitive, contradicts FR-H06 | Medium |
| 3 | `test_hd_wallet_remove_cascades` doesn't verify config key deletion | Medium |
| 4 | No test for "wrong chars" (invalid Base58 characters) validation path | Medium |
| 5 | `_b58decode` off-by-one for all-"1" strings (latent, no practical impact) | Low |
| 6 | `ExtendedKeyValidationError` defined but never raised | Low |
| 7 | `hd_loading` always `False` — spec semantic not implemented | Low |
