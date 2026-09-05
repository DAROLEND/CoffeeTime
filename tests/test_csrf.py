"""Unit tests for the CSRF token helpers (the synchronous half of
app/services/csrf.py — verify_csrf() itself needs a real Request/session
and is covered by router-level tests once routes exist in later phases)."""
from app.middleware.session import SessionData
from app.services.csrf import CSRF_SESSION_KEY, csrf_field, csrf_token


def test_csrf_token_is_generated_once_and_cached():
    session = SessionData({})
    token1 = csrf_token(session)
    token2 = csrf_token(session)
    assert token1 == token2
    assert session[CSRF_SESSION_KEY] == token1
    assert len(token1) == 64  # secrets.token_hex(32)


def test_csrf_field_embeds_the_token():
    session = SessionData({})
    html = csrf_field(session)
    token = session[CSRF_SESSION_KEY]
    assert f'value="{token}"' in html
    assert 'name="csrf_token"' in html
