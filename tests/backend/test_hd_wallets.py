"""Tests for HD wallet — extended key validation, detection, normalization,
WalletService._add_hd_wallet flow, and DerivedAddressRepository (T20)."""

from datetime import datetime, timezone
from decimal import Decimal

from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.dependencies import get_db
from backend.database import init_db
from backend.models.configuration import Configuration
from backend.models.derived_address import DerivedAddress
from backend.models.user import User
from backend.models.wallet import Wallet
from backend.repositories.derived_address import DerivedAddressRepository
from backend.routers.auth import router as auth_router
from backend.routers.wallets import router as wallets_router
from backend.services.wallet import (
    WalletService,
    detect_input_type,
    normalize_to_xpub,
    validate_extended_public_key,
)

# ---------------------------------------------------------------------------
# Real test keys (derived from BIP32 test vector, validated by _b58decode_check)
# ---------------------------------------------------------------------------

# BIP32 test vector m/0' child key
VALID_XPUB = "xpub68Gmy5EdvgibQVfPdqkBBCHxA5htiqg55crXYuXoQRKfDBFA1WEjWgP6LHhwBZeNK1VTsfTFUHCdrfp1bgwQ9xv5ski8PX9rL2dZXvgGDnw"
# Same key material, ypub version bytes
VALID_YPUB = "ypub6T73GjuZ5NG5FnrWUCXoPHPTL3rLfTfZzjNkLJRgnRhYGH4PGAQJ8k3EMVfXBUJHiecGd93ovwZBjxRaKPMQxCbgk6QYyRyLbkhCvXJ8PtA"
# Same key material, zpub version bytes
VALID_ZPUB = "zpub6mwJaQaUE3oZ763dJZKRbNUxW1znc5f4uqty7hKaAS5RKNscWpZrkohNNhd7BNxD8Hj5NceNPbujdF3935mRkSHHcS6yZLnpsUkrK1XoMLr"
# Same key material, tpub version bytes (testnet)
VALID_TPUB = "tpubD8eQVK4Kdxg3gHrF62jGP7dKVCoYiEB8dFSpuTawkL5YxTus5j5pf83vaKnii4bc6v2NVEy81P2gYrJczYne3QNNwMTS53p5uzDyHvnw2jm"
# xpub with flipped checksum byte — same length, same prefix, bad checksum
BAD_CHECKSUM_XPUB = "xpub68Gmy5EdvgibQVfPdqkBBCHxA5htiqg55crXYuXoQRKfDBFA1WEjWgP6LHhwBZeNK1VTsfTFUHCdrfp1bgwQ9xv5ski8PX9rL2dZXsnjcwy"

assert len(VALID_XPUB) == 111
assert len(VALID_YPUB) == 111
assert len(VALID_ZPUB) == 111
assert len(VALID_TPUB) == 111
assert len(BAD_CHECKSUM_XPUB) == 111

VALID_BTC_ADDR = "1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf"
VALID_KAS_ADDR = "kaspa:" + "a" * 61


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def fresh_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def hd_client(fresh_engine):
    """HTTP test client with auth + wallets routers."""
    session_factory = async_sessionmaker(
        fresh_engine, class_=AsyncSession, expire_on_commit=False
    )
    await init_db(engine=fresh_engine, session_factory=session_factory)

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(wallets_router)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest_asyncio.fixture
async def auth_token(hd_client):
    resp = await hd_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    assert resp.status_code == 201
    return resp.json()["token"]


@pytest_asyncio.fixture
async def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


async def add_wallet_http(client, headers, network, address, tag=None):
    payload = {"network": network, "address": address}
    if tag is not None:
        payload["tag"] = tag
    return await client.post("/api/wallets/", json=payload, headers=headers)


# ---------------------------------------------------------------------------
# Unit tests: detect_input_type
# ---------------------------------------------------------------------------


def test_detect_input_type_xpub():
    assert detect_input_type(VALID_XPUB) == "hd_wallet"


def test_detect_input_type_ypub():
    assert detect_input_type(VALID_YPUB) == "hd_wallet"


def test_detect_input_type_zpub():
    assert detect_input_type(VALID_ZPUB) == "hd_wallet"


def test_detect_input_type_tpub():
    assert detect_input_type(VALID_TPUB) == "hd_wallet"


def test_detect_input_type_upub():
    upub = "upub" + "A" * 107  # any upub prefix
    assert detect_input_type(upub) == "hd_wallet"


def test_detect_input_type_vpub():
    vpub = "vpub" + "A" * 107
    assert detect_input_type(vpub) == "hd_wallet"


def test_detect_input_type_individual_btc_legacy():
    assert detect_input_type("1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf") == "individual_btc"


def test_detect_input_type_individual_btc_p2sh():
    assert detect_input_type("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy") == "individual_btc"


def test_detect_input_type_individual_btc_bech32():
    assert detect_input_type("bc1q" + "a" * 38) == "individual_btc"


def test_detect_input_type_individual_btc_taproot():
    assert detect_input_type("bc1p" + "a" * 58) == "individual_btc"


def test_detect_input_type_kaspa():
    assert detect_input_type(VALID_KAS_ADDR) == "kas"


def test_detect_input_type_unknown_short():
    assert detect_input_type("notanaddress") == "unknown"


def test_detect_input_type_uppercase_xpub_length_heuristic():
    # "XPUB..." is 111 chars → triggers the length heuristic → hd_wallet
    # (will fail validation with "Unrecognized key format" inside validate_extended_public_key)
    assert detect_input_type("XPUB" + "A" * 107) == "hd_wallet"


def test_detect_input_type_length_heuristic_111_chars():
    # 111-char string with unrecognized prefix → hd_wallet (FR-H05 path)
    s = "abcd" + "A" * 107
    assert len(s) == 111
    assert detect_input_type(s) == "hd_wallet"


def test_detect_input_type_length_heuristic_107_chars():
    s = "abcd" + "A" * 103
    assert len(s) == 107
    assert detect_input_type(s) == "hd_wallet"


def test_detect_input_type_length_heuristic_115_chars():
    s = "abcd" + "A" * 111
    assert len(s) == 115
    assert detect_input_type(s) == "hd_wallet"


def test_detect_input_type_106_chars_is_unknown():
    s = "abcd" + "A" * 102
    assert len(s) == 106
    assert detect_input_type(s) == "unknown"


def test_detect_input_type_whitespace_stripped():
    # Whitespace stripping occurs inside detect_input_type
    assert detect_input_type(f"  {VALID_XPUB}  ") == "hd_wallet"


# ---------------------------------------------------------------------------
# Unit tests: validate_extended_public_key
# ---------------------------------------------------------------------------


def test_validate_extended_public_key_valid_xpub():
    assert validate_extended_public_key(VALID_XPUB) is None


def test_validate_extended_public_key_valid_ypub():
    assert validate_extended_public_key(VALID_YPUB) is None


def test_validate_extended_public_key_valid_zpub():
    assert validate_extended_public_key(VALID_ZPUB) is None


def test_validate_extended_public_key_testnet_tpub():
    err = validate_extended_public_key(VALID_TPUB)
    assert err is not None
    assert "Testnet keys are not supported" in err
    assert "mainnet" in err


def test_validate_extended_public_key_testnet_upub():
    upub = "upub" + "A" * 107  # right length, wrong checksum — testnet check runs first
    err = validate_extended_public_key(upub)
    assert err is not None
    assert "Testnet keys are not supported" in err


def test_validate_extended_public_key_testnet_vpub():
    vpub = "vpub" + "A" * 107
    err = validate_extended_public_key(vpub)
    assert err is not None
    assert "Testnet keys are not supported" in err


def test_validate_extended_public_key_length_110():
    short = VALID_XPUB[:110]
    err = validate_extended_public_key(short)
    assert err is not None
    assert "Expected 111 characters, got 110" in err


def test_validate_extended_public_key_length_112():
    long_key = VALID_XPUB + "A"
    err = validate_extended_public_key(long_key)
    assert err is not None
    assert "Expected 111 characters, got 112" in err


def test_validate_extended_public_key_bad_checksum():
    err = validate_extended_public_key(BAD_CHECKSUM_XPUB)
    assert err is not None
    assert "checksum" in err.lower()


def test_validate_extended_public_key_invalid_base58_char():
    """xpub prefix + 111 chars total, but contains '0' (invalid Base58 char).

    '0' (zero) is not in the Base58 alphabet. The _b58decode call raises
    ValueError("Invalid Base58 character"), which is caught by the blanket
    except in validate_extended_public_key and surfaced as a checksum error.
    """
    # Replace char at position 50 with '0' (digit zero — not in Base58 alphabet)
    bad_key = VALID_XPUB[:50] + "0" + VALID_XPUB[51:]
    assert len(bad_key) == 111
    assert bad_key.startswith("xpub")
    assert "0" in bad_key
    err = validate_extended_public_key(bad_key)
    assert err is not None
    # _b58decode raises ValueError("Invalid Base58 character") which is
    # reported as the checksum error message (both flow through the same
    # except ValueError handler)
    assert "checksum verification failed" in err


def test_validate_extended_public_key_unrecognized_prefix():
    # 111-char string with non-xpub/ypub/zpub prefix
    s = "abcd" + "A" * 107
    assert len(s) == 111
    err = validate_extended_public_key(s)
    assert err is not None
    assert "Unrecognized key format" in err
    assert "xpub" in err


# ---------------------------------------------------------------------------
# Unit tests: normalize_to_xpub
# ---------------------------------------------------------------------------


def test_normalize_to_xpub_xpub_unchanged():
    result = normalize_to_xpub(VALID_XPUB)
    assert result == VALID_XPUB


def test_normalize_to_xpub_ypub():
    result = normalize_to_xpub(VALID_YPUB)
    assert result.startswith("xpub")
    assert len(result) == 111


def test_normalize_to_xpub_zpub():
    result = normalize_to_xpub(VALID_ZPUB)
    assert result.startswith("xpub")
    assert len(result) == 111


def test_normalize_to_xpub_ypub_key_material_preserved():
    """Normalizing ypub → xpub then back to ypub yields the original."""
    import hashlib

    _BASE58_CHARS = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    _BASE58_MAP = {c: i for i, c in enumerate(_BASE58_CHARS)}

    def _b58decode(s):
        num = 0
        for char in s:
            num = num * 58 + _BASE58_MAP[char]
        leading = len(s) - len(s.lstrip("1"))
        byte_len = (num.bit_length() + 7) // 8 if num > 0 else 1
        return b"\x00" * leading + num.to_bytes(byte_len, "big")

    def _b58decode_check(s):
        decoded = _b58decode(s)
        payload, checksum = decoded[:-4], decoded[-4:]
        expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        if checksum != expected:
            raise ValueError("checksum mismatch")
        return payload

    xpub_normalized = normalize_to_xpub(VALID_YPUB)
    xpub_payload = _b58decode_check(xpub_normalized)
    ypub_payload = _b58decode_check(VALID_YPUB)
    # Key material bytes 4..78 must be identical (only version prefix differs)
    assert xpub_payload[4:] == ypub_payload[4:]


# ---------------------------------------------------------------------------
# Integration: HTTP add HD wallet (via hd_client fixture)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_hd_wallet_xpub_valid(hd_client, auth_headers):
    resp = await add_wallet_http(hd_client, auth_headers, "BTC", VALID_XPUB)
    assert resp.status_code == 201
    data = resp.json()
    assert data["wallet_type"] == "hd"
    assert data["extended_key_type"] == "xpub"
    assert data["address"] == VALID_XPUB
    assert data["network"] == "BTC"


@pytest.mark.asyncio
async def test_add_hd_wallet_ypub_valid(hd_client, auth_headers):
    resp = await add_wallet_http(hd_client, auth_headers, "BTC", VALID_YPUB)
    assert resp.status_code == 201
    data = resp.json()
    assert data["wallet_type"] == "hd"
    assert data["extended_key_type"] == "ypub"
    assert data["address"] == VALID_YPUB


@pytest.mark.asyncio
async def test_add_hd_wallet_zpub_valid(hd_client, auth_headers):
    resp = await add_wallet_http(hd_client, auth_headers, "BTC", VALID_ZPUB)
    assert resp.status_code == 201
    data = resp.json()
    assert data["wallet_type"] == "hd"
    assert data["extended_key_type"] == "zpub"
    assert data["address"] == VALID_ZPUB


@pytest.mark.asyncio
async def test_add_hd_wallet_testnet_rejected(hd_client, auth_headers):
    resp = await add_wallet_http(hd_client, auth_headers, "BTC", VALID_TPUB)
    assert resp.status_code == 400
    assert "Testnet keys are not supported" in resp.json()["detail"]
    assert "mainnet" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_add_hd_wallet_wrong_length(hd_client, auth_headers):
    short_xpub = VALID_XPUB[:110]
    resp = await add_wallet_http(hd_client, auth_headers, "BTC", short_xpub)
    assert resp.status_code == 400
    assert "Expected 111 characters, got 110" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_add_hd_wallet_bad_checksum(hd_client, auth_headers):
    resp = await add_wallet_http(hd_client, auth_headers, "BTC", BAD_CHECKSUM_XPUB)
    assert resp.status_code == 400
    assert "checksum" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_add_hd_wallet_duplicate(hd_client, auth_headers):
    await add_wallet_http(hd_client, auth_headers, "BTC", VALID_XPUB, "First")
    resp = await add_wallet_http(hd_client, auth_headers, "BTC", VALID_XPUB, "Second")
    assert resp.status_code == 400
    assert "already being tracked" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_add_hd_wallet_uppercase_rejected(hd_client, auth_headers):
    # "XPUB..." is 111 chars → length heuristic → hd_wallet path →
    # validate_extended_public_key → "Unrecognized key format" (XPUB is not xpub/ypub/zpub)
    resp = await add_wallet_http(
        hd_client, auth_headers, "BTC", "XPUB" + VALID_XPUB[4:]
    )
    assert resp.status_code == 400
    assert "Unrecognized key format" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_add_hd_wallet_whitespace_trimmed(hd_client, auth_headers):
    resp = await add_wallet_http(hd_client, auth_headers, "BTC", f"  {VALID_XPUB}  ")
    assert resp.status_code == 201
    assert resp.json()["address"] == VALID_XPUB


@pytest.mark.asyncio
async def test_add_hd_wallet_default_tag(hd_client, auth_headers):
    resp = await add_wallet_http(hd_client, auth_headers, "BTC", VALID_XPUB)
    assert resp.status_code == 201
    assert resp.json()["tag"] == "BTC HD Wallet #1"


@pytest.mark.asyncio
async def test_add_hd_wallet_default_tag_increment(hd_client, auth_headers):
    resp1 = await add_wallet_http(hd_client, auth_headers, "BTC", VALID_XPUB)
    resp2 = await add_wallet_http(hd_client, auth_headers, "BTC", VALID_YPUB)
    assert resp1.json()["tag"] == "BTC HD Wallet #1"
    assert resp2.json()["tag"] == "BTC HD Wallet #2"


@pytest.mark.asyncio
async def test_add_hd_wallet_limit_counts_as_one(hd_client, auth_headers):
    """HD wallet counts as 1 toward the 50-wallet limit (FR-H10)."""
    # Add 49 KAS wallets
    bech32_digits = "023456789"
    for i in range(49):
        d1 = bech32_digits[i // len(bech32_digits)]
        d2 = bech32_digits[i % len(bech32_digits)]
        addr = "kaspa:" + "a" * 59 + d1 + d2
        resp = await add_wallet_http(hd_client, auth_headers, "KAS", addr, f"KAS {i}")
        assert resp.status_code == 201

    # 50th wallet: HD wallet — must succeed
    resp = await add_wallet_http(hd_client, auth_headers, "BTC", VALID_XPUB)
    assert resp.status_code == 201
    assert resp.json()["wallet_type"] == "hd"

    # 51st wallet: must be rejected
    resp = await add_wallet_http(hd_client, auth_headers, "BTC", VALID_YPUB)
    assert resp.status_code == 409
    assert "Wallet limit reached (50)" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_hd_wallet_coexists_with_individual(hd_client, auth_headers):
    """HD wallet and individual BTC wallet can coexist (FR-H11)."""
    resp1 = await add_wallet_http(hd_client, auth_headers, "BTC", VALID_XPUB, "HD")
    resp2 = await add_wallet_http(
        hd_client, auth_headers, "BTC", VALID_BTC_ADDR, "Individual"
    )
    assert resp1.status_code == 201
    assert resp2.status_code == 201


@pytest.mark.asyncio
async def test_hd_wallet_list_response_shape(hd_client, auth_headers):
    """GET /api/wallets returns wallet_type and extended_key_type fields."""
    await add_wallet_http(hd_client, auth_headers, "BTC", VALID_XPUB, "My HD")
    resp = await hd_client.get("/api/wallets/", headers=auth_headers)
    assert resp.status_code == 200
    wallets = resp.json()["wallets"]
    assert len(wallets) == 1
    w = wallets[0]
    assert w["wallet_type"] == "hd"
    assert w["extended_key_type"] == "xpub"
    assert "derived_addresses" in w
    assert "derived_address_count" in w
    assert "derived_address_total" in w
    assert "hd_loading" in w


@pytest.mark.asyncio
async def test_hd_wallet_remove_cascades(hd_client, auth_headers, fresh_engine):
    """Deleting an HD wallet removes derived_address rows and the config key (FR-H16)."""
    resp = await add_wallet_http(hd_client, auth_headers, "BTC", VALID_XPUB, "Cascade")
    wallet_id = resp.json()["id"]

    config_key = f"hd_address_count:{wallet_id}"

    # Insert a derived address row and a config key directly via DB
    session_factory = async_sessionmaker(
        fresh_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as db:
        row = DerivedAddress(
            id=str(uuid4()),
            wallet_id=wallet_id,
            address="bc1qxyz",
            current_balance_native="0.01",
            balance_sat=1000000,
            last_updated_at=datetime.now(timezone.utc),
        )
        db.add(row)
        cfg = Configuration(
            key=config_key,
            value="250",
            updated_at=datetime.now(timezone.utc),
        )
        db.add(cfg)
        await db.commit()

    # Delete wallet via HTTP
    del_resp = await hd_client.delete(f"/api/wallets/{wallet_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # Verify derived address is gone (ORM cascade)
    async with session_factory() as db:
        da_result = await db.execute(
            select(DerivedAddress).where(DerivedAddress.wallet_id == wallet_id)
        )
        assert da_result.scalar_one_or_none() is None

        # Verify config key is gone (delete_by_prefix in remove_wallet)
        cfg_result = await db.execute(
            select(Configuration).where(Configuration.key == config_key)
        )
        assert cfg_result.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# DerivedAddressRepository unit tests
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_session(fresh_engine):
    session_factory = async_sessionmaker(
        fresh_engine, class_=AsyncSession, expire_on_commit=False
    )
    await init_db(engine=fresh_engine, session_factory=session_factory)
    async with session_factory() as session:
        # Create a user and HD wallet to satisfy FK constraints
        now = datetime.now(timezone.utc)
        user = User(id="user-1", username="testuser", password_hash="x", created_at=now)
        session.add(user)
        wallet = Wallet(
            id="wallet-1",
            user_id="user-1",
            network="BTC",
            address=VALID_XPUB,
            tag="HD Test",
            wallet_type="hd",
            extended_key_type="xpub",
            created_at=now,
        )
        session.add(wallet)
        await session.commit()
        yield session


@pytest.mark.asyncio
async def test_derived_address_repo_replace_all(db_session):
    repo = DerivedAddressRepository(db_session)
    now = datetime.now(timezone.utc)

    addresses = [
        {"address": "addr1", "balance_btc": Decimal("0.05"), "balance_sat": 5_000_000},
        {"address": "addr2", "balance_btc": Decimal("0.10"), "balance_sat": 10_000_000},
        {"address": "addr3", "balance_btc": Decimal("0.01"), "balance_sat": 1_000_000},
    ]
    total = await repo.replace_all("wallet-1", addresses, now)
    await db_session.commit()

    assert total == 3

    rows = await repo.get_by_wallet("wallet-1")
    assert len(rows) == 3
    # Ordered by balance_sat descending
    assert rows[0].balance_sat == 10_000_000
    assert rows[1].balance_sat == 5_000_000
    assert rows[2].balance_sat == 1_000_000


@pytest.mark.asyncio
async def test_derived_address_repo_replace_all_replaces_old_rows(db_session):
    repo = DerivedAddressRepository(db_session)
    now = datetime.now(timezone.utc)

    # First insert
    await repo.replace_all(
        "wallet-1",
        [
            {
                "address": "old-addr",
                "balance_btc": Decimal("0.1"),
                "balance_sat": 10_000_000,
            }
        ],
        now,
    )
    await db_session.commit()

    # Replace with new data
    await repo.replace_all(
        "wallet-1",
        [
            {
                "address": "new-addr",
                "balance_btc": Decimal("0.2"),
                "balance_sat": 20_000_000,
            }
        ],
        now,
    )
    await db_session.commit()

    rows = await repo.get_by_wallet("wallet-1")
    assert len(rows) == 1
    assert rows[0].address == "new-addr"


@pytest.mark.asyncio
async def test_derived_address_repo_cap_200(db_session):
    repo = DerivedAddressRepository(db_session)
    now = datetime.now(timezone.utc)

    # Create 250 addresses
    addresses = [
        {
            "address": f"addr{i}",
            "balance_btc": Decimal(str(i)) / 100_000_000,
            "balance_sat": i,
        }
        for i in range(250)
    ]
    total = await repo.replace_all("wallet-1", addresses, now)
    await db_session.commit()

    assert total == 250
    rows = await repo.get_by_wallet("wallet-1")
    assert len(rows) == 200
    # Top 200 by balance_sat: indices 249, 248, ..., 50
    assert rows[0].balance_sat == 249


# ---------------------------------------------------------------------------
# WalletService._add_hd_wallet — service-layer unit tests
# (bypass HTTP, test service directly with mocked dependencies)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def service_db(fresh_engine):
    session_factory = async_sessionmaker(
        fresh_engine, class_=AsyncSession, expire_on_commit=False
    )
    await init_db(engine=fresh_engine, session_factory=session_factory)
    async with session_factory() as session:
        now = datetime.now(timezone.utc)
        user = User(
            id="svc-user-1",
            username="svcuser",
            password_hash="x",
            created_at=now,
        )
        session.add(user)
        await session.commit()
        yield session, user


@pytest.mark.asyncio
async def test_service_add_hd_wallet_creates_hd_type(service_db):
    db, user = service_db
    service = WalletService(db=db, user=user)
    wallet = await service._add_hd_wallet(VALID_XPUB, "My xpub")
    await db.commit()

    assert wallet.wallet_type == "hd"
    assert wallet.extended_key_type == "xpub"
    assert wallet.address == VALID_XPUB
    assert wallet.network == "BTC"
    assert wallet.tag == "My xpub"


@pytest.mark.asyncio
async def test_service_add_hd_wallet_ypub_key_type(service_db):
    db, user = service_db
    service = WalletService(db=db, user=user)
    wallet = await service._add_hd_wallet(VALID_YPUB, None)
    await db.commit()

    assert wallet.extended_key_type == "ypub"


@pytest.mark.asyncio
async def test_service_add_hd_wallet_zpub_key_type(service_db):
    db, user = service_db
    service = WalletService(db=db, user=user)
    wallet = await service._add_hd_wallet(VALID_ZPUB, None)
    await db.commit()

    assert wallet.extended_key_type == "zpub"


@pytest.mark.asyncio
async def test_service_add_hd_wallet_default_tag_is_btc_hd_wallet(service_db):
    db, user = service_db
    service = WalletService(db=db, user=user)
    wallet = await service._add_hd_wallet(VALID_XPUB, None)
    await db.commit()

    assert wallet.tag == "BTC HD Wallet #1"


@pytest.mark.asyncio
async def test_service_add_hd_wallet_invalid_raises(service_db):
    from backend.core.exceptions import (
        AddressValidationError,
        ExtendedKeyValidationError,
    )

    db, user = service_db
    service = WalletService(db=db, user=user)

    # Must raise ExtendedKeyValidationError (subclass of AddressValidationError)
    with pytest.raises(ExtendedKeyValidationError):
        await service._add_hd_wallet(VALID_TPUB, None)

    # Verify it is also caught by the parent class (router compatibility)
    with pytest.raises(AddressValidationError):
        await service._add_hd_wallet(BAD_CHECKSUM_XPUB, None)


@pytest.mark.asyncio
async def test_service_add_hd_wallet_duplicate_raises(service_db):
    from backend.core.exceptions import DuplicateWalletError

    db, user = service_db
    service = WalletService(db=db, user=user)

    await service._add_hd_wallet(VALID_XPUB, "First")
    await db.commit()

    with pytest.raises(DuplicateWalletError):
        await service._add_hd_wallet(VALID_XPUB, "Second")


# ---------------------------------------------------------------------------
# Test: add_wallet() routes BTC to _add_hd_wallet when xpub detected
# (also covers hd wallet no-active-addresses scenario)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_hd_wallet_no_active_addresses(hd_client, auth_headers):
    """New xpub with zero transactions: wallet saved, balance=None (pending)."""
    resp = await add_wallet_http(hd_client, auth_headers, "BTC", VALID_XPUB)
    assert resp.status_code == 201
    data = resp.json()
    # No balance snapshot yet (background task mocked out at HTTP level)
    assert data["balance"] is None
    assert data["wallet_type"] == "hd"
