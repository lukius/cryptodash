# T03: Repository Layer

**Status**: done
**Layer**: backend
**Assignee**: developer
**Depends on**: T02

## Context

The repository layer is the sole owner of all SQL queries. Services never touch SQLAlchemy directly
— they call repository methods. This strict boundary makes services testable with mock repos and
keeps SQL in one place. All five repository files must be complete before services (T05, T07, T08,
T09) can be written.

> "Repository Layer (DAL): SQLAlchemy async + SQLite ... Repositories expose CRUD methods; keep
> raw SQL/SQLAlchemy query construction internal."
> — specs/TECH_SPEC.md, Section 3.2

## Files owned

- `backend/repositories/user.py` (create)
- `backend/repositories/session.py` (create)
- `backend/repositories/wallet.py` (create)
- `backend/repositories/transaction.py` (create)
- `backend/repositories/snapshot.py` (create)
- `backend/repositories/config.py` (create)
- `backend/repositories/__init__.py` (modify — re-export all repos)
- `tests/backend/test_repositories.py` (create)

## Subtasks

- [ ] ST1: Implement `UserRepository` — `create(user)`, `get_by_username(username) -> User | None`,
      `get_by_id(id) -> User | None`, `update_password_hash(user_id, new_hash)`.
- [ ] ST2: Implement `SessionRepository` — `create(session)`, `get_by_token(token) -> Session | None`,
      `delete_by_token(token)`, `delete_all_for_user(user_id)`,
      `delete_expired(before: datetime)`.
- [ ] ST3: Implement `WalletRepository` — `create(wallet)`, `get_by_id(id) -> Wallet | None`,
      `list_all(user_id) -> list[Wallet]`, `count_by_user(user_id) -> int`,
      `exists_by_address(network, normalized_address, user_id) -> bool`,
      `tag_exists(tag, user_id, exclude_id=None) -> bool`,
      `update_tag(wallet_id, new_tag)`, `delete(wallet_id)`.
- [ ] ST4: Implement `TransactionRepository` — `bulk_create(transactions)`,
      `get_latest_for_wallet(wallet_id) -> Transaction | None` (by block_height or timestamp),
      `exists_by_hash(wallet_id, tx_hash) -> bool`,
      `compute_balance(wallet_id) -> Decimal | None` (sum of all amounts).
- [ ] ST5: Implement `BalanceSnapshotRepository` — `create(snapshot)`, `bulk_create(snapshots)`,
      `get_latest_for_wallet(wallet_id) -> BalanceSnapshot | None`,
      `get_range(wallet_id, from_dt, to_dt) -> list[BalanceSnapshot]`,
      `get_nearest_before(wallet_id, dt) -> BalanceSnapshot | None`.
- [ ] ST6: Implement `PriceSnapshotRepository` — `create(snapshot)`, `bulk_create(snapshots)`,
      `get_latest(coin) -> PriceSnapshot | None`,
      `get_range(coin, from_dt, to_dt) -> list[PriceSnapshot]`,
      `get_nearest_before(coin, dt) -> PriceSnapshot | None`.
- [ ] ST7: Implement `ConfigRepository` — `get(key) -> str | None`, `set(key, value)`,
      `set_default(key, default_value)` (only writes if key not present).
- [ ] ST8: Write `tests/backend/test_repositories.py` — test each method against the in-memory test DB,
      including: cascade delete verification, duplicate detection, range queries, compute_balance.

## Acceptance criteria

- [ ] `pytest tests/backend/test_repositories.py -v` passes with no failures.
- [ ] `WalletRepository.exists_by_address` correctly detects BTC duplicates case-insensitively (test).
- [ ] `TransactionRepository.compute_balance` returns the correct sum of signed amounts (test).
- [ ] `BalanceSnapshotRepository.get_nearest_before` returns the closest snapshot before a given
      datetime, not after (test).
- [ ] `ConfigRepository.set_default` does not overwrite an existing key (test).
- [ ] `ruff check backend/repositories/` exits 0.

## Notes

- `tag_exists` must do a case-insensitive comparison: `lower(tag) = lower(:tag)`. This mirrors the
  spec business rule that tags are unique case-insensitively (FR-005, specs/FUNC_SPEC.md §5.1.d).
- `bulk_create` for transactions should use `INSERT OR IGNORE` semantics (skip rows with duplicate
  `(wallet_id, tx_hash)`) to implement deduplication at the DB level (FR-027).
- All methods must accept an `AsyncSession` injected via the constructor, not create their own.
