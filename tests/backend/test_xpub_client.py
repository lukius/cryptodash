"""Tests for XpubClient — Trezor Blockbook backend for HD wallet queries."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from backend.clients.xpub import (
    SATOSHI,
    DerivedAddressData,
    XpubClient,
    XpubSummary,
    XpubTransaction,
)

BASE_URL = "https://btc2.trezor.io/api/v2"

# A real BIP84 zpub (used here only as an opaque path component — no key
# material is dereferenced locally).
ZPUB = (
    "zpub6qgBZX81kMmpeFYY5v3YssHmJXA4hHh6dL9HVpPPKr8dpBiRZX"
    "qRT2wiMyLaqkXcX5ARMkHZEk6q6tuGqgkSNoftw2ZEGsD3ok7WsZDkTBA"
)
XPUB_URL_RE = r"https://btc2\.trezor\.io/api/v2/xpub/[^?]+"
STATUS_URL = f"{BASE_URL}/api"


def _xpub_summary_response(
    balance: int = 0,
    n_tx: int = 0,
    tokens: list[dict] | None = None,
) -> dict:
    """Build a minimal Blockbook /xpub/{key}?details=tokenBalances response."""
    return {
        "address": ZPUB,
        "balance": str(balance),
        "totalReceived": str(max(balance, 0)),
        "totalSent": "0",
        "unconfirmedBalance": "0",
        "unconfirmedTxs": 0,
        "txs": n_tx,
        "addrTxCount": n_tx,
        "usedTokens": len(tokens) if tokens else 0,
        "tokens": tokens or [],
    }


def _token(
    address: str,
    balance: int,
    transfers: int = 1,
    path: str = "m/84'/0'/0'/0/0",
) -> dict:
    return {
        "type": "XPUBAddress",
        "standard": "XPUBAddress",
        "name": address,
        "path": path,
        "transfers": transfers,
        "decimals": 8,
        "balance": str(balance),
        "totalReceived": str(max(balance, 0)),
        "totalSent": "0",
    }


def _tx(
    txid: str,
    block_time: int | None,
    block_height: int | None,
    vout: list[dict] | None = None,
    vin: list[dict] | None = None,
    confirmations: int = 1,
) -> dict:
    """Build a minimal Blockbook tx object."""
    return {
        "txid": txid,
        "version": 1,
        "blockHash": "deadbeef" if block_height is not None else None,
        "blockHeight": block_height,
        "confirmations": confirmations,
        "blockTime": block_time,
        "size": 200,
        "vsize": 150,
        "value": "0",
        "valueIn": "0",
        "fees": "0",
        "vin": vin or [],
        "vout": vout or [],
    }


def _vout(addr: str, value: int, n: int = 0) -> dict:
    return {
        "value": str(value),
        "n": n,
        "hex": "00",
        "addresses": [addr],
        "isAddress": True,
    }


def _vin(addr: str, value: int, n: int = 0) -> dict:
    return {
        "txid": "prev" + str(n),
        "vout": 0,
        "sequence": 0xFFFFFFFF,
        "n": n,
        "addresses": [addr],
        "isAddress": True,
        "value": str(value),
    }


def _txs_page_response(
    page: int,
    total_pages: int,
    transactions: list[dict],
    tokens: list[dict] | None = None,
    balance: int = 0,
) -> dict:
    """Build a Blockbook /xpub/{key}?details=txs paginated response."""
    return {
        "page": page,
        "totalPages": total_pages,
        "itemsOnPage": len(transactions),
        "address": ZPUB,
        "balance": str(balance),
        "totalReceived": "0",
        "totalSent": "0",
        "unconfirmedBalance": "0",
        "unconfirmedTxs": 0,
        "txs": len(transactions),
        "addrTxCount": len(transactions),
        "usedTokens": len(tokens) if tokens else 0,
        "tokens": tokens or [],
        "transactions": transactions,
    }


@pytest.fixture
def client():
    return XpubClient()


# ---------------------------------------------------------------------------
# Constants and dataclasses
# ---------------------------------------------------------------------------


def test_satoshi_constant():
    assert SATOSHI == Decimal("100000000")


def test_xpub_summary_fields():
    derived = [DerivedAddressData(address="bc1qfoo", balance_sat=1000, n_tx=1)]
    summary = XpubSummary(
        balance_sat=1000,
        balance_btc=Decimal("0.00001"),
        n_tx=1,
        derived_addresses=derived,
    )
    assert summary.balance_sat == 1000
    assert summary.derived_addresses == derived


def test_xpub_transaction_fields():
    tx = XpubTransaction(
        tx_hash="abc",
        timestamp=1700000000,
        block_height=820000,
        amount_sat=50000,
    )
    assert tx.tx_hash == "abc"
    assert tx.amount_sat == 50000


# ---------------------------------------------------------------------------
# get_tip_height
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_tip_height(client):
    respx.get(STATUS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "blockbook": {"bestHeight": 946638},
                "backend": {"blocks": 946638},
            },
        )
    )
    assert await client.get_tip_height() == 946638


@respx.mock
async def test_get_tip_height_propagates_5xx(client):
    respx.get(STATUS_URL).mock(return_value=httpx.Response(500))
    with pytest.raises(httpx.HTTPStatusError):
        await client.get_tip_height()


# ---------------------------------------------------------------------------
# get_xpub_summary
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_xpub_summary_empty_wallet(client):
    """Empty xpub → balance=0, no derived addresses."""
    respx.get(url__regex=XPUB_URL_RE).mock(
        return_value=httpx.Response(200, json=_xpub_summary_response())
    )
    summary = await client.get_xpub_summary(ZPUB)

    assert isinstance(summary, XpubSummary)
    assert summary.balance_sat == 0
    assert summary.balance_btc == Decimal("0")
    assert summary.n_tx == 0
    assert summary.derived_addresses == []


@respx.mock
async def test_get_xpub_summary_with_active_addresses(client):
    """Active addresses with positive balance appear in derived_addresses."""
    tokens = [
        _token("bc1qaaa", 50_000_000, transfers=2, path="m/84'/0'/0'/0/0"),
        _token("bc1qbbb", 30_000_000, transfers=1, path="m/84'/0'/0'/0/1"),
    ]
    respx.get(url__regex=XPUB_URL_RE).mock(
        return_value=httpx.Response(
            200, json=_xpub_summary_response(balance=80_000_000, n_tx=3, tokens=tokens)
        )
    )

    summary = await client.get_xpub_summary(ZPUB)
    assert summary.balance_sat == 80_000_000
    assert summary.balance_btc == Decimal("0.8")
    assert summary.n_tx == 3
    assert len(summary.derived_addresses) == 2
    assert summary.derived_addresses[0].address == "bc1qaaa"
    assert summary.derived_addresses[0].balance_sat == 50_000_000
    assert summary.derived_addresses[0].n_tx == 2


@respx.mock
async def test_get_xpub_summary_excludes_zero_balance(client):
    """Tokens with balance=0 are filtered out, even when transfers > 0."""
    tokens = [
        _token("bc1qfunded", 50_000_000, transfers=1),
        _token("bc1qspent", 0, transfers=2),  # fully spent active addr
    ]
    respx.get(url__regex=XPUB_URL_RE).mock(
        return_value=httpx.Response(
            200, json=_xpub_summary_response(balance=50_000_000, n_tx=3, tokens=tokens)
        )
    )

    summary = await client.get_xpub_summary(ZPUB)
    assert summary.balance_sat == 50_000_000
    # n_tx still reflects on-chain activity from the aggregate field
    assert summary.n_tx == 3
    assert len(summary.derived_addresses) == 1
    assert summary.derived_addresses[0].address == "bc1qfunded"


@respx.mock
async def test_get_xpub_summary_uses_single_call(client):
    """get_xpub_summary issues exactly one HTTP request (no per-address fan-out)."""
    route = respx.get(url__regex=XPUB_URL_RE).mock(
        return_value=httpx.Response(200, json=_xpub_summary_response())
    )
    await client.get_xpub_summary(ZPUB)
    assert route.call_count == 1


@respx.mock
async def test_get_xpub_summary_requests_tokenbalances_detail(client):
    """The summary call must request tokenBalances + tokens=used."""
    route = respx.get(url__regex=XPUB_URL_RE).mock(
        return_value=httpx.Response(200, json=_xpub_summary_response())
    )
    await client.get_xpub_summary(ZPUB)
    qs = route.calls.last.request.url.params
    assert qs["details"] == "tokenBalances"
    assert qs["tokens"] == "used"


@respx.mock
async def test_get_xpub_summary_propagates_5xx(client):
    respx.get(url__regex=XPUB_URL_RE).mock(return_value=httpx.Response(500))
    with pytest.raises(httpx.HTTPStatusError):
        await client.get_xpub_summary(ZPUB)


# ---------------------------------------------------------------------------
# get_xpub_transactions_all
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_xpub_transactions_all_empty(client):
    respx.get(url__regex=XPUB_URL_RE).mock(
        return_value=httpx.Response(
            200, json=_txs_page_response(page=1, total_pages=0, transactions=[])
        )
    )
    txs = await client.get_xpub_transactions_all(ZPUB)
    assert txs == []


@respx.mock
async def test_get_xpub_transactions_all_single_page(client):
    """A single-page wallet returns all transactions sorted oldest-first."""
    addr0 = "bc1qaaa"
    addr1 = "bc1qbbb"
    tokens = [_token(addr0, 0, transfers=1), _token(addr1, 0, transfers=1)]
    transactions = [
        _tx(
            txid="newer",
            block_time=1700001000,
            block_height=820001,
            vout=[_vout(addr0, 5_000_000)],
        ),
        _tx(
            txid="older",
            block_time=1700000000,
            block_height=820000,
            vout=[_vout(addr1, 10_000_000)],
        ),
    ]
    respx.get(url__regex=XPUB_URL_RE).mock(
        return_value=httpx.Response(
            200,
            json=_txs_page_response(
                page=1, total_pages=1, transactions=transactions, tokens=tokens
            ),
        )
    )

    txs = await client.get_xpub_transactions_all(ZPUB)
    assert len(txs) == 2
    assert txs[0].tx_hash == "older"
    assert txs[1].tx_hash == "newer"
    assert txs[0].timestamp <= txs[1].timestamp


@respx.mock
async def test_get_xpub_transactions_all_paginates(client):
    """Multi-page responses are concatenated until totalPages is reached."""
    addr = "bc1qaaa"
    tokens = [_token(addr, 0, transfers=2)]

    def make_tx(txid: str, t: int, h: int) -> dict:
        return _tx(txid=txid, block_time=t, block_height=h, vout=[_vout(addr, 1000)])

    page_responses = {
        1: _txs_page_response(
            page=1,
            total_pages=2,
            transactions=[make_tx("t2", 1700002000, 820002)],
            tokens=tokens,
        ),
        2: _txs_page_response(
            page=2,
            total_pages=2,
            transactions=[make_tx("t1", 1700001000, 820001)],
            tokens=tokens,
        ),
    }

    def handler(request):
        page = int(request.url.params.get("page", "1"))
        return httpx.Response(200, json=page_responses[page])

    respx.get(url__regex=XPUB_URL_RE).mock(side_effect=handler)

    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        txs = await client.get_xpub_transactions_all(ZPUB)

    assert [t.tx_hash for t in txs] == ["t1", "t2"]


@respx.mock
async def test_get_xpub_transactions_all_skips_unconfirmed(client):
    """Transactions with confirmations=0 / blockTime=null are excluded."""
    addr = "bc1qaaa"
    tokens = [_token(addr, 0, transfers=2)]
    confirmed = _tx(
        txid="confirmed",
        block_time=1700000000,
        block_height=820000,
        vout=[_vout(addr, 10_000_000)],
        confirmations=3,
    )
    unconfirmed = _tx(
        txid="pending",
        block_time=None,
        block_height=None,
        vout=[_vout(addr, 5_000_000)],
        confirmations=0,
    )
    respx.get(url__regex=XPUB_URL_RE).mock(
        return_value=httpx.Response(
            200,
            json=_txs_page_response(
                page=1,
                total_pages=1,
                transactions=[unconfirmed, confirmed],
                tokens=tokens,
            ),
        )
    )

    txs = await client.get_xpub_transactions_all(ZPUB)
    assert len(txs) == 1
    assert txs[0].tx_hash == "confirmed"


@respx.mock
async def test_get_xpub_transactions_all_net_amount_incoming(client):
    """Pure incoming tx → positive net amount."""
    addr = "bc1qaaa"
    tokens = [_token(addr, 0, transfers=1)]
    transactions = [
        _tx(
            txid="incoming",
            block_time=1700000000,
            block_height=820000,
            vout=[_vout(addr, 100_000_000), _vout("bc1qexternal", 50_000_000, n=1)],
            vin=[_vin("bc1qsender", 200_000_000)],
        )
    ]
    respx.get(url__regex=XPUB_URL_RE).mock(
        return_value=httpx.Response(
            200,
            json=_txs_page_response(
                page=1, total_pages=1, transactions=transactions, tokens=tokens
            ),
        )
    )

    txs = await client.get_xpub_transactions_all(ZPUB)
    assert txs[0].amount_sat == 100_000_000


@respx.mock
async def test_get_xpub_transactions_all_net_amount_outgoing(client):
    """Outgoing tx → negative net amount; change to wallet partially offsets the outflow."""
    receive_addr = "bc1qreceive"
    change_addr = "bc1qchange"
    tokens = [_token(receive_addr, 0), _token(change_addr, 0)]

    transactions = [
        _tx(
            txid="spend",
            block_time=1700000000,
            block_height=820000,
            vin=[_vin(receive_addr, 100_000)],
            vout=[
                _vout(change_addr, 60_000),  # change back to wallet
                _vout("bc1qexternal", 30_000, n=1),
            ],
        )
    ]
    respx.get(url__regex=XPUB_URL_RE).mock(
        return_value=httpx.Response(
            200,
            json=_txs_page_response(
                page=1, total_pages=1, transactions=transactions, tokens=tokens
            ),
        )
    )

    txs = await client.get_xpub_transactions_all(ZPUB)
    # 60k change in - 100k spent = -40k net
    assert txs[0].amount_sat == -40_000


@respx.mock
async def test_get_xpub_transactions_all_ignores_non_address_outputs(client):
    """OP_RETURN / non-address vouts (isAddress=false) don't contribute to net amount."""
    addr = "bc1qaaa"
    tokens = [_token(addr, 0)]
    transactions = [
        _tx(
            txid="op_return",
            block_time=1700000000,
            block_height=820000,
            vin=[_vin(addr, 50_000)],
            vout=[
                {
                    "value": "0",
                    "n": 0,
                    "hex": "6a04deadbeef",
                    "addresses": ["OP_RETURN (OP_RETURN deadbeef)"],
                    "isAddress": False,
                },
                _vout("bc1qexternal", 49_000, n=1),
            ],
        )
    ]
    respx.get(url__regex=XPUB_URL_RE).mock(
        return_value=httpx.Response(
            200,
            json=_txs_page_response(
                page=1, total_pages=1, transactions=transactions, tokens=tokens
            ),
        )
    )

    txs = await client.get_xpub_transactions_all(ZPUB)
    # Net = 0 in - 50k out = -50k
    assert txs[0].amount_sat == -50_000


# ---------------------------------------------------------------------------
# get_xpub_transactions_since — incremental sync
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_xpub_transactions_since_filters_by_timestamp(client):
    """Txs with blockTime > after_timestamp are returned; older ones are filtered."""
    addr = "bc1qaaa"
    tokens = [_token(addr, 0, transfers=2)]
    after_ts = 1700000000

    transactions = [
        _tx(
            txid="new",
            block_time=1700001000,
            block_height=820001,
            vout=[_vout(addr, 5_000_000)],
        ),
        _tx(
            txid="old",
            block_time=1700000000,  # exactly at cutoff — must be excluded
            block_height=820000,
            vout=[_vout(addr, 10_000_000)],
        ),
    ]

    respx.get(url__regex=XPUB_URL_RE).mock(
        return_value=httpx.Response(
            200,
            json=_txs_page_response(
                page=1, total_pages=1, transactions=transactions, tokens=tokens
            ),
        )
    )

    txs = await client.get_xpub_transactions_since(ZPUB, after_ts)
    assert len(txs) == 1
    assert txs[0].tx_hash == "new"


@respx.mock
async def test_get_xpub_transactions_since_stops_paginating_after_cutoff(client):
    """Pagination stops once a tx older than after_timestamp is observed."""
    addr = "bc1qaaa"
    tokens = [_token(addr, 0, transfers=1)]
    after_ts = 1700001000

    page1 = _txs_page_response(
        page=1,
        total_pages=2,
        transactions=[
            _tx(
                txid="newer",
                block_time=1700002000,
                block_height=820002,
                vout=[_vout(addr, 1000)],
            ),
            _tx(
                txid="cutoff",
                block_time=1700000000,
                block_height=820000,
                vout=[_vout(addr, 1000)],
            ),
        ],
        tokens=tokens,
    )
    page2_called = False

    def handler(request):
        nonlocal page2_called
        page = int(request.url.params.get("page", "1"))
        if page == 1:
            return httpx.Response(200, json=page1)
        page2_called = True
        return httpx.Response(500, json={"error": "should not have been called"})

    respx.get(url__regex=XPUB_URL_RE).mock(side_effect=handler)

    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        txs = await client.get_xpub_transactions_since(ZPUB, after_ts)

    assert [t.tx_hash for t in txs] == ["newer"]
    assert not page2_called, "Pagination should stop once cutoff is crossed"


@respx.mock
async def test_get_xpub_transactions_since_empty_when_no_new_txs(client):
    """All txs at or before after_timestamp → empty result."""
    addr = "bc1qaaa"
    tokens = [_token(addr, 0, transfers=1)]
    after_ts = 1700005000

    transactions = [
        _tx(
            txid="old",
            block_time=1700000000,
            block_height=820000,
            vout=[_vout(addr, 10_000)],
        )
    ]

    respx.get(url__regex=XPUB_URL_RE).mock(
        return_value=httpx.Response(
            200,
            json=_txs_page_response(
                page=1, total_pages=1, transactions=transactions, tokens=tokens
            ),
        )
    )

    txs = await client.get_xpub_transactions_since(ZPUB, after_ts)
    assert txs == []
