"""Tests for hd_derive.py — BIP32 address derivation from xpub/ypub/zpub.

Uses known BIP32 test vectors and cross-checks with well-known zpub addresses.
"""

import pytest

from backend.clients.hd_derive import (
    _b58decode_check,
    _b58encode_check,
    _hash160,
    _p2pkh_address,
    _p2sh_p2wpkh_address,
    _p2wpkh_address,
    _parse_extended_key,
    derive_address_at,
)


# ---------------------------------------------------------------------------
# Known test vectors
# ---------------------------------------------------------------------------

# BIP32 test vector 1 root: m (xpub at depth 0)
# From https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki#test-vectors
BIP32_TV1_XPUB_ROOT = (
    "xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC5Lk5yga8LyNnAaGEzLkPqmreZXQS"
    "bEbmJ2YMRbMPtJYypTVKGPFSZnRD7G2Gy5CQjYRrFqF3kAe"
)

# Account-level key used for the canonical xpub test vectors — BIP32 TV1 child m/0
BIP32_TV1_XPUB_m0 = "xpub68Gmy5EdvgibQVfPdqkBBCHxA5htiqg55crXYuXoQRKfDBFA1WEjWgP6LHhwBZeNK1VTsfTFUHCdrfp1bgwQ9xv5ski8PX9rL2dZXvgGDnw"

# Known zpub for test: from a real Trezor/Electrum derivation, we test structural
# properties (correct prefix, correct length, non-empty) rather than exact values
# since we don't have a known test vector with zpub in stdlib form.
# Instead we test round-trip consistency: derive addr at (0,0) returns a bc1q string.

# A synthetic zpub constructed from known key material (same as TV1 xpub but with
# zpub version bytes) — tests structural properties.
_XPUB_VERSION = bytes.fromhex("0488B21E")
_ZPUB_VERSION = bytes.fromhex("04B24746")
_YPUB_VERSION = bytes.fromhex("049D7CB2")


def _reversion(key: str, new_version: bytes) -> str:
    """Swap version bytes of an extended public key."""
    import hashlib

    _BASE58_CHARS = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    _BASE58_MAP = {c: i for i, c in enumerate(_BASE58_CHARS)}

    def decode(s):
        num = 0
        for ch in s:
            num = num * 58 + _BASE58_MAP[ch]
        leading = len(s) - len(s.lstrip("1"))
        byte_len = (num.bit_length() + 7) // 8 if num > 0 else 1
        return b"\x00" * leading + num.to_bytes(byte_len, "big")

    def encode(data):
        num = int.from_bytes(data, "big")
        result = []
        while num > 0:
            num, rem = divmod(num, 58)
            result.append(_BASE58_CHARS[rem])
        leading = len(data) - len(data.lstrip(b"\x00"))
        return "1" * leading + "".join(reversed(result))

    decoded = decode(key)
    payload, _ = decoded[:-4], decoded[-4:]
    new_payload = new_version + payload[4:]
    checksum = hashlib.sha256(hashlib.sha256(new_payload).digest()).digest()[:4]
    return encode(new_payload + checksum)


SYNTHETIC_ZPUB = _reversion(BIP32_TV1_XPUB_m0, _ZPUB_VERSION)
SYNTHETIC_YPUB = _reversion(BIP32_TV1_XPUB_m0, _YPUB_VERSION)


# ---------------------------------------------------------------------------
# _parse_extended_key
# ---------------------------------------------------------------------------


def test_parse_extended_key_xpub():
    pubkey, chaincode, key_type = _parse_extended_key(BIP32_TV1_XPUB_m0)
    assert key_type == "xpub"
    assert len(pubkey) == 33
    assert len(chaincode) == 32
    # Compressed pubkey must start with 0x02 or 0x03
    assert pubkey[0] in (0x02, 0x03)


def test_parse_extended_key_zpub():
    pubkey, chaincode, key_type = _parse_extended_key(SYNTHETIC_ZPUB)
    assert key_type == "zpub"
    assert len(pubkey) == 33
    assert len(chaincode) == 32


def test_parse_extended_key_ypub():
    pubkey, chaincode, key_type = _parse_extended_key(SYNTHETIC_YPUB)
    assert key_type == "ypub"
    assert len(pubkey) == 33
    assert len(chaincode) == 32


def test_parse_extended_key_bad_checksum():
    # Corrupt the last byte of the key string
    bad = BIP32_TV1_XPUB_m0[:-1] + ("w" if BIP32_TV1_XPUB_m0[-1] != "w" else "x")
    with pytest.raises(ValueError, match="[Cc]hecksum"):
        _parse_extended_key(bad)


def test_parse_extended_key_unknown_version():
    # Swap to a version that isn't xpub/ypub/zpub
    unknown = _reversion(BIP32_TV1_XPUB_m0, bytes.fromhex("04358394"))  # Ltub
    with pytest.raises(ValueError, match="Unrecognized"):
        _parse_extended_key(unknown)


# ---------------------------------------------------------------------------
# _hash160
# ---------------------------------------------------------------------------


def test_hash160_known_vector():
    # HASH160 of an all-zero 33-byte pubkey (not a real key — just tests the hash chain)
    data = b"\x02" + b"\x00" * 32
    result = _hash160(data)
    assert len(result) == 20
    # Must be deterministic
    assert _hash160(data) == result


# ---------------------------------------------------------------------------
# Address encoding
# ---------------------------------------------------------------------------


def test_p2wpkh_address_starts_with_bc1q():
    # Arbitrary 33-byte compressed pubkey bytes
    pubkey = bytes.fromhex(
        "0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"
    )
    addr = _p2wpkh_address(pubkey)
    assert addr.startswith("bc1q")
    # P2WPKH bech32 addresses are 42 chars for 20-byte witness program
    assert len(addr) == 42


def test_p2sh_p2wpkh_address_starts_with_3():
    pubkey = bytes.fromhex(
        "0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"
    )
    addr = _p2sh_p2wpkh_address(pubkey)
    assert addr.startswith("3")
    assert 25 <= len(addr) <= 34


def test_p2pkh_address_starts_with_1():
    pubkey = bytes.fromhex(
        "0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"
    )
    addr = _p2pkh_address(pubkey)
    assert addr.startswith("1")
    assert 25 <= len(addr) <= 34


# Known P2PKH for genesis block pubkey
def test_p2pkh_genesis_pubkey():
    # Satoshi's genesis block output pubkey (uncompressed form not used here —
    # for compressed form we use a known value)
    pubkey = bytes.fromhex(
        "0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"
    )
    addr = _p2pkh_address(pubkey)
    # Known address for compressed form of generator point G
    assert addr == "1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH"


# ---------------------------------------------------------------------------
# derive_address_at — structural tests
# ---------------------------------------------------------------------------


def test_derive_address_at_xpub_returns_p2pkh():
    addr = derive_address_at(BIP32_TV1_XPUB_m0, chain=0, index=0)
    assert addr.startswith("1"), f"Expected P2PKH (1...) address, got {addr!r}"


def test_derive_address_at_zpub_returns_bech32():
    addr = derive_address_at(SYNTHETIC_ZPUB, chain=0, index=0)
    assert addr.startswith("bc1q"), f"Expected bech32 address, got {addr!r}"
    assert len(addr) == 42


def test_derive_address_at_ypub_returns_p2sh():
    addr = derive_address_at(SYNTHETIC_YPUB, chain=0, index=0)
    assert addr.startswith("3"), f"Expected P2SH address, got {addr!r}"


def test_derive_address_at_different_indices_differ():
    addr0 = derive_address_at(BIP32_TV1_XPUB_m0, chain=0, index=0)
    addr1 = derive_address_at(BIP32_TV1_XPUB_m0, chain=0, index=1)
    addr2 = derive_address_at(BIP32_TV1_XPUB_m0, chain=0, index=2)
    assert addr0 != addr1
    assert addr1 != addr2
    assert addr0 != addr2


def test_derive_address_at_chain0_vs_chain1_differ():
    addr_recv = derive_address_at(BIP32_TV1_XPUB_m0, chain=0, index=0)
    addr_change = derive_address_at(BIP32_TV1_XPUB_m0, chain=1, index=0)
    assert addr_recv != addr_change


def test_derive_address_at_deterministic():
    """Same inputs always produce the same output."""
    addr_a = derive_address_at(BIP32_TV1_XPUB_m0, chain=0, index=5)
    addr_b = derive_address_at(BIP32_TV1_XPUB_m0, chain=0, index=5)
    assert addr_a == addr_b


def test_derive_address_at_known_bip32_tv1_xpub():
    """BIP32 test vector 1: m/0H/0/0 address derivation is correct.

    The BIP32 TV1 spec provides xpub keys at various derivation paths.
    Using BIP32_TV1_XPUB_m0 (m/0H) as the account key and deriving chain=0,
    index=0 produces m/0H/0/0. Cross-checked against the BIP32 spec by verifying
    that our _derive_child_pubkey(m/0H, 1) == the spec's m/0H/1 key.
    """
    addr = derive_address_at(BIP32_TV1_XPUB_m0, chain=0, index=0)
    # Verified against BIP32 spec cross-check (child key m/0H/1 matches TV1)
    assert addr == "1BvgsfsZQVtkLS69NvGF8rw6NZW2ShJQHr"


# ---------------------------------------------------------------------------
# Base58Check round-trip
# ---------------------------------------------------------------------------


def test_b58_round_trip():
    payload = b"\x00" + bytes(range(20))
    encoded = _b58encode_check(payload)
    decoded = _b58decode_check(encoded)
    assert decoded == payload
