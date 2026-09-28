"""
bcrypt hashes come in several variants (`$2a$`, `$2b$`, `$2y$`); every one
of them must verify, whichever library produced the stored hash.

The `$2y$` hashes below were generated for this test from a known
password, so it can check both a correct and a wrong password.
"""
from app.services.auth import is_bcrypt_hash, verify_password

PASSWORD = "coffee-time-test"

HASHES_2Y = [
    "$2y$10$D5phHJR3W.7Yx99L0vzFXOTtrT7.6iTVmi3jXMGMjiFR9sQa.unfy",
    "$2y$12$D6rcBECh82H9.0INgJGQyuJEE9vlkcOMjIXDvjKxbBZ2XEV/BnOOK",
]


def test_passlib_identifies_2y_bcrypt_hashes():
    for hashed in HASHES_2Y:
        assert is_bcrypt_hash(hashed), f"passlib did not recognize {hashed!r} as bcrypt"


def test_2y_hashes_verify_the_right_password():
    for hashed in HASHES_2Y:
        assert verify_password(PASSWORD, hashed) is True


def test_verify_wrong_password_returns_false_not_exception():
    for hashed in HASHES_2Y:
        assert verify_password("definitely-not-the-real-password", hashed) is False


def test_new_hash_round_trips():
    from app.services.auth import hash_password

    hashed = hash_password("a-fresh-password-123")
    assert is_bcrypt_hash(hashed)
    assert verify_password("a-fresh-password-123", hashed) is True
    assert verify_password("wrong", hashed) is False
