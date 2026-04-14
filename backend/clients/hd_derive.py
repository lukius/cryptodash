"""Pure-Python BIP32 HD address derivation.

Derives addresses from account-level extended public keys (xpub/ypub/zpub)
using only stdlib: hashlib, hmac, struct.

Supports:
- BIP84 (zpub) → P2WPKH bech32 addresses (bc1q...)
- BIP49 (ypub) → P2SH-P2WPKH base58check addresses (3...)
- BIP44 (xpub) → P2PKH base58check addresses (1...)

Public API
----------
derive_address_at(key, chain, index) -> str
"""

import hashlib
import hmac
import struct

# ---------------------------------------------------------------------------
# secp256k1 curve parameters
# ---------------------------------------------------------------------------

_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
_Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
_Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8

# Point at infinity sentinel
_INFINITY = (None, None)


def _point_add(P, Q):
    """Elliptic curve point addition on secp256k1."""
    if P == _INFINITY:
        return Q
    if Q == _INFINITY:
        return P
    px, py = P
    qx, qy = Q
    if px == qx:
        if py != qy:
            return _INFINITY
        # Point doubling
        lam = (3 * px * px) * pow(2 * py, _P - 2, _P) % _P
    else:
        lam = (qy - py) * pow(qx - px, _P - 2, _P) % _P
    rx = (lam * lam - px - qx) % _P
    ry = (lam * (px - rx) - py) % _P
    return (rx, ry)


def _point_mul(k, P):
    """Scalar multiplication on secp256k1 using double-and-add."""
    result = _INFINITY
    addend = P
    while k:
        if k & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        k >>= 1
    return result


def _pubkey_to_bytes(point) -> bytes:
    """Compress an (x, y) curve point to 33-byte compressed pubkey."""
    x, y = point
    prefix = b"\x02" if y % 2 == 0 else b"\x03"
    return prefix + x.to_bytes(32, "big")


def _parse_compressed_pubkey(data: bytes):
    """Parse a 33-byte compressed public key back to an (x, y) curve point."""
    prefix = data[0]
    x = int.from_bytes(data[1:], "big")
    y_sq = (pow(x, 3, _P) + 7) % _P
    y = pow(y_sq, (_P + 1) // 4, _P)
    if (y % 2 == 0) != (prefix == 0x02):
        y = _P - y
    return (x, y)


# ---------------------------------------------------------------------------
# Base58Check codec (standalone — do NOT import from services.wallet)
# ---------------------------------------------------------------------------

_BASE58_CHARS = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_BASE58_MAP = {c: i for i, c in enumerate(_BASE58_CHARS)}


def _b58decode(s: str) -> bytes:
    num = 0
    for ch in s:
        if ch not in _BASE58_MAP:
            raise ValueError(f"Invalid Base58 character: {ch!r}")
        num = num * 58 + _BASE58_MAP[ch]
    leading = len(s) - len(s.lstrip("1"))
    byte_len = (num.bit_length() + 7) // 8 if num > 0 else 1
    return b"\x00" * leading + num.to_bytes(byte_len, "big")


def _b58encode(data: bytes) -> str:
    num = int.from_bytes(data, "big")
    result: list[str] = []
    while num > 0:
        num, rem = divmod(num, 58)
        result.append(_BASE58_CHARS[rem])
    leading = len(data) - len(data.lstrip(b"\x00"))
    return "1" * leading + "".join(reversed(result))


def _b58decode_check(s: str) -> bytes:
    """Decode Base58Check; raises ValueError on checksum mismatch."""
    decoded = _b58decode(s)
    if len(decoded) < 4:
        raise ValueError("Too short for Base58Check")
    payload, checksum = decoded[:-4], decoded[-4:]
    expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    if checksum != expected:
        raise ValueError("Base58Check checksum mismatch")
    return payload


def _b58encode_check(payload: bytes) -> str:
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return _b58encode(payload + checksum)


# ---------------------------------------------------------------------------
# Extended key version bytes
# ---------------------------------------------------------------------------

_VERSIONS = {
    bytes.fromhex("0488B21E"): "xpub",
    bytes.fromhex("049D7CB2"): "ypub",
    bytes.fromhex("04B24746"): "zpub",
}


def _parse_extended_key(key: str) -> tuple[bytes, bytes, str]:
    """Parse an account-level extended public key.

    Returns (pubkey_33_bytes, chaincode_32_bytes, key_type_str).
    key_type_str is one of 'xpub', 'ypub', 'zpub'.
    """
    payload = _b58decode_check(key)
    if len(payload) != 78:
        raise ValueError(f"Extended key payload must be 78 bytes, got {len(payload)}")
    version = payload[:4]
    key_type = _VERSIONS.get(version)
    if key_type is None:
        raise ValueError(f"Unrecognized extended key version: {version.hex()}")
    chaincode = payload[13:45]
    pubkey = payload[45:78]
    return pubkey, chaincode, key_type


# ---------------------------------------------------------------------------
# BIP32 child key derivation (public, non-hardened)
# ---------------------------------------------------------------------------


def _derive_child_pubkey(
    parent_pubkey: bytes, parent_chaincode: bytes, index: int
) -> tuple[bytes, bytes]:
    """Derive a non-hardened child public key at the given index.

    Returns (child_pubkey_33_bytes, child_chaincode_32_bytes).
    """
    data = parent_pubkey + struct.pack(">I", index)
    I = hmac.new(parent_chaincode, data, hashlib.sha512).digest()  # noqa: E741
    IL, IR = I[:32], I[32:]
    IL_int = int.from_bytes(IL, "big")
    if IL_int >= _N:
        raise ValueError("Derived key is invalid (IL >= N)")
    parent_point = _parse_compressed_pubkey(parent_pubkey)
    child_point = _point_add(_point_mul(IL_int, (_Gx, _Gy)), parent_point)
    if child_point == _INFINITY:
        raise ValueError("Derived key is the point at infinity")
    child_pubkey = _pubkey_to_bytes(child_point)
    return child_pubkey, IR


# ---------------------------------------------------------------------------
# Address encoding helpers
# ---------------------------------------------------------------------------


def _hash160(data: bytes) -> bytes:
    """RIPEMD-160(SHA-256(data))."""
    sha256 = hashlib.sha256(data).digest()
    ripemd = hashlib.new("ripemd160", sha256).digest()
    return ripemd


# Bech32 charset
_BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _bech32_polymod(values):
    GEN = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ v
        for i in range(5):
            chk ^= GEN[i] if ((b >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp):
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _convertbits(data, frombits, tobits, pad=True):
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


def _bech32_encode(hrp: str, witver: int, witprog: bytes) -> str:
    """Encode a bech32 address (segwit v0)."""
    data = [witver] + _convertbits(witprog, 8, 5)
    combined = data + [0, 0, 0, 0, 0, 0]
    checksum = _bech32_polymod(_bech32_hrp_expand(hrp) + combined) ^ 1
    return hrp + "1" + "".join([_BECH32_CHARSET[d] for d in data]) + "".join(
        [_BECH32_CHARSET[(checksum >> (5 * (5 - i))) & 31] for i in range(6)]
    )


def _p2wpkh_address(pubkey: bytes) -> str:
    """BIP84: P2WPKH bech32 address from 33-byte compressed pubkey."""
    keyhash = _hash160(pubkey)
    return _bech32_encode("bc", 0, keyhash)


def _p2sh_p2wpkh_address(pubkey: bytes) -> str:
    """BIP49: P2SH-P2WPKH address (3...) from 33-byte compressed pubkey."""
    keyhash = _hash160(pubkey)
    # redeem script: OP_0 <20-byte-key-hash>
    redeem_script = b"\x00\x14" + keyhash
    script_hash = _hash160(redeem_script)
    return _b58encode_check(b"\x05" + script_hash)


def _p2pkh_address(pubkey: bytes) -> str:
    """BIP44: P2PKH address (1...) from 33-byte compressed pubkey."""
    keyhash = _hash160(pubkey)
    return _b58encode_check(b"\x00" + keyhash)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def derive_address_at(key: str, chain: int, index: int) -> str:
    """Derive the address at m/.../chain/index from an account-level extended key.

    Parameters
    ----------
    key   : xpub/ypub/zpub account-level extended public key string
    chain : 0 = external/receive, 1 = internal/change
    index : child index (non-hardened, 0-based)

    Returns
    -------
    Bitcoin address string appropriate for the key type:
    - zpub → bc1q... (P2WPKH)
    - ypub → 3...   (P2SH-P2WPKH)
    - xpub → 1...   (P2PKH)
    """
    pubkey, chaincode, key_type = _parse_extended_key(key)

    # Derive the chain-level key (m/.../chain)
    chain_pubkey, chain_chaincode = _derive_child_pubkey(pubkey, chaincode, chain)
    # Derive the address-level key (m/.../chain/index)
    addr_pubkey, _ = _derive_child_pubkey(chain_pubkey, chain_chaincode, index)

    if key_type == "zpub":
        return _p2wpkh_address(addr_pubkey)
    elif key_type == "ypub":
        return _p2sh_p2wpkh_address(addr_pubkey)
    else:  # xpub
        return _p2pkh_address(addr_pubkey)
