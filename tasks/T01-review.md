# T01 Review: Backend Project Scaffolding

**Reviewer:** Tech Lead
**Date:** 2026-04-12
**Verdict:** APPROVED (after fixes)

---

## Re-review: 2026-04-12

All four issues from the first review are resolved:

1. `backend/cli.py` created — `from backend.cli import reset_password` imports cleanly. Implementation matches TECH_SPEC.md Section 6.2; lazy import of `AuthService` is a correct forward-compatibility choice for scaffolding.
2. `ruff format --check backend/ tests/` exits 0 — 26 files already formatted.
3. `grep -rn "utcnow" backend/ tests/` returns no matches.
4. `pytest tests/backend/ -v` — 3/3 passed, zero warnings.

---

## Original Review (first pass — CHANGES_REQUIRED)

---

## Overall Assessment

The scaffolding is largely solid — project structure, config, database engine, Alembic
wiring, conftest, and the three smoke tests are all correct and spec-aligned. The ORM
model stubs are minimal, faithful copies of the spec, and do not block T02. Two issues
require fixes before T01 can be closed: `backend/cli.py` is missing (a broken import
in `run.py`), and `ruff format` fails on 7 files. One medium issue (deprecated
`datetime.utcnow()`) and one low-severity issue (Python version mismatch) are also
noted.

---

## Issues

---

### Issue 1: `backend/cli.py` does not exist — `run.py` will crash on `reset-password`

**Severity:** Critical

**Component:** backend/cli.py, run.py

**File(s):** `run.py:29`

**Problem:**
`run.py` imports `from backend.cli import reset_password` inside the
`reset-password` branch. `backend/cli.py` was never created. Running
`python run.py reset-password` raises `ModuleNotFoundError` immediately.
This is a broken acceptance criterion and a broken CLI feature.

**Spec reference:**
> "Password reset CLI (`backend/cli.py`): ..."
> — specs/TECH_SPEC.md, Section 6.2

**Evidence:**
```
$ ls backend/cli.py
ls: cannot access 'backend/cli.py': No such file or directory
```

**Expected:** `backend/cli.py` exists and defines `async def reset_password()`.

**Actual:** File absent; import fails at runtime.

**Suggested fix:** Create `backend/cli.py` with the exact implementation shown in
specs/TECH_SPEC.md Section 6.2.

---

### Issue 2: `ruff format` fails — 7 files are not formatted

**Severity:** High

**Component:** backend/, tests/backend/

**Files:**
- `backend/database.py`
- `backend/models/balance_snapshot.py`
- `backend/models/price_snapshot.py`
- `backend/models/wallet.py`
- `backend/repositories/config.py`
- `tests/backend/conftest.py`
- `tests/backend/test_database.py`

**Problem:**
`ruff format --check backend/ tests/` exits non-zero. CLAUDE.md lists
`ruff format backend/ tests/` as a required lint step. The CI will
fail and the code is inconsistent with the project standard.

**Evidence:**
```
$ ruff format --check backend/ tests/
Would reformat: backend/database.py
Would reformat: backend/models/balance_snapshot.py
Would reformat: backend/models/price_snapshot.py
Would reformat: backend/models/wallet.py
Would reformat: backend/repositories/config.py
Would reformat: tests/backend/conftest.py
Would reformat: tests/backend/test_database.py
7 files would be reformatted, 18 files already formatted
```

**Expected:** `ruff format --check` exits 0.

**Suggested fix:** Run `ruff format backend/ tests/` and commit the result.

---

### Issue 3: `datetime.utcnow()` is deprecated in Python 3.12+

**Severity:** Medium

**Component:** backend/repositories/config.py

**File(s):** `backend/repositories/config.py:20, 40, 42`

**Problem:**
`datetime.utcnow()` is deprecated as of Python 3.12 and scheduled for removal.
The project targets Python 3.11+, but `.venv` is running Python 3.12.3 (per
pytest header), so the deprecation warning fires on every test run today.
More importantly, `datetime.utcnow()` returns a naive datetime — the spec stores
all timestamps as UTC, and naive datetimes cannot be distinguished from local time
if the host TZ is ever not UTC.

**Evidence:**
```
DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for
removal in a future version. Use timezone-aware objects to represent datetimes
in UTC: datetime.datetime.now(datetime.UTC).
  backend/repositories/config.py:20
```

**Expected:** `datetime.now(timezone.utc)` or `datetime.now(UTC)` (Python 3.11+
alias) used everywhere a UTC timestamp is needed.

**Actual:** `datetime.utcnow()` used in three places in `config.py`.

**Note:** The same pattern exists in `backend/models/user.py:16`
(`default=datetime.utcnow`). That model field default is also naive and deprecated,
though it will not yet warn at import time (only when the ORM calls it).

**Suggested fix:** Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)`
across `backend/repositories/config.py` and `backend/models/user.py`. Import
`from datetime import datetime, timezone`.

---

### Issue 4: Python 3.12 in `.venv` — version mismatch with spec

**Severity:** Low

**Component:** .venv / environment

**Problem:**
`pytest` reports `python3.12.3` (from `.venv/pyvenv.cfg`). The spec and CLAUDE.md
both say Python 3.11+. This is not a code defect, but `run.py` enforces `>= 3.11`
and the project should be tested on the minimum supported version. Running only on
3.12 may hide 3.11-incompatible syntax or typing usage.

**Expected:** Development and CI use Python 3.11 (minimum supported).

**Actual:** `.venv` uses Python 3.12.

**Note:** This is an environment/infra observation, not a blocker for the developer.
Worth tracking.

---

## Automated Check Results

| Check | Result |
|-------|--------|
| `ruff check backend/ tests/` | PASS (no lint errors) |
| `ruff format --check backend/ tests/` | FAIL (7 files need reformatting) |
| `pytest tests/backend/ -v` | PASS (3/3) |
| `python -c "from backend.config import config; print(config.db_path)"` | PASS |
| `python -c "import asyncio; from backend.database import init_db; asyncio.run(init_db())"` | PASS |
| `alembic current` | PASS |

---

## Spec Alignment Notes

- `backend/config.py` — exact match to TECH_SPEC.md Section 6.1.
- `backend/database.py` — WAL mode, foreign keys, `create_all`, config seeding all present;
  signature extended with optional `engine`/`session_factory` params (good: enables test isolation).
- `run.py` — exact match to TECH_SPEC.md Section 6.2, except the referenced `backend/cli.py` is missing (Issue 1).
- `alembic.ini` + `backend/migrations/env.py` — correctly wired for async SQLite.
- `backend/migrations/script.py.mako` — standard template, correct.
- `tests/backend/conftest.py` — provides `db_engine`, `db_session`, and `test_client` fixtures,
  each backed by fresh in-memory SQLite. Isolation is correct. The `test_client` fixture
  gracefully stubs the app until T10 delivers `backend/app.py`. Auth helper fixture (create
  test user + session) is absent — that is acceptable for T01 scope; T05/T06 will add it.
- ORM model stubs (T02 scope-creep) — all 7 models faithfully match the spec's Section 5.1
  column definitions, constraints, and relationships. They do not block T02.
- `requirements-dev.txt` — pinned versions match TECH_SPEC.md Section 1.5 exactly.
  `httpx` is omitted as a dev dep but it is already in `requirements.txt`, which
  `requirements-dev.txt` includes via `-r requirements.txt`. No gap.

---

## Spec Ambiguities / Gaps Discovered

None found during this review.
