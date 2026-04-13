"""Tests for BTC and KAS address validation functions (T07 ST5)."""

from backend.services.wallet import validate_btc_address, validate_kas_address


# ---------------------------------------------------------------------------
# BTC — P2PKH (starts with '1')
# ---------------------------------------------------------------------------


def test_btc_p2pkh_valid():
    assert validate_btc_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf") is None


def test_btc_p2pkh_valid_min_length():
    # 25 chars starting with 1, all valid Base58 chars
    assert validate_btc_address("1" + "A" * 24) is None


def test_btc_p2pkh_valid_max_length():
    assert validate_btc_address("1" + "A" * 33) is None


def test_btc_p2pkh_too_short():
    # 24 chars — below minimum of 25
    assert validate_btc_address("1" + "A" * 23) is not None


def test_btc_p2pkh_too_long():
    # 35 chars — above maximum of 34
    assert validate_btc_address("1" + "A" * 34) is not None


def test_btc_p2pkh_invalid_char_zero():
    # '0' is not in Base58 alphabet
    assert validate_btc_address("1A1zP1eP5QGef02DMPTfTL5SLmv7Div0") is not None


def test_btc_p2pkh_invalid_char_uppercase_o():
    # 'O' is not in Base58 alphabet
    assert validate_btc_address("1A1zP1eP5QGefiODMPTfTL5SLmv7Div") is not None


def test_btc_p2pkh_invalid_char_uppercase_i():
    # 'I' is not in Base58 alphabet
    assert validate_btc_address("1A1zP1eP5QGefiIDMPTfTL5SLmv7Div") is not None


def test_btc_p2pkh_invalid_char_lowercase_l():
    # 'l' is not in Base58 alphabet
    assert validate_btc_address("1A1zP1eP5QGefilDMPTfTL5SLmv7Div") is not None


# ---------------------------------------------------------------------------
# BTC — P2SH (starts with '3')
# ---------------------------------------------------------------------------


def test_btc_p2sh_valid():
    assert validate_btc_address("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy") is None


def test_btc_p2sh_valid_min_length():
    assert validate_btc_address("3" + "A" * 24) is None


def test_btc_p2sh_valid_max_length():
    assert validate_btc_address("3" + "A" * 33) is None


def test_btc_p2sh_too_short():
    assert validate_btc_address("3" + "A" * 23) is not None


def test_btc_p2sh_too_long():
    assert validate_btc_address("3" + "A" * 34) is not None


def test_btc_p2sh_invalid_char():
    assert validate_btc_address("3J98t1WpEZ73CNmQviecrnyiWrnqRh0NLy") is not None


# ---------------------------------------------------------------------------
# BTC — Bech32 SegWit v0 (bc1q, 42 or 62 chars)
# ---------------------------------------------------------------------------

# Valid SegWit v0: bc1q + 38 valid bech32 chars = 42 chars
_VALID_BC1Q_42 = "bc1q" + "a" * 38
# Valid SegWit v0: bc1q + 58 valid bech32 chars = 62 chars
_VALID_BC1Q_62 = "bc1q" + "a" * 58


def test_btc_bech32_segwit_v0_42_chars():
    assert validate_btc_address(_VALID_BC1Q_42) is None


def test_btc_bech32_segwit_v0_62_chars():
    assert validate_btc_address(_VALID_BC1Q_62) is None


def test_btc_bech32_segwit_v0_wrong_length_41():
    assert validate_btc_address("bc1q" + "a" * 37) is not None


def test_btc_bech32_segwit_v0_wrong_length_43():
    assert validate_btc_address("bc1q" + "a" * 39) is not None


def test_btc_bech32_segwit_v0_wrong_length_61():
    assert validate_btc_address("bc1q" + "a" * 57) is not None


def test_btc_bech32_segwit_v0_wrong_length_63():
    assert validate_btc_address("bc1q" + "a" * 59) is not None


def test_btc_bech32_segwit_v0_mixed_case_normalized():
    # The validator lowercases bc1q addresses before checking, so mixed case is accepted
    mixed = "bc1q" + "A" * 38
    assert validate_btc_address(mixed) is None


def test_btc_bech32_segwit_v0_invalid_char_b():
    # 'b' is not in the bech32 character set [023456789acdefghjklmnpqrstuvwxyz]
    assert validate_btc_address("bc1q" + "b" * 38) is not None


def test_btc_bech32_segwit_v0_invalid_char_1():
    # '1' is not in the bech32 character set
    assert validate_btc_address("bc1q" + "1" * 38) is not None


def test_btc_bech32_segwit_v0_uppercase_prefix_ok():
    # The spec says address.lower() is applied when starts with bc1q
    upper = "BC1Q" + "a" * 38
    assert validate_btc_address(upper) is None


# ---------------------------------------------------------------------------
# BTC — Bech32m Taproot (bc1p, exactly 62 chars)
# ---------------------------------------------------------------------------

# Valid Taproot: bc1p + 58 valid bech32 chars = 62 chars
_VALID_BC1P_62 = "bc1p" + "a" * 58


def test_btc_bech32m_taproot_valid():
    assert validate_btc_address(_VALID_BC1P_62) is None


def test_btc_bech32m_taproot_wrong_length_61():
    assert validate_btc_address("bc1p" + "a" * 57) is not None


def test_btc_bech32m_taproot_wrong_length_63():
    assert validate_btc_address("bc1p" + "a" * 59) is not None


def test_btc_bech32m_taproot_mixed_case_normalized():
    # The validator lowercases bc1p addresses before checking, so mixed case is accepted
    mixed = "bc1p" + "A" * 58
    assert validate_btc_address(mixed) is None


def test_btc_bech32m_taproot_uppercase_prefix_ok():
    upper = "BC1P" + "a" * 58
    assert validate_btc_address(upper) is None


def test_btc_bech32m_taproot_invalid_char():
    assert validate_btc_address("bc1p" + "b" * 58) is not None


# ---------------------------------------------------------------------------
# BTC — Unknown prefix
# ---------------------------------------------------------------------------


def test_btc_unknown_prefix_returns_error():
    assert validate_btc_address("2abc" + "A" * 30) is not None


def test_btc_empty_string():
    assert validate_btc_address("") is not None


# ---------------------------------------------------------------------------
# BTC — Whitespace and newline stripping
# ---------------------------------------------------------------------------


def test_btc_leading_trailing_whitespace_stripped():
    assert validate_btc_address("  " + _VALID_BC1Q_42 + "  ") is None


def test_btc_newline_in_address_stripped():
    assert (
        validate_btc_address(_VALID_BC1Q_42[:20] + "\n" + _VALID_BC1Q_42[20:]) is None
    )


def test_btc_spaces_embedded_stripped():
    assert validate_btc_address(_VALID_BC1Q_42[:20] + " " + _VALID_BC1Q_42[20:]) is None


def test_btc_p2pkh_whitespace_stripped():
    assert validate_btc_address("  1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf  ") is None


# ---------------------------------------------------------------------------
# KAS — Valid addresses
# ---------------------------------------------------------------------------

# Valid KAS: "kaspa:" + exactly 61 lowercase bech32 chars
_KAS_VALID_REMAINDER = "a" * 61
_KAS_VALID = "kaspa:" + _KAS_VALID_REMAINDER


def test_kas_valid_61_char_remainder():
    assert validate_kas_address(_KAS_VALID) is None


def test_kas_valid_62_char_remainder():
    assert validate_kas_address("kaspa:" + "a" * 62) is None


def test_kas_valid_63_char_remainder():
    assert validate_kas_address("kaspa:" + "a" * 63) is None


# ---------------------------------------------------------------------------
# KAS — Invalid addresses
# ---------------------------------------------------------------------------


def test_kas_wrong_prefix():
    assert validate_kas_address("bitcoin:" + "a" * 61) is not None


def test_kas_no_prefix():
    assert validate_kas_address("a" * 61) is not None


def test_kas_remainder_too_short():
    # 59 chars — below minimum of 60
    assert validate_kas_address("kaspa:" + "a" * 59) is not None


def test_kas_remainder_60_chars_valid():
    # 60 chars — minimum valid length (real Kaspa addresses use 60-char payloads)
    assert validate_kas_address("kaspa:" + "a" * 60) is None


def test_kas_remainder_too_long():
    # 64 chars — above maximum of 63
    assert validate_kas_address("kaspa:" + "a" * 64) is not None


def test_kas_uppercase_chars_rejected():
    # KAS addresses must be lowercase bech32
    assert validate_kas_address("kaspa:" + "A" * 61) is not None


def test_kas_invalid_char_b():
    # 'b' is not in bech32 charset
    assert validate_kas_address("kaspa:" + "b" * 61) is not None


def test_kas_invalid_char_1():
    # '1' is not in bech32 charset
    assert validate_kas_address("kaspa:" + "1" * 61) is not None


def test_kas_empty_string():
    assert validate_kas_address("") is not None


# ---------------------------------------------------------------------------
# KAS — Whitespace and newline stripping
# ---------------------------------------------------------------------------


def test_kas_leading_trailing_whitespace_stripped():
    assert validate_kas_address("  " + _KAS_VALID + "  ") is None


def test_kas_newline_in_address_stripped():
    addr = "kaspa:" + "a" * 30 + "\n" + "a" * 31
    assert validate_kas_address(addr) is None


def test_kas_spaces_embedded_stripped():
    addr = "kaspa:" + "a" * 30 + " " + "a" * 31
    assert validate_kas_address(addr) is None
