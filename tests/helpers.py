"""Test helpers for driving the JSON API like the SPA does: fetch a CSRF
token once, send it in X-CSRF-Token on every mutating request, and
refetch it after the session is reset (logout, expiry)."""
from __future__ import annotations

from starlette.testclient import TestClient

from app.models.auth import AdminUser, User
from app.services.auth import hash_password


class Api:
    def __init__(self, client: TestClient):
        self.client = client
        self._token: str | None = None

    def token(self, refresh: bool = False) -> str:
        if refresh or not self._token:
            self._token = self.client.get("/api/csrf-token").json()["csrf_token"]
        return self._token

    def get(self, url: str, **kw):
        return self.client.get(url, **kw)

    def _send(self, method: str, url: str, **kw):
        headers = dict(kw.pop("headers", None) or {})
        headers["X-CSRF-Token"] = self.token()
        resp = self.client.request(method, url, headers=headers, **kw)
        if resp.status_code == 403 and resp.json().get("code") == "csrf_expired":
            headers["X-CSRF-Token"] = self.token(refresh=True)
            resp = self.client.request(method, url, headers=headers, **kw)
        return resp

    def post(self, url: str, **kw):
        return self._send("POST", url, **kw)

    def patch(self, url: str, **kw):
        return self._send("PATCH", url, **kw)

    def put(self, url: str, **kw):
        return self._send("PUT", url, **kw)

    def delete(self, url: str, **kw):
        return self._send("DELETE", url, **kw)


def login_user(api: Api, db_session, login: str = "alice", password: str = "pass1234", **fields) -> User:
    user = User(login=login, email=f"{login}@example.com", password=hash_password(password), **fields)
    db_session.add(user)
    db_session.commit()
    resp = api.post("/api/auth/login", json={"login": login, "password": password})
    assert resp.status_code == 200, resp.text
    return user


def login_admin(api: Api, db_session, username: str = "boss", role: str = "super", perms: str = "[]") -> AdminUser:
    admin = AdminUser(username=username, password=hash_password("adminpass1"), role=role, permissions=perms)
    db_session.add(admin)
    db_session.commit()
    resp = api.post("/api/auth/login", json={"login": username, "password": "adminpass1"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["kind"] == "admin"
    return admin
