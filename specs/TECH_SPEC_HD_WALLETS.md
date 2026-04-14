# CryptoDash — Technical Specification Addendum: HD Wallet Support

**Version:** 1.0
**Date:** 2026-04-13
**Status:** Draft
**Source:** `specs/FUNC_SPEC_HD_WALLETS.md` v1.0
**Extends:** `specs/TECH_SPEC.md` v1.0

---

## 0. Scope and Reading Order

This document specifies only the changes required to add HD wallet support on top of the existing CryptoDash codebase (described in `TECH_SPEC.md`). Readers should be familiar with `TECH_SPEC.md` before reading this document. All sections here are additive or override-specific subsections of the base spec. Where this document is silent, base spec behavior applies unchanged.

---

## 1. Technology Stack Changes

### 1.1 New Dependencies

**No new Python dependencies are added.** The Base58Check encoding/decoding required for extended key validation and ypub/zpub conversion is implemented as a pure-Python utility using `hashlib` (already in stdlib). This avoids adding a `base58` library and keeps the dependency footprint minimal.

**No new frontend dependencies are added.** The HD badge and derived address list are implemented with existing Tailwind CSS utilities and Vue components.

### 1.2 External API: blockchain.info

A second Bitcoin API is introduced alongside Mempool.space, used exclusively for xpub queries.

| Property | Value |
|---|---|
| Base URL | `https://blockchain.info` |
| Protocol | REST over HTTPS, JSON |
| Auth | None (free tier, keyless) |
| Rate limit | Not officially documented; treated as 1 req/sec safe upper bound |
| Coverage | xpub (BIP32/BIP44), ypub/zpub via version-byte conversion (see §4.2) |

**Why blockchain.info and not Mempool.space:** Mempool.space's REST API does not expose an xpub/ypub/zpub aggregation endpoint. blockchain.info's `multiaddr` endpoint is the established public API for this purpose and is explicitly referenced in the functional spec brief as a confirmed capability. Blockchair supports all three key types natively but its free tier is limited to 30 calls/day, making it unsuitable for a refresh-cycle-integrated feature.

**Key endpoints used:**

| Endpoint | Purpose |
|---|---|
| `GET /multiaddr?active={xpub}&n=50&offset=0` | Fetch aggregate balance, derived address list, and paginated transaction list |

**`multiaddr` response structure (relevant fields):**

```json
{
  "wallet": {
    "final_balance": 123456789,
    "n_tx": 42
  },
  "addresses": [
    {
      "address": "bc1q...",
      "final_balance": 50000000,
      "n_tx": 3,
      "total_received": 100000000,
      "total_sent": 50000000
    }
  ],
  "txs": [
    {
      "hash": "abc...",
      "time": 1700000000,
      "block_height": 820000,
      "result": -50000,
      "inputs": [...],
      "out": [...]
    }
  ],
  "info": {
    "n_tx": 42,
    "n_unredeemed": 5
  }
}
```

- `wallet.final_balance`: aggregate confirmed balance in satoshis.
- `addresses`: ALL active derived addresses (those with at least one transaction). This list is complete in a single call — it is NOT affected by the `n`/`offset` pagination parameters (those only page the `txs` array).
- `txs`: paginated transaction list (50 per page, newest first). Paginate with `offset` to retrieve all.
- `info.n_tx`: total transaction count across the whole xpub — used to determine how many pages are needed.

---

## 2. Architecture Changes

### 2.1 New Component: XpubClient

```
backend/clients/xpub.py   — XpubClient: blockchain.info multiaddr endpoint
```

All other components already exist and are extended in-place.

**Updated data flow for HD wallets:**

```
Add HD Wallet
  → WalletService.add_wallet() detects HD wallet
    → validate_extended_public_key()
    → WalletRepository.create()
    → asyncio.create_task(_fetch_initial_hd_data())
      → RefreshService.refresh_single_hd_wallet()
        → XpubClient.get_xpub_summary()
          → stores BalanceSnapshot (aggregate)
          → DerivedAddressRepository.upsert_all()
      → HistoryService.full_import_hd()
        → XpubClient.get_xpub_transactions_all()
          → stores Transaction records (aggregate)
          → stores historical BalanceSnapshot records
```

### 2.2 Updated Component Responsibility Table

New / changed entries only:

| Component | Layer | Responsibility |
|---|---|---|
| **XpubClient** | External | Queries blockchain.info `multiaddr` for aggregate xpub balance, derived address list, and paginated transactions. |
| **WalletService** (extended) | Service | Detects HD wallet input, validates extended public keys, stores HD wallet records, generates "BTC HD Wallet #n" tags. |
| **RefreshService** (extended) | Service | Refreshes HD wallets via `XpubClient`; updates `DerivedAddress` cache on each successful fetch. |
| **HistoryService** (extended) | Service | Full and incremental history import at the aggregate xpub level using `XpubClient`. |
| **DerivedAddressRepository** | Repository | CRUD for the `derived_addresses` table; replaces the full list on each successful fetch. |

---

## 3. Project Structure Changes

New and modified files only. The complete tree is as described in `TECH_SPEC.md §3`, with the following additions:

```
backend/
│
├── models/
│   └── derived_address.py           # NEW: DerivedAddress ORM model
│
├── clients/
│   └── xpub.py                      # NEW: XpubClient (blockchain.info)
│
├── repositories/
│   └── derived_address.py           # NEW: DerivedAddressRepository
│
├── services/
│   └── wallet.py                    # MODIFIED: HD wallet detection, validation, add flow
│   └── refresh.py                   # MODIFIED: HD wallet refresh cycle
│   └── history.py                   # MODIFIED: HD wallet full import + incremental sync
│
├── schemas/
│   └── wallet.py                    # MODIFIED: WalletResponse with HD fields
│
└── migrations/versions/
    └── 002_hd_wallet_support.py     # NEW: Alembic migration

frontend/src/
│
├── components/
│   ├── wallet/
│   │   ├── HdBadge.vue              # NEW: "HD" badge component
│   │   └── DerivedAddressList.vue   # NEW: Expandable derived address table
│   │
│   └── (AddWalletDialog.vue)        # MODIFIED: xpub detection + helper text
│   └── (WalletTable.vue)            # MODIFIED: HD badge, expand/collapse row
│
├── types/
│   └── api.ts                       # MODIFIED: WalletResponse, DerivedAddressResponse
│
└── utils/
    └── validation.ts                # MODIFIED: client-side xpub format detection

tests/backend/
├── test_hd_wallets.py               # NEW: HD wallet service + validation tests
├── test_xpub_client.py              # NEW: XpubClient unit tests
└── test_wallets.py                  # MODIFIED: add HD wallet test cases
```

---

## 4. Component Specifications

### 4.1 Extended Key Validation

**File:** `backend/services/wallet.py` (new functions alongside existing `validate_btc_address`)

#### 4.1.a Interface

```python
def detect_input_type(raw_input: str) -> Literal["individual_btc", "hd_wallet", "kas", "unknown"]:
    """
    Determines the type of address/key input after normalization (strip + collapse whitespace).
    Used by WalletService to route BTC inputs to the correct validator.
    Does NOT perform full validation — only prefix/length heuristics.
    """

def validate_extended_public_key(key: str) -> str | None:
    """
    Validates an extended public key string.
    Returns None if valid; returns error message string if invalid.
    Input must already be normalized (stripped).
    Performs: prefix check → length check → Base58Check verification.
    """
```

#### 4.1.b Detection Logic (`detect_input_type`)

After normalization (`key.strip().replace("\n", "").replace(" ", "")`):

```python
def detect_input_type(raw: str) -> Literal["individual_btc", "hd_wallet", "kas", "unknown"]:
    s = raw.strip().replace("\n", "").replace(" ", "")

    # Kaspa: unambiguous prefix
    if s.startswith("kaspa:"):
        return "kas"

    # Extended key prefixes (mainnet and testnet)
    EXTENDED_PREFIXES = ("xpub", "ypub", "zpub", "tpub", "upub", "vpub")
    if any(s.startswith(p) for p in EXTENDED_PREFIXES):
        return "hd_wallet"

    # Known individual BTC address prefixes
    BTC_INDIVIDUAL_PREFIXES = ("1", "3", "bc1q", "bc1p")
    if any(s.startswith(p) for p in BTC_INDIVIDUAL_PREFIXES):
        return "individual_btc"

    # Length heuristic for unrecognized extended keys (FR-H05)
    if 107 <= len(s) <= 115:
        return "hd_wallet"  # Will fail validation with "unrecognized prefix" error

    return "unknown"
```

**Integration into `WalletService.add_wallet()`:** After normalization, call `detect_input_type()`. Route BTC inputs:
- `"individual_btc"` → existing `validate_btc_address()` path
- `"hd_wallet"` → new `validate_extended_public_key()` path → create HD wallet
- `"unknown"` → fall through to existing "Invalid Bitcoin address format." error

#### 4.1.c Validation Logic (`validate_extended_public_key`)

```python
import hashlib

# Mainnet extended key version bytes
_XPUB_VERSIONS = {
    "xpub": bytes.fromhex("0488B21E"),
    "ypub": bytes.fromhex("049D7CB2"),
    "zpub": bytes.fromhex("04B24746"),
}
_TESTNET_PREFIXES = {"tpub", "upub", "vpub"}

def validate_extended_public_key(key: str) -> str | None:
    """Returns None if valid, error message string if invalid."""
    # 1. Testnet check (before length check — better error message)
    if any(key.startswith(p) for p in _TESTNET_PREFIXES):
        return (
            "Testnet keys are not supported. "
            "Please export a mainnet key from your wallet."
        )

    # 2. Unrecognized prefix
    if not any(key.startswith(p) for p in _XPUB_VERSIONS):
        return (
            "Unrecognized key format. "
            "Bitcoin extended public keys start with xpub, ypub, or zpub."
        )

    # 3. Length check (exactly 111 characters)
    if len(key) != 111:
        return (
            f"Invalid extended public key. "
            f"Expected 111 characters, got {len(key)}."
        )

    # 4. Base58Check integrity
    try:
        _b58decode_check(key)
    except ValueError:
        return (
            "Invalid extended public key: checksum verification failed. "
            "Please re-export the key from your wallet."
        )

    return None  # Valid
```

#### 4.1.d Pure-Python Base58Check Implementation

```python
# backend/services/wallet.py (module-level helpers, not exported)

_BASE58_CHARS = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_BASE58_MAP = {c: i for i, c in enumerate(_BASE58_CHARS)}

def _b58decode(s: str) -> bytes:
    """Decode a Base58 string to bytes."""
    num = 0
    for char in s:
        if char not in _BASE58_MAP:
            raise ValueError(f"Invalid Base58 character: {char!r}")
        num = num * 58 + _BASE58_MAP[char]
    # Count leading '1' characters → leading zero bytes
    leading_zeros = len(s) - len(s.lstrip("1"))
    result = num.to_bytes((num.bit_length() + 7) // 8 or 1, "big")
    return b"\x00" * leading_zeros + result

def _b58decode_check(s: str) -> bytes:
    """
    Decode a Base58Check string. Raises ValueError if checksum fails.
    Returns the payload (without the 4-byte checksum).
    """
    decoded = _b58decode(s)
    if len(decoded) < 4:
        raise ValueError("Too short for Base58Check")
    payload, checksum = decoded[:-4], decoded[-4:]
    expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    if checksum != expected:
        raise ValueError("Base58Check checksum mismatch")
    return payload
```

**Why inline rather than a module:** These functions are only needed for xpub validation and key conversion (§4.2). Keeping them in `wallet.py` avoids creating a utility module for two small private functions.

#### 4.1.e Edge Cases

| Input | `detect_input_type` | `validate_extended_public_key` | Final behavior |
|---|---|---|---|
| `"xpub6Cu..."` (valid, 111 chars) | `hd_wallet` | `None` (valid) | HD wallet created |
| `"ypub6M..."` (valid, 111 chars) | `hd_wallet` | `None` (valid) | HD wallet created |
| `"tpub4..."` | `hd_wallet` | testnet error message | 400 error |
| `"xpub6Cu..."` (110 chars) | `hd_wallet` | length error | 400 error |
| `"xpub6Cu..."` (bad checksum) | `hd_wallet` | checksum error | 400 error |
| `"  xpub6Cu... "` (whitespace) | `hd_wallet` (after strip) | valid | HD wallet created |
| `"XPUB6..."` (uppercase) | `unknown` | — | "Invalid Bitcoin address format." |
| `"abcdefghij..."` (111 chars, no prefix) | `hd_wallet` (length heuristic) | unrecognized prefix | 400 error |
| `"bc1qxy..."` (42 chars) | `individual_btc` | — | existing BTC validation |

**Note on case sensitivity:** FR-H03 specifies that the prefix must be lowercase. `detect_input_type` does NOT lowercase the input before checking (it checks `key.startswith("xpub")` on the already-stripped value). An uppercase `XPUB` prefix falls through to `unknown`, then to "Invalid Bitcoin address format." This is correct per spec — the user will understand the error when they see it, and re-pasting from a wallet app (which always produces lowercase) will succeed.

---

### 4.2 ypub/zpub → xpub Conversion

blockchain.info's `multiaddr` endpoint accepts only xpub-format keys. ypub and zpub use different BIP32 version bytes but encode the same underlying key material. Converting them is a lossless version-byte substitution — it does NOT perform key derivation and is NOT "local address derivation" as defined in the func spec's out-of-scope clause.

```python
# backend/services/wallet.py

_XPUB_VERSION_BYTES = bytes.fromhex("0488B21E")
_KEY_TYPE_VERSIONS = {
    "xpub": bytes.fromhex("0488B21E"),
    "ypub": bytes.fromhex("049D7CB2"),
    "zpub": bytes.fromhex("04B24746"),
}

_BASE58_CHARS = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def _b58encode(data: bytes) -> str:
    """Encode bytes to Base58 string."""
    num = int.from_bytes(data, "big")
    result = []
    while num > 0:
        num, rem = divmod(num, 58)
        result.append(_BASE58_CHARS[rem])
    # Leading zero bytes → '1' characters
    leading = len(data) - len(data.lstrip(b"\x00"))
    return "1" * leading + "".join(reversed(result))

def _b58encode_check(payload: bytes) -> str:
    """Encode bytes with Base58Check (appends 4-byte checksum)."""
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return _b58encode(payload + checksum)

def normalize_to_xpub(key: str) -> str:
    """
    Convert an ypub or zpub key to xpub version bytes for API compatibility.
    xpub keys are returned unchanged.
    Precondition: key has already been validated by validate_extended_public_key().
    """
    prefix = key[:4]
    if prefix == "xpub":
        return key
    payload = _b58decode_check(key)
    # Replace first 4 bytes (version) with xpub version bytes
    xpub_payload = _XPUB_VERSION_BYTES + payload[4:]
    return _b58encode_check(xpub_payload)
```

**Storage:** The `extended_public_key` column stores the **original** key as supplied by the user (ypub or zpub). The xpub-normalized form is computed on the fly by `normalize_to_xpub()` when calling `XpubClient`. This preserves user intent and allows the UI to show "ypub" or "zpub" type information.

---

### 4.3 XpubClient

**File:** `backend/clients/xpub.py`

#### 4.3.a Interface

```python
import asyncio
from decimal import Decimal
from backend.clients.base import BaseClient

SATOSHI = Decimal("100000000")

class XpubClient(BaseClient):
    def __init__(self):
        super().__init__(base_url="https://blockchain.info", timeout=30.0)

    async def get_xpub_summary(self, xpub_normalized: str) -> "XpubSummary":
        """
        Fetches aggregate balance and the full active derived address list.
        The 'addresses' array in the multiaddr response is complete in a single
        call (not paginated by n/offset).
        Parameters:
          xpub_normalized: an xpub-format key (convert ypub/zpub first).
        Returns: XpubSummary with aggregate balance and list of DerivedAddressData.
        Raises: httpx.HTTPStatusError, httpx.RequestError on API failure.
        """

    async def get_xpub_transactions_all(self, xpub_normalized: str) -> list["XpubTransaction"]:
        """
        Fetches ALL transactions for the xpub by paginating through the
        multiaddr endpoint with offset=0, 50, 100, ... until the txs array
        is empty or we've retrieved all n_tx transactions.
        Returns list of XpubTransaction sorted oldest-first.
        Adds a 0.2s sleep between pages to respect rate limits.
        """

    async def get_xpub_transactions_since(
        self, xpub_normalized: str, after_timestamp: int
    ) -> list["XpubTransaction"]:
        """
        Fetches transactions newer than after_timestamp (Unix epoch seconds).
        Paginates until we encounter a transaction at or before after_timestamp.
        Used for incremental sync.
        Returns list sorted oldest-first.
        """
```

#### 4.3.b Data Structures

```python
from dataclasses import dataclass

@dataclass
class DerivedAddressData:
    address: str
    balance_sat: int    # confirmed balance in satoshis
    n_tx: int           # number of on-chain transactions

@dataclass
class XpubSummary:
    balance_sat: int                    # aggregate confirmed balance in satoshis
    balance_btc: Decimal                # = balance_sat / SATOSHI
    n_tx: int                           # total transaction count
    derived_addresses: list[DerivedAddressData]  # ALL active addresses

@dataclass
class XpubTransaction:
    tx_hash: str
    timestamp: int       # Unix epoch seconds (block confirmation time)
    block_height: int | None
    amount_sat: int      # signed net satoshi amount (positive = received, negative = sent)
```

#### 4.3.c Implementation

```python
class XpubClient(BaseClient):
    _TX_PAGE_SIZE = 50

    async def get_xpub_summary(self, xpub_normalized: str) -> XpubSummary:
        data = await self._get_with_retry(
            "/multiaddr",
            params={"active": xpub_normalized, "n": 1, "offset": 0},
        )
        wallet = data.get("wallet", {})
        balance_sat = wallet.get("final_balance", 0)
        n_tx = data.get("info", {}).get("n_tx", 0)

        derived = []
        for addr in data.get("addresses", []):
            derived.append(DerivedAddressData(
                address=addr["address"],
                balance_sat=addr.get("final_balance", 0),
                n_tx=addr.get("n_tx", 0),
            ))

        return XpubSummary(
            balance_sat=balance_sat,
            balance_btc=Decimal(balance_sat) / SATOSHI,
            n_tx=n_tx,
            derived_addresses=derived,
        )

    async def get_xpub_transactions_all(self, xpub_normalized: str) -> list[XpubTransaction]:
        # First call: determine total tx count
        first_page = await self._get_with_retry(
            "/multiaddr",
            params={"active": xpub_normalized, "n": self._TX_PAGE_SIZE, "offset": 0},
        )
        total = first_page.get("info", {}).get("n_tx", 0)
        all_txs = self._parse_txs(first_page.get("txs", []))

        offset = self._TX_PAGE_SIZE
        while offset < total:
            await asyncio.sleep(0.2)
            page = await self._get_with_retry(
                "/multiaddr",
                params={"active": xpub_normalized, "n": self._TX_PAGE_SIZE, "offset": offset},
            )
            txs = self._parse_txs(page.get("txs", []))
            if not txs:
                break
            all_txs.extend(txs)
            offset += self._TX_PAGE_SIZE

        # Sort oldest-first for history replay
        all_txs.sort(key=lambda t: (t.timestamp or 0, t.block_height or 0))
        return all_txs

    async def get_xpub_transactions_since(
        self, xpub_normalized: str, after_timestamp: int
    ) -> list[XpubTransaction]:
        """Fetch pages until we see a tx at or before after_timestamp."""
        new_txs = []
        offset = 0
        while True:
            page = await self._get_with_retry(
                "/multiaddr",
                params={"active": xpub_normalized, "n": self._TX_PAGE_SIZE, "offset": offset},
            )
            txs = self._parse_txs(page.get("txs", []))
            if not txs:
                break
            for tx in txs:
                if (tx.timestamp or 0) > after_timestamp:
                    new_txs.append(tx)
                else:
                    # Reached already-known transactions (API returns newest first)
                    new_txs.sort(key=lambda t: (t.timestamp or 0))
                    return new_txs
            offset += self._TX_PAGE_SIZE
            await asyncio.sleep(0.2)

        new_txs.sort(key=lambda t: (t.timestamp or 0))
        return new_txs

    def _parse_txs(self, raw_txs: list[dict]) -> list[XpubTransaction]:
        """Parse raw multiaddr transaction objects into XpubTransaction."""
        result = []
        for tx in raw_txs:
            result.append(XpubTransaction(
                tx_hash=tx.get("hash", ""),
                timestamp=tx.get("time"),          # epoch seconds; may be None for unconfirmed
                block_height=tx.get("block_height"),
                amount_sat=tx.get("result", 0),    # signed net amount for the xpub
            ))
        return result
```

**Unconfirmed transaction handling:** The `multiaddr` API may include unconfirmed transactions (mempool) with `time=None` or `block_height=None`. These are stored with `timestamp = datetime.utcnow()` as an approximation but are NOT used for historical balance reconstruction (only confirmed transactions with real block times are replayed). The `source="live"` snapshot from the balance endpoint is always authoritative.

#### 4.3.d Edge Cases

| Scenario | Behavior | Test |
|---|---|---|
| `multiaddr` returns 0 addresses (new xpub, no txs yet) | `XpubSummary.derived_addresses = []`; `balance_sat = 0` | `test_xpub_new_wallet` |
| `multiaddr` returns > 200 active addresses | All returned; caller (repository layer) caps at 200 for display | `test_xpub_over_200_addresses` |
| API returns HTTP 429 | Inherited `_get_with_retry` behavior: wait `Retry-After` or 60s, retry once | `test_xpub_rate_limit` |
| API returns HTTP 5xx | Inherited retry behavior; raises on second failure | `test_xpub_server_error` |
| Request timeout (>30s) | `httpx.ReadTimeout` raised; caller handles | `test_xpub_timeout` |
| Transaction with `time=None` (unconfirmed) | Stored with `timestamp = datetime.utcnow()`; excluded from history replay | `test_xpub_unconfirmed_tx` |
| `info.n_tx` is 0 (inconsistent response) | Pagination loop terminates immediately; returns `[]` | `test_xpub_zero_tx_count` |

---

### 4.4 Wallet Model Extension

**File:** `backend/models/wallet.py`

Two new nullable columns are added to the `Wallet` model. The `address` column already stores the extended public key for HD wallets (per func spec §6.1 — "For hd wallets: set to the `extended_public_key` value."). The existing `String(128)` length is sufficient for a 111-character xpub key.

```python
# backend/models/wallet.py  (additions only)
from sqlalchemy import String

class Wallet(Base):
    # ... existing fields unchanged ...

    # HD wallet fields (nullable; present iff wallet_type == "hd")
    wallet_type: Mapped[str] = mapped_column(
        String(10), nullable=False, default="individual"
    )  # "individual" | "hd"
    extended_key_type: Mapped[str | None] = mapped_column(
        String(4), nullable=True
    )  # "xpub" | "ypub" | "zpub" | None

    # Relationship
    derived_addresses: Mapped[list["DerivedAddress"]] = relationship(
        back_populates="wallet", cascade="all, delete-orphan"
    )
```

**Existing `address` field:** Stores the raw xpub/ypub/zpub string for HD wallets. The existing `UniqueConstraint("user_id", "network", "address")` therefore enforces HD wallet uniqueness by key string, which is exact-match per FR-H06 (no case normalization).

**No change to `address` column length:** `String(128)` accommodates 111-char xpub keys without any schema change.

---

### 4.5 DerivedAddress Model

**File:** `backend/models/derived_address.py` (new file)

```python
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base

if TYPE_CHECKING:
    from backend.models.wallet import Wallet

class DerivedAddress(Base):
    __tablename__ = "derived_addresses"
    __table_args__ = (
        UniqueConstraint("wallet_id", "address", name="uq_derived_wallet_address"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)       # UUIDv4
    wallet_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("wallets.id"), nullable=False
    )
    address: Mapped[str] = mapped_column(String(64), nullable=False)     # Bitcoin derived address
    current_balance_native: Mapped[str] = mapped_column(
        String(40), nullable=False                                        # Decimal as string (BTC)
    )
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    wallet: Mapped["Wallet"] = relationship(back_populates="derived_addresses")
```

**Lifecycle:** The entire set of derived addresses for a wallet is replaced on each successful HD wallet fetch (via `DerivedAddressRepository.replace_all()`). This is a cache, not a history. Rows are hard-deleted and re-inserted on each refresh.

**No index on `address`** beyond the unique constraint. With at most 200 rows per HD wallet and at most 50 HD wallets (200 × 50 = 10,000 rows max), index overhead is not justified.

---

### 4.6 DerivedAddressRepository

**File:** `backend/repositories/derived_address.py` (new file)

```python
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.derived_address import DerivedAddress

class DerivedAddressRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def replace_all(
        self,
        wallet_id: str,
        addresses: list[dict],
        updated_at: datetime,
    ) -> int:
        """
        Atomically replaces all derived addresses for a wallet.
        'addresses' is a list of dicts: {"address": str, "balance_btc": Decimal}.
        Only stores the top 200 by balance (FR-H15).
        Returns the total count before capping (for the "Showing top 200 of N" note).
        """
        total = len(addresses)
        # Sort by balance descending and cap at 200
        top = sorted(addresses, key=lambda x: x["balance_btc"], reverse=True)[:200]

        # Delete existing rows for this wallet
        await self.db.execute(
            delete(DerivedAddress).where(DerivedAddress.wallet_id == wallet_id)
        )

        # Insert new rows
        for entry in top:
            row = DerivedAddress(
                id=str(uuid4()),
                wallet_id=wallet_id,
                address=entry["address"],
                current_balance_native=str(entry["balance_btc"]),
                last_updated_at=updated_at,
            )
            self.db.add(row)

        return total

    async def get_by_wallet(self, wallet_id: str) -> list[DerivedAddress]:
        """Returns derived addresses ordered by balance descending (as stored)."""
        result = await self.db.execute(
            select(DerivedAddress)
            .where(DerivedAddress.wallet_id == wallet_id)
            .order_by(DerivedAddress.current_balance_native.desc())
        )
        return list(result.scalars().all())
```

**Note on ordering:** The `ORDER BY current_balance_native DESC` works on the string representation of the Decimal because SQLite will sort these as strings, which may not produce numeric order (e.g., "9" sorts after "10"). This is a known SQLite limitation. To ensure correct numeric ordering, `replace_all` stores rows pre-sorted and the query preserves insertion order via `rowid`. Alternatively, store `balance_sat` as an integer column for sorting. **Decision:** Add a `balance_sat` integer column to `DerivedAddress` for reliable ordering.

Revised model:

```python
class DerivedAddress(Base):
    # ... other fields ...
    current_balance_native: Mapped[str] = mapped_column(String(40), nullable=False)   # BTC as string
    balance_sat: Mapped[int] = mapped_column(nullable=False, default=0)                # for sorting
```

Repository `replace_all` passes `balance_sat=entry["balance_sat"]`, and `get_by_wallet` orders by `DerivedAddress.balance_sat.desc()`.

---

### 4.7 WalletService Extensions

**File:** `backend/services/wallet.py`

#### 4.7.a New HD Wallet Detection and Routing in `add_wallet`

The existing `add_wallet` signature is unchanged. The service internally determines if the input is an HD wallet:

```python
async def add_wallet(self, network: str, address: str, tag: str | None) -> Wallet:
    # 1. Check wallet limit (unchanged)
    count = await self.wallet_repo.count_by_user(self.user_id)
    if count >= self.MAX_WALLETS:
        raise WalletLimitReachedError(...)

    # 2. Normalize input
    address = address.strip().replace("\n", "").replace(" ", "")

    # 3. Route by input type
    if network == "BTC":
        input_type = detect_input_type(address)
        if input_type == "hd_wallet":
            return await self._add_hd_wallet(address, tag)
        else:
            return await self._add_individual_wallet(network, address, tag)
    elif network == "KAS":
        return await self._add_individual_wallet(network, address, tag)
    else:
        raise ValueError(f"Unsupported network: {network}")
```

#### 4.7.b `_add_hd_wallet`

```python
async def _add_hd_wallet(self, key: str, tag: str | None) -> Wallet:
    # 1. Validate extended public key
    error = validate_extended_public_key(key)
    if error:
        raise AddressValidationError(error)

    # 2. Check duplicate (exact string match, case-sensitive per FR-H06)
    exists = await self.wallet_repo.exists_by_address("BTC", key)
    if exists:
        raise DuplicateWalletError("This HD wallet key is already being tracked.")

    # 3. Determine key type from prefix
    key_type = key[:4]  # "xpub", "ypub", or "zpub"

    # 4. Handle tag (HD wallets get "BTC HD Wallet #n" default)
    if not tag or not tag.strip():
        tag = await self._generate_hd_default_tag()
    else:
        tag = tag.strip()
        if len(tag) > 50:
            raise TagValidationError("Tag must be 50 characters or fewer.")
        if await self.wallet_repo.tag_exists(tag):
            raise TagValidationError("A wallet with this tag already exists.")

    # 5. Persist
    wallet = Wallet(
        id=str(uuid4()),
        user_id=self.user_id,
        network="BTC",
        address=key,                    # extended_public_key stored in address column
        tag=tag,
        wallet_type="hd",
        extended_key_type=key_type,
        created_at=datetime.utcnow(),
    )
    await self.wallet_repo.create(wallet)
    await self.db.commit()

    # 6. Trigger background tasks
    asyncio.create_task(self._fetch_initial_hd_data(wallet))

    return wallet

async def _generate_hd_default_tag(self) -> str:
    n = 1
    while True:
        candidate = f"BTC HD Wallet #{n}"
        if not await self.wallet_repo.tag_exists(candidate):
            return candidate
        n += 1
```

#### 4.7.c `_fetch_initial_hd_data`

```python
async def _fetch_initial_hd_data(self, wallet: Wallet) -> None:
    """Background task: initial balance + history import for HD wallet."""
    try:
        await self.refresh_service.refresh_single_hd_wallet(wallet)
    except Exception:
        logger.warning(f"Could not fetch initial balance for HD wallet {wallet.tag}")
    try:
        await self.history_service.full_import_hd(wallet)
    except Exception:
        logger.warning(f"HD wallet history import failed for {wallet.tag}")
    await self.ws_manager.broadcast("wallet:added", {"wallet_id": wallet.id})
```

#### 4.7.d Remove HD Wallet

The existing `remove_wallet` method is unchanged. The cascade `"all, delete-orphan"` on `Wallet.derived_addresses` ensures all `DerivedAddress` rows are deleted when the parent wallet is deleted. The existing `balance_snapshots` and `transactions` cascades also apply.

---

### 4.8 RefreshService Extensions

**File:** `backend/services/refresh.py`

#### 4.8.a `refresh_single_hd_wallet`

```python
async def refresh_single_hd_wallet(self, wallet: Wallet) -> BalanceSnapshot | None:
    """
    Fetches aggregate balance + derived address list for one HD wallet.
    Updates DerivedAddress cache. Stores a BalanceSnapshot.
    Does NOT acquire _lock (same as refresh_single_wallet for individual wallets).
    """
    xpub = normalize_to_xpub(wallet.address)
    try:
        summary = await self.xpub_client.get_xpub_summary(xpub)
    except Exception as e:
        logger.warning(f"HD wallet balance fetch failed for {wallet.tag}: {e}")
        return None

    now = datetime.utcnow()

    # Store aggregate balance snapshot
    snapshot = BalanceSnapshot(
        id=str(uuid4()),
        wallet_id=wallet.id,
        balance=str(summary.balance_btc),
        timestamp=now,
        source="live",
    )
    await self.snapshot_repo.create(snapshot)

    # Update derived address cache
    btc_price = await self.price_service.get_cached_btc_price()
    addr_entries = [
        {
            "address": a.address,
            "balance_btc": Decimal(a.balance_sat) / SATOSHI,
            "balance_sat": a.balance_sat,
        }
        for a in summary.derived_addresses
    ]
    total_count = await self.derived_address_repo.replace_all(
        wallet_id=wallet.id,
        addresses=addr_entries,
        updated_at=now,
    )

    # Store total_count for "Showing top 200 of N" display (as wallet metadata)
    # This is stored in a new Configuration key: "hd_address_count:{wallet_id}"
    if total_count > 200:
        await self.config_repo.set(
            f"hd_address_count:{wallet.id}", str(total_count)
        )

    await self.db.commit()
    return snapshot
```

#### 4.8.b `run_full_refresh` Extension

The existing `_fetch_all_wallets` parallel fetch loop is extended to handle HD wallets:

```python
async def _get_balance(self, wallet: Wallet) -> Decimal:
    if wallet.wallet_type == "hd":
        xpub = normalize_to_xpub(wallet.address)
        summary = await self.xpub_client.get_xpub_summary(xpub)
        # Also update derived addresses (side effect within the lock)
        addr_entries = [...]
        await self.derived_address_repo.replace_all(
            wallet_id=wallet.id,
            addresses=addr_entries,
            updated_at=datetime.utcnow(),
        )
        return summary.balance_btc
    elif wallet.network == "BTC":
        return await self.btc_client.get_balance(wallet.address)
    else:
        return await self.kas_client.get_balance(wallet.address)
```

**Rate limiting consideration:** HD wallet fetches hit blockchain.info (1 call for summary + N calls for transactions). Individual wallet fetches hit Mempool.space. These are separate services; the existing semaphore of 5 concurrent fetches applies globally, which is appropriate.

---

### 4.9 HistoryService Extensions

**File:** `backend/services/history.py`

#### 4.9.a `full_import_hd`

```python
async def full_import_hd(self, wallet: Wallet) -> HistoryImportResult:
    """
    One-time full transaction history import for an HD wallet.
    Fetches all transactions at the xpub aggregate level.
    Stores transactions and historical BalanceSnapshot records.
    Algorithm is identical to individual wallet full_import but uses XpubClient.
    """
    try:
        result = await asyncio.wait_for(
            self._do_full_import_hd(wallet),
            timeout=self.IMPORT_TIMEOUT,  # 300 seconds
        )
        return result
    except asyncio.TimeoutError:
        logger.warning(f"HD wallet history import timed out for {wallet.tag}.")
        await self.ws_manager.broadcast("wallet:history:completed", {
            "wallet_id": wallet.id,
            "partial": True,
        })
        return HistoryImportResult(partial=True)

async def _do_full_import_hd(self, wallet: Wallet) -> HistoryImportResult:
    await self.ws_manager.broadcast("wallet:history:progress", {
        "wallet_id": wallet.id, "status": "started"
    })

    xpub = normalize_to_xpub(wallet.address)
    all_txs = await self.xpub_client.get_xpub_transactions_all(xpub)

    # Same algorithm as individual wallet: running sum replay → BalanceSnapshot records
    running_balance = Decimal("0")
    tx_records = []
    for tx in all_txs:   # already sorted oldest-first
        if tx.timestamp is None:
            continue  # skip unconfirmed
        amount_btc = Decimal(tx.amount_sat) / SATOSHI
        running_balance += amount_btc
        ts = datetime.fromtimestamp(tx.timestamp, tz=timezone.utc).replace(tzinfo=None)
        tx_records.append(Transaction(
            id=str(uuid4()),
            wallet_id=wallet.id,
            tx_hash=tx.tx_hash,
            amount=str(amount_btc),
            balance_after=str(running_balance),
            block_height=tx.block_height,
            timestamp=ts,
            created_at=datetime.utcnow(),
        ))

    # Batch insert (500 at a time)
    await self._batch_insert_transactions(tx_records)

    # Compute daily end-of-day snapshots
    await self._store_daily_snapshots(wallet, tx_records)

    # Fetch historical prices for USD value computation
    if tx_records:
        oldest = tx_records[0].timestamp
        await self._fetch_and_store_historical_prices("BTC", oldest)

    await self.ws_manager.broadcast("wallet:history:completed", {
        "wallet_id": wallet.id, "partial": False
    })
    return HistoryImportResult(partial=False)
```

#### 4.9.b `incremental_sync_hd`

Called from `RefreshService._get_balance()` (same point as `incremental_sync` for individual wallets):

```python
async def incremental_sync_hd(self, wallet: Wallet) -> int:
    """
    Fetch only new transactions for an HD wallet.
    Returns count of new transactions stored.
    """
    # Find the timestamp of the most recent stored transaction
    last_tx = await self.transaction_repo.get_latest_by_wallet(wallet.id)
    if last_tx is None:
        # No stored transactions; defer to full_import_hd (which runs separately)
        return 0

    after_ts = int(last_tx.timestamp.timestamp())
    xpub = normalize_to_xpub(wallet.address)
    new_txs = await self.xpub_client.get_xpub_transactions_since(xpub, after_ts)

    if not new_txs:
        return 0

    # Compute running balance continuing from last known balance_after
    running_balance = Decimal(last_tx.balance_after or "0")
    records = []
    for tx in new_txs:
        if tx.timestamp is None:
            continue
        amount_btc = Decimal(tx.amount_sat) / SATOSHI
        running_balance += amount_btc
        ts = datetime.fromtimestamp(tx.timestamp, tz=timezone.utc).replace(tzinfo=None)
        records.append(Transaction(
            id=str(uuid4()),
            wallet_id=wallet.id,
            tx_hash=tx.tx_hash,
            amount=str(amount_btc),
            balance_after=str(running_balance),
            block_height=tx.block_height,
            timestamp=ts,
            created_at=datetime.utcnow(),
        ))

    await self._batch_insert_transactions(records)
    return len(records)
```

---

### 4.10 API Schema Extensions

**File:** `backend/schemas/wallet.py`

```python
class DerivedAddressResponse(BaseModel):
    address: str
    balance_native: str           # BTC as Decimal string
    balance_usd: str | None       # USD value, None if no price available

class WalletResponse(BaseModel):
    id: str
    network: str
    address: str                  # For HD wallets: truncated xpub (display only — see §4.10.a)
    tag: str
    wallet_type: str              # "individual" or "hd"
    extended_key_type: str | None # "xpub", "ypub", "zpub", or None
    balance: str | None
    balance_usd: str | None
    created_at: str
    last_updated: str | None
    warning: str | None
    history_status: str           # "complete", "importing", "failed", "pending"
    # HD wallet fields (None for individual wallets)
    derived_addresses: list[DerivedAddressResponse] | None = None
    derived_address_count: int | None = None     # total stored (≤200)
    derived_address_total: int | None = None     # raw API total (may be >200)
    hd_loading: bool = False                     # True while first fetch is in progress
```

#### 4.10.a Address Truncation

The `address` field in `WalletResponse` always contains the **full** key/address. Truncation for display ("xpub6CUGRo...d4e7f2") is performed **client-side** in the frontend utility `format.ts`. This keeps the API clean and allows the frontend to choose display format.

```typescript
// frontend/src/utils/format.ts
export function formatWalletAddress(
  address: string,
  walletType: 'individual' | 'hd'
): string {
  if (walletType === 'hd') {
    // "xpubXXXXXX...YYYYYY" — first 10 chars + "..." + last 6 chars
    return address.length > 16
      ? `${address.slice(0, 10)}...${address.slice(-6)}`
      : address
  }
  // Individual address: first 8 + "..." + last 6
  return address.length > 14
    ? `${address.slice(0, 8)}...${address.slice(-6)}`
    : address
}
```

#### 4.10.b Router Changes

No new HTTP endpoints are required. The existing `GET /api/wallets` and `POST /api/wallets` endpoints handle HD wallets transparently. The wallet router's `list_wallets` handler is updated to include derived addresses in the response.

**`GET /api/wallets` response change:** For each HD wallet, the response now includes `derived_addresses`, `derived_address_count`, and `derived_address_total`. For individual wallets these are `null`.

The `WalletCreate` schema is unchanged — the user passes the xpub string in the `address` field as they would any wallet address.

---

### 4.11 Error Handling Additions

New exception classes in `backend/core/exceptions.py`:

```python
class ExtendedKeyValidationError(AddressValidationError):
    """Raised for xpub/ypub/zpub format errors. Subclasses AddressValidationError
    so existing 400 handler catches it without modification."""
    pass
```

`validate_extended_public_key` returns strings (not exceptions) like `validate_btc_address`. The service raises `AddressValidationError(error_message)` in both cases, keeping the router handler unchanged.

**No new exception handlers are needed.** All HD wallet errors map to existing HTTP status codes:
- 400: invalid key format, duplicate key, tag errors
- 409: wallet limit

---

### 4.12 Alembic Migration

**File:** `backend/migrations/versions/002_hd_wallet_support.py`

```python
"""Add HD wallet support: wallet_type, extended_key_type columns + derived_addresses table.

Revision ID: 002
Revises: 001
Create Date: 2026-04-13
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"

def upgrade():
    # Add columns to wallets table
    # SQLite supports ADD COLUMN but not ALTER COLUMN or DROP COLUMN < 3.35
    op.add_column(
        "wallets",
        sa.Column(
            "wallet_type",
            sa.String(10),
            nullable=False,
            server_default="individual",
        ),
    )
    op.add_column(
        "wallets",
        sa.Column("extended_key_type", sa.String(4), nullable=True),
    )

    # Create derived_addresses table
    op.create_table(
        "derived_addresses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "wallet_id",
            sa.String(36),
            sa.ForeignKey("wallets.id"),
            nullable=False,
        ),
        sa.Column("address", sa.String(64), nullable=False),
        sa.Column("current_balance_native", sa.String(40), nullable=False),
        sa.Column("balance_sat", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_updated_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("wallet_id", "address", name="uq_derived_wallet_address"),
    )

def downgrade():
    op.drop_table("derived_addresses")
    # SQLite does not support DROP COLUMN before version 3.35.
    # For downgrade, recreate the table without the new columns.
    # (Practical downgrade: restore from backup or recreate DB.)
    pass  # Left as no-op; document that downgrade requires manual intervention.
```

**SQLite caveat:** `ADD COLUMN` with `server_default` is supported in SQLite 3.x. The `wallet_type` default of `"individual"` ensures existing wallets are correctly classified without a data migration.

---

## 5. Data Models

### 5.1 Full Schema Additions

The complete new/modified ORM model set:

**Modified: `backend/models/wallet.py`** — adds `wallet_type`, `extended_key_type`, and `derived_addresses` relationship.

**New: `backend/models/derived_address.py`** — `DerivedAddress` table as specified in §4.5.

**Updated `backend/models/__init__.py`:**
```python
from backend.models.derived_address import DerivedAddress  # add this import
```

### 5.2 API Schemas Summary

#### `POST /api/wallets` — request (unchanged)

```json
{
  "network": "BTC",
  "address": "xpub6CUGRUBf5RVvPHfD4ADzFLmVRSG41jFjfFbM7EkFGH...",
  "tag": "My Ledger"
}
```

#### `GET /api/wallets` — response (individual wallet, unchanged shape)

```json
{
  "wallets": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "network": "BTC",
      "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
      "tag": "Cold Storage",
      "wallet_type": "individual",
      "extended_key_type": null,
      "balance": "0.05312000",
      "balance_usd": "3802.45",
      "created_at": "2026-04-13T10:00:00",
      "last_updated": "2026-04-13T12:00:00",
      "warning": null,
      "history_status": "complete",
      "derived_addresses": null,
      "derived_address_count": null,
      "derived_address_total": null,
      "hd_loading": false
    }
  ]
}
```

#### `GET /api/wallets` — response (HD wallet)

```json
{
  "wallets": [
    {
      "id": "660e9511-f30c-52e5-b827-557766551111",
      "network": "BTC",
      "address": "xpub6CUGRUBf5RVvPHfD4ADzFLmVRSG41jFjfFbM7EkFGH...",
      "tag": "My Ledger",
      "wallet_type": "hd",
      "extended_key_type": "xpub",
      "balance": "0.15000000",
      "balance_usd": "10750.00",
      "created_at": "2026-04-13T10:00:00",
      "last_updated": "2026-04-13T12:00:00",
      "warning": null,
      "history_status": "complete",
      "derived_addresses": [
        {
          "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
          "balance_native": "0.10000000",
          "balance_usd": "7166.67"
        },
        {
          "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf0S",
          "balance_native": "0.05000000",
          "balance_usd": "3583.33"
        }
      ],
      "derived_address_count": 2,
      "derived_address_total": 2,
      "hd_loading": false
    }
  ]
}
```

#### HD wallet loading state (first fetch in progress)

```json
{
  "balance": null,
  "history_status": "importing",
  "hd_loading": true,
  "derived_addresses": null,
  "derived_address_count": null
}
```

#### HD wallet API failure

```json
{
  "balance": "0.15000000",
  "warning": "Last update failed. Showing data from 2026-04-13T11:00:00.",
  "derived_addresses": [
    { "address": "bc1q...", "balance_native": "0.10000000", "balance_usd": "7166.67" }
  ],
  "derived_address_count": 1,
  "derived_address_total": 1
}
```

---

## 6. Configuration Changes

### 6.1 New Configuration Keys

Two new keys are stored in the `configuration` table using the existing `ConfigRepository`:

| Key pattern | Value | Purpose |
|---|---|---|
| `hd_address_count:{wallet_id}` | integer as string | Total derived address count from the API, stored when it exceeds 200, for "Showing top 200 of N" display (FR-H15). |

These keys are deleted automatically when the parent wallet is deleted (cascade via the wallet delete flow — call `config_repo.delete_by_prefix(f"hd_address_count:{wallet_id}")` in `WalletService.remove_wallet()`).

---

## 7. Frontend Changes

### 7.1 New Components

#### `frontend/src/components/wallet/HdBadge.vue`

```vue
<template>
  <span
    class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold
           bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200"
    aria-label="HD Wallet"
    title="Hierarchical Deterministic Wallet (xpub/ypub/zpub)"
  >
    HD
  </span>
</template>
```

**Accessibility:** The badge uses visible text "HD" (not color alone) per FR-H30 / func spec §8.c. The `aria-label` provides context for screen readers.

#### `frontend/src/components/wallet/DerivedAddressList.vue`

```vue
<template>
  <div class="mt-2 border border-zinc-700 rounded-lg overflow-hidden">
    <!-- Loading state -->
    <div v-if="loading" class="flex justify-center py-4">
      <LoadingSpinner />
    </div>

    <!-- Error state (API failure for derived list) -->
    <div v-else-if="error" class="text-sm text-red-400 px-4 py-3">
      Could not load address breakdown. Will retry on next refresh.
    </div>

    <!-- Empty state -->
    <div v-else-if="!addresses || addresses.length === 0"
         class="text-sm text-zinc-400 px-4 py-3">
      No transactions found for this HD wallet yet.
    </div>

    <!-- Address table -->
    <template v-else>
      <table class="w-full text-sm">
        <thead class="bg-zinc-800 text-zinc-400 text-xs uppercase">
          <tr>
            <th class="px-4 py-2 text-left">Address</th>
            <th class="px-4 py-2 text-right">BTC</th>
            <th class="px-4 py-2 text-right">USD</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-zinc-700">
          <tr v-for="addr in addresses" :key="addr.address"
              class="hover:bg-zinc-800/50 transition-colors">
            <td class="px-4 py-2 font-mono text-xs">
              <!-- Truncated with full address on hover -->
              <span
                :title="addr.address"
                class="cursor-help"
              >{{ formatAddress(addr.address) }}</span>
            </td>
            <td class="px-4 py-2 text-right text-zinc-200">
              {{ formatBtc(addr.balance_native) }}
            </td>
            <td class="px-4 py-2 text-right text-zinc-400">
              {{ addr.balance_usd ? formatUsd(addr.balance_usd) : 'N/A' }}
            </td>
          </tr>
        </tbody>
      </table>
      <!-- "Showing top N of M" note (FR-H15) -->
      <div
        v-if="totalAddressCount > addresses.length"
        class="text-xs text-zinc-500 px-4 py-2 border-t border-zinc-700"
      >
        Showing top {{ addresses.length }} of {{ totalAddressCount }} addresses.
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { DerivedAddressResponse } from '@/types/api'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { formatBtc, formatUsd } from '@/utils/format'

defineProps<{
  addresses: DerivedAddressResponse[] | null
  totalAddressCount: number | null
  loading: boolean
  error: boolean
}>()

function formatAddress(addr: string): string {
  // First 8 chars + "..." + last 6 chars
  return addr.length > 14 ? `${addr.slice(0, 8)}...${addr.slice(-6)}` : addr
}
</script>
```

### 7.2 Modified: `AddWalletDialog.vue`

**Changes:**

1. **Input label dynamic update (FR-H02 / §11.3 decision):** On `@paste` and `@blur` events, detect if the value starts with `xpub`, `ypub`, or `zpub`. If so, update the label from "Wallet address" to "Extended public key (xpub/ypub/zpub)".

2. **Trezor helper text (func spec §8.c):** Show helper text below the input when network is "BTC":
   > "Find your extended public key in Trezor Suite under Account → Details → Show public key."
   This helper text is always visible when BTC is selected (not just when an xpub is detected) — it serves as guidance before the user even pastes.

3. **Placeholder text:** When BTC is selected, the address input placeholder becomes: "Bitcoin address or extended public key (xpub/ypub/zpub)".

```typescript
// In AddWalletDialog.vue <script setup>
import { ref, computed } from 'vue'

const addressInput = ref('')
const isExtendedKey = computed(() =>
  ['xpub', 'ypub', 'zpub'].some(p => addressInput.value.trim().startsWith(p))
)
const inputLabel = computed(() =>
  isExtendedKey.value ? 'Extended public key (xpub/ypub/zpub)' : 'Wallet address'
)

function onPasteOrBlur() {
  // isExtendedKey computed property updates automatically via reactivity
}
```

### 7.3 Modified: `WalletTable.vue`

**Changes:**

1. Add `HdBadge` component next to the tag for HD wallets.
2. Add expand/collapse chevron icon for HD wallet rows.
3. Add expanded state (`expandedWalletId: string | null`) in component state.
4. Render `DerivedAddressList` below the HD wallet row when expanded.
5. Animate expand/collapse with a CSS transition (`max-height` + `overflow-hidden`).

```typescript
// In WalletTable.vue <script setup>
import { ref } from 'vue'
import HdBadge from '@/components/wallet/HdBadge.vue'
import DerivedAddressList from '@/components/wallet/DerivedAddressList.vue'

const expandedWalletId = ref<string | null>(null)

function toggleExpand(walletId: string) {
  expandedWalletId.value = expandedWalletId.value === walletId ? null : walletId
}
```

Template addition per wallet row:

```vue
<!-- Expand button (HD wallets only) -->
<button
  v-if="wallet.wallet_type === 'hd'"
  @click="toggleExpand(wallet.id)"
  class="p-1 rounded hover:bg-zinc-700 transition-colors"
  :aria-label="expandedWalletId === wallet.id ? 'Collapse address list' : 'Expand address list'"
  :aria-expanded="expandedWalletId === wallet.id"
>
  <!-- Chevron icon, rotated when expanded -->
  <ChevronDownIcon
    class="w-4 h-4 transition-transform"
    :class="{ 'rotate-180': expandedWalletId === wallet.id }"
  />
</button>

<!-- Derived address list (HD wallets, when expanded) -->
<Transition name="expand">
  <DerivedAddressList
    v-if="wallet.wallet_type === 'hd' && expandedWalletId === wallet.id"
    :addresses="wallet.derived_addresses"
    :total-address-count="wallet.derived_address_total"
    :loading="wallet.hd_loading"
    :error="!wallet.hd_loading && wallet.derived_addresses === null && wallet.warning !== null"
  />
</Transition>
```

### 7.4 Modified: `WalletDetailView.vue`

- Show `HdBadge` next to the wallet tag in the page header.
- Show `DerivedAddressList` below the aggregate balance chart (same component as in the wallet table).
- Use the same expand/collapse state but default to **expanded** on the detail page (since the user navigated specifically to this wallet's page).

### 7.5 TypeScript Type Additions

**File:** `frontend/src/types/api.ts`

```typescript
export interface DerivedAddressResponse {
  address: string
  balance_native: string
  balance_usd: string | null
}

export interface WalletResponse {
  id: string
  network: string
  address: string
  tag: string
  wallet_type: 'individual' | 'hd'
  extended_key_type: 'xpub' | 'ypub' | 'zpub' | null
  balance: string | null
  balance_usd: string | null
  created_at: string
  last_updated: string | null
  warning: string | null
  history_status: 'complete' | 'importing' | 'failed' | 'pending'
  derived_addresses: DerivedAddressResponse[] | null
  derived_address_count: number | null
  derived_address_total: number | null
  hd_loading: boolean
}
```

### 7.6 Client-Side Validation Update

**File:** `frontend/src/utils/validation.ts`

Add client-side detection for extended keys (mirrors backend `detect_input_type`):

```typescript
export function detectBtcInputType(
  value: string
): 'individual' | 'hd' | 'unknown' {
  const s = value.trim()
  const HD_PREFIXES = ['xpub', 'ypub', 'zpub', 'tpub', 'upub', 'vpub']
  if (HD_PREFIXES.some(p => s.startsWith(p))) return 'hd'
  const BTC_PREFIXES = ['1', '3', 'bc1q', 'bc1p']
  if (BTC_PREFIXES.some(p => s.startsWith(p))) return 'individual'
  if (s.length >= 107 && s.length <= 115) return 'hd'
  return 'unknown'
}
```

**This is a UX-only check** — the backend always re-validates. The result drives the label change in `AddWalletDialog.vue`.

---

## 8. Security Considerations

All security properties from `TECH_SPEC.md §8` apply unchanged. Specific additions for HD wallets:

- **Extended public keys** are public key material. They do NOT grant spending ability and are stored unencrypted, consistent with how Bitcoin addresses are stored.
- **Privacy note:** An xpub key allows address enumeration. This is a deliberate trade-off the user makes when exporting their xpub. No warning is shown in the UI (per func spec §8.b: "The user is assumed to be aware of this trade-off").
- **No local derivation:** The system never derives child keys. It only forwards the xpub to blockchain.info and receives pre-derived addresses back. No BIP32 child key computation occurs in CryptoDash.
- **ypub/zpub conversion:** The `normalize_to_xpub()` function substitutes version bytes only. The underlying key material is NOT modified. The converted key is only used transiently in API calls and is never stored.

---

## 9. Testing Strategy

### 9.1 New Test File: `tests/backend/test_hd_wallets.py`

| Test | Scenario |
|---|---|
| `test_add_hd_wallet_xpub_valid` | Add valid xpub; wallet created with `wallet_type="hd"`, `extended_key_type="xpub"` |
| `test_add_hd_wallet_ypub_valid` | Add valid ypub; `extended_key_type="ypub"` |
| `test_add_hd_wallet_zpub_valid` | Add valid zpub; `extended_key_type="zpub"` |
| `test_add_hd_wallet_testnet_rejected` | tpub/upub/vpub keys return 400 with testnet message |
| `test_add_hd_wallet_wrong_length` | 110-char xpub returns 400 with length message |
| `test_add_hd_wallet_bad_checksum` | Valid prefix, valid length, bad checksum → 400 checksum message |
| `test_add_hd_wallet_duplicate` | Same xpub added twice → 400 "already being tracked" |
| `test_add_hd_wallet_uppercase_rejected` | `XPUB6...` → 400 "Invalid Bitcoin address format" |
| `test_add_hd_wallet_whitespace_trimmed` | `" xpub6... "` → succeeds after trimming |
| `test_add_hd_wallet_default_tag` | No tag provided → "BTC HD Wallet #1" |
| `test_add_hd_wallet_default_tag_increment` | Second HD wallet with no tag → "BTC HD Wallet #2" |
| `test_add_hd_wallet_limit_counts_as_one` | 49 individual wallets + 1 HD wallet = 50 total |
| `test_hd_wallet_coexists_with_individual` | Add xpub + a derived address as individual wallet → both accepted, no warning |
| `test_hd_wallet_list_response_shape` | `GET /api/wallets` returns `derived_addresses`, `wallet_type`, `extended_key_type` |
| `test_hd_wallet_remove_cascades` | Delete HD wallet → `derived_addresses` rows deleted, snapshots deleted |
| `test_derived_address_repo_replace_all` | Replace all: old rows deleted, new rows inserted, sorted by balance_sat desc |
| `test_derived_address_repo_cap_200` | API returns 250 addresses → only top 200 stored |
| `test_normalize_to_xpub_xpub` | xpub → returned unchanged |
| `test_normalize_to_xpub_ypub` | ypub → xpub-format, same key material |
| `test_normalize_to_xpub_zpub` | zpub → xpub-format, same key material |
| `test_validate_extended_public_key_valid` | All three valid prefixes pass |
| `test_validate_extended_public_key_testnet` | All three testnet prefixes fail with correct message |
| `test_validate_extended_public_key_length_110` | 110 chars → length error with N=110 |
| `test_validate_extended_public_key_length_112` | 112 chars → length error with N=112 |
| `test_validate_extended_public_key_checksum` | Valid prefix+length, flipped byte → checksum error |
| `test_validate_extended_public_key_unrecognized_prefix` | 111-char string with "abcd" prefix → unrecognized error |
| `test_hd_wallet_history_import` | `full_import_hd` stores transactions and daily snapshots |
| `test_hd_wallet_incremental_sync` | `incremental_sync_hd` only fetches new txs after last known |
| `test_hd_wallet_no_active_addresses` | New xpub with zero txs → wallet saved, balance=0, empty address list |

### 9.2 New Test File: `tests/backend/test_xpub_client.py`

| Test | Scenario |
|---|---|
| `test_get_xpub_summary_parses_response` | Mock multiaddr response → correct XpubSummary |
| `test_get_xpub_summary_empty_addresses` | `addresses: []` → `derived_addresses = []` |
| `test_get_xpub_transactions_all_single_page` | n_tx ≤ 50 → single request, sorted oldest-first |
| `test_get_xpub_transactions_all_multi_page` | n_tx = 125 → 3 requests (0, 50, 100 offsets) |
| `test_get_xpub_transactions_since` | Stop pagination when tx.timestamp ≤ after_timestamp |
| `test_xpub_client_rate_limit_handling` | 429 → wait Retry-After, retry |
| `test_xpub_client_server_error` | 500 → raises on second attempt |
| `test_xpub_client_unconfirmed_tx` | tx with `time=None` → included but timestamp=now |
| `test_xpub_client_zero_n_tx` | `info.n_tx=0` → returns `[]`, no extra requests |

### 9.3 Modified: `tests/backend/test_wallets.py`

- Add test case: `test_add_wallet_btc_detects_individual_vs_hd` — same service call with individual address vs xpub key routes correctly.
- Add test case: `test_add_wallet_btc_unrecognized_length_heuristic` — 111-char string with unknown prefix → 400 unrecognized message.

### 9.4 Frontend Tests

**`tests/frontend/components/HdBadge.test.ts`**
- Renders "HD" text.
- Has `aria-label` attribute.

**`tests/frontend/components/DerivedAddressList.test.ts`**
- Renders loading spinner when `loading=true`.
- Renders "No transactions found..." when `addresses=[]`.
- Renders "Could not load..." when `error=true`.
- Renders address rows in correct order.
- Shows "Showing top 200 of N" note when `totalAddressCount > addresses.length`.
- Truncates addresses to "first8...last6" format.

**`tests/frontend/components/AddWalletDialog.test.ts`** (existing, extended)
- Label changes to "Extended public key..." on paste of xpub value.
- Trezor helper text visible when network is "BTC".

### 9.5 How to Run

```bash
# Backend tests (all including HD wallet tests)
pytest tests/backend/ -v

# Specific HD wallet tests
pytest tests/backend/test_hd_wallets.py tests/backend/test_xpub_client.py -v

# Frontend tests
cd frontend && npm run test
```

---

## 10. Ambiguity Resolution Log

### 10.1 xpub API Provider

**Functional spec:** "The specific API provider for xpub queries is deferred to the technical specification phase."

**Decision:** Use **blockchain.info's `multiaddr` endpoint** (`https://blockchain.info/multiaddr?active={xpub}`).

**Justification:**
- Explicitly cited in the functional spec brief as a confirmed capability.
- Supports xpub natively; ypub/zpub handled via version-byte conversion (§4.2).
- No API key required (free tier).
- Returns both aggregate balance and derived address list in a single call.
- Established API with long history of availability.
- Mempool.space (the existing BTC API) does not offer an xpub endpoint.
- Blockchair's free tier (30 calls/day) is too restrictive for a refresh-cycle-integrated feature.

**Known limitation:** blockchain.info natively supports only xpub. ypub and zpub are converted to xpub format via `normalize_to_xpub()` before the API call. This is a standard technique used by Electrum and many other tools. The conversion is lossless.

### 10.2 ypub/zpub Support Mechanism

**Functional spec:** Accepts ypub and zpub. API selection deferred.

**Decision:** Convert ypub/zpub to xpub (version-byte substitution) before querying blockchain.info. Store the original key. Never store the converted form.

**Justification:** ypub and zpub differ from xpub only in the 4-byte version prefix. The underlying key material is identical. Substituting version bytes is not "local address derivation" (the func spec's out-of-scope item). The result is a valid xpub key that blockchain.info can use to derive and look up all the same addresses. Confirmed approach: used by BTCPayServer, Electrum, and multiple Bitcoin libraries.

### 10.3 Extended Key Length Validation (FR-H03 vs. §9 Constraint)

**Functional spec FR-H03:** "the full string must be 111 characters long."
**Func spec §9 (Constraints):** "The tech spec may relax the length check to a range (e.g., 107–115) with a note."

**Decision:** Validate as **exactly 111 characters** for v1 (strict, per FR-H03).

**Justification:** Base58Check-encoded 78-byte payloads (the standard BIP32 extended key size) consistently produce 111-character Base58 strings. The 107–115 range in §9 is a hedge against hypothetical edge cases; no known wallet software produces extended keys of other lengths for standard BIP44/49/84 accounts. If user reports appear, the range can be widened without affecting stored data.

### 10.4 Input Detection Timing (FR-H02 / §11.3)

**Functional spec §11.3:** "Detect on submit and on paste events (not on every keystroke)."

**Decision:** The `isExtendedKey` computed property in Vue reacts on every change to the input (Vue reactivity). However, the **label change** is only triggered on paste and blur events, not on every keystroke, by binding `isExtendedKey` to the label only after a "committed input" event has occurred. This is implemented by setting a `hasCommitted: boolean` flag on paste/blur.

**Practical implementation:**

```typescript
const hasCommitted = ref(false)
const showExtendedLabel = computed(
  () => hasCommitted.value && isExtendedKey.value
)
```

On `@paste`: set `hasCommitted.value = true`.
On `@blur`: set `hasCommitted.value = true`.
On `@input`: leave `hasCommitted` unchanged (label doesn't update while typing).

### 10.5 Derived Address Sorting (FR-H14)

**Functional spec FR-H14:** "Display the derived address sub-list in descending order of current balance."

**Decision:** Store a `balance_sat` integer column in `DerivedAddress` for reliable numeric sorting. Sort in the `DerivedAddressRepository.get_by_wallet()` query with `ORDER BY balance_sat DESC`. The string-based `current_balance_native` column is not suitable for sorting (lexicographic vs. numeric).

### 10.6 Overlap Between HD and Individual Wallets (§11.5)

**Functional spec §11.5:** "No overlap detection. If a user tracks both `xpub6...` and one of its derived addresses (e.g., `bc1qxyz...`) as separate wallets, both are tracked independently."

**Decision:** No change needed in the implementation. The existing `DuplicateWalletError` check for individual wallets uses the `(network, address)` pair. An xpub string is not a valid Bitcoin address, so an xpub cannot collide with an individual address in the unique constraint. Cross-type collisions are structurally impossible at the DB level.

### 10.7 Derived Address Error State in Response

**Functional spec §5.1.e:** "Aggregate balance may still succeed. Expanded list shows: 'Could not load address breakdown. Will retry on next refresh.'"

**Decision:** When the aggregate balance fetch succeeds but we cannot obtain the derived address breakdown (e.g., the API response lacks an `addresses` field), we still store the `BalanceSnapshot` but do NOT update `DerivedAddress` rows. The frontend detects this state as `warning !== null AND derived_addresses !== null` (the old cache is still shown). Only when `derived_addresses === null` (no cache at all) AND `warning !== null` does the "Could not load..." message appear. This is encoded in the `DerivedAddressList` component's `error` prop logic (§7.1).

### 10.8 Removal of HD Wallet During Active Refresh (§5.1.e)

**Functional spec:** "Allow removal. The in-progress fetch for that wallet is cancelled or its result discarded."

**Decision:** The in-progress `asyncio.Task` for that wallet is NOT explicitly cancelled. Instead, the refresh service's result-writing step performs a wallet existence check before writing to the DB:

```python
async def _write_snapshot(self, wallet_id: str, balance: Decimal) -> None:
    wallet = await self.wallet_repo.get(wallet_id)
    if wallet is None:
        return  # Wallet was removed during fetch; discard result silently
    ...
```

This avoids the complexity of task cancellation and is safe because:
- `asyncio` cooperative multitasking means the delete commits between `await` points.
- The wallet existence check is the last step before writing.
- Partial writes (e.g., DerivedAddress rows written before the check) are cleaned up by the cascade on wallet delete, which already ran.

### 10.9 Tag Uniqueness Across Wallet Types

**Functional spec FR-H07:** "The system shall apply the same tag rules to HD wallets as to individual-address wallets."

**Decision:** Tags are unique across ALL wallets (individual and HD) in the same user's account. The existing `wallet_repo.tag_exists()` query checks all wallets regardless of type. A user cannot name an HD wallet "BTC Wallet #1" if that tag is already used by an individual wallet.

### 10.10 hd_loading Flag Lifecycle

**Implementation decision:** The `hd_loading` field in `WalletResponse` is `True` between wallet creation and the first successful balance fetch. Since there is no persistent "loading" state in the DB, the backend determines `hd_loading` as:

```python
hd_loading = (
    wallet.wallet_type == "hd"
    and wallet.last_updated is None  # no successful snapshot yet
    and wallet.history_status == "importing"
)
```

`last_updated` is derived from the most recent `BalanceSnapshot.timestamp`. If no snapshot exists yet (first fetch still in progress), `hd_loading = True`.

---

*Last updated: 2026-04-13*
