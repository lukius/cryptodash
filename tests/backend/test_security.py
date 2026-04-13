from backend.core.security import generate_token, hash_password, verify_password


def test_hash_password_differs_from_plaintext():
    h = hash_password("mysecret")
    assert h != "mysecret"


def test_hash_password_bcrypt_prefix():
    h = hash_password("anypassword")
    assert h.startswith("$2b$12$")


def test_verify_password_correct():
    h = hash_password("correct")
    assert verify_password("correct", h) is True


def test_verify_password_wrong():
    h = hash_password("correct")
    assert verify_password("wrong", h) is False


def test_generate_token_unique():
    t1 = generate_token()
    t2 = generate_token()
    assert t1 != t2


def test_generate_token_length():
    # secrets.token_urlsafe(32) produces 43 characters (32 bytes base64url-encoded)
    t = generate_token()
    assert isinstance(t, str)
    assert len(t) == 43
