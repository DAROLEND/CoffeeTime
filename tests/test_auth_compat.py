"""
Phase 1 verification step from the migration plan: prove passlib's bcrypt
backend accepts real hashes produced by PHP's `password_hash($pw,
PASSWORD_DEFAULT)` (which yields `$2y$` hashes), so existing users' and
admins' passwords keep working without any rehash/migration step.

Hashes below are copied verbatim from CoffeeTime.sql's `users` and
`admin_users` INSERT statements — real bcrypt output, not fabricated. We
don't have the corresponding plaintexts (nor should we — they're real
account passwords), so this test proves two things without ever knowing a
real plaintext:
  1. passlib recognizes the `$2y$` hash format as bcrypt (doesn't raise,
     doesn't say "unknown scheme").
  2. Verifying an obviously-wrong password against it returns False, not
     an exception — matching PHP's password_verify() behavior exactly.
A real "log in with your actual existing password" click-through against
a live copy of the DB is still the authoritative check (see the plan's
Phase 4 verification step); this test only rules out a hash-format
incompatibility before any code depending on it is written.
"""
from app.services.auth import is_bcrypt_hash, verify_password

REAL_HASHES_FROM_DUMP = [
    # users.password (client_id=3, 4, 5) — $2y$10$...
    "$2y$10$AoiNmgD97PcXMiRpRpVJzuw6T4Bd9XHzWP7YJDnfBQlrwDOhWrSEK",
    "$2y$10$hGu9mRrpTwInzMwgMAESSOzyRPL5sSKYLMY/m7YoHYSuNFx7FGicy",
    # users.password (client_id=6) — $2y$12$...
    "$2y$12$PfhF9VyB.HEkc4M.UtJudeIzB4HZ2DE69YLJZ054SNv1ZW1EOwHRi",
    # admin_users.password (id=1, super admin) — $2y$12$...
    "$2y$12$f6ZuyZrN66JlTlKLazIXPet9G8rq9y/TTo2Mco8tD5/FHKEfyEyEK",
]


def test_passlib_identifies_php_bcrypt_hashes():
    for hashed in REAL_HASHES_FROM_DUMP:
        assert is_bcrypt_hash(hashed), f"passlib did not recognize {hashed!r} as bcrypt"


def test_verify_wrong_password_returns_false_not_exception():
    for hashed in REAL_HASHES_FROM_DUMP:
        assert verify_password("definitely-not-the-real-password", hashed) is False


def test_new_hash_round_trips():
    from app.services.auth import hash_password

    hashed = hash_password("a-fresh-password-123")
    assert is_bcrypt_hash(hashed)
    assert verify_password("a-fresh-password-123", hashed) is True
    assert verify_password("wrong", hashed) is False
