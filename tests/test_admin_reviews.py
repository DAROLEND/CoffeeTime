"""Phase 8 (5/n) verification: admin/admin_reviews.php port. No permission
fix needed here — PHP already had require_perm('reviews').

Confirmed fix applied: the dead `delete_id` POST branch (unreachable from
any form/script — grepped) that ran a duplicate DELETE statement is not
ported at all; only the one reachable AJAX delete path is kept."""
from __future__ import annotations

import re

from app.models.auth import AdminUser, User
from app.models.cms import SiteReview
from app.models.orders import OrderRating
from app.services.auth import hash_password


def _login_admin(client, db_session, username="boss", role="super", perms="[]"):
    admin = AdminUser(username=username, password=hash_password("adminpass1"), role=role, permissions=perms)
    db_session.add(admin)
    db_session.commit()
    resp = client.get("/login")
    token = re.search(r'name="csrf_token" value="([a-f0-9]+)"', resp.text).group(1)
    client.post("/login", data={"csrf_token": token, "email": username, "password": "adminpass1"}, follow_redirects=False)
    return admin


def test_reviews_requires_reviews_permission(client, db_session):
    _login_admin(client, db_session, role="staff", perms='["products"]')
    resp = client.get("/admin/reviews", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/dashboard"


def test_reviews_default_tab_lists_site_reviews(client, db_session):
    _login_admin(client, db_session)
    db_session.add(SiteReview(name="Іван", text="Дуже смачно, дякую!", rating=5, status="approved"))
    db_session.commit()

    resp = client.get("/admin/reviews")
    assert resp.status_code == 200
    assert "Іван" in resp.text
    assert "Дуже смачно" in resp.text


def test_reviews_filter_by_rating_and_status(client, db_session):
    _login_admin(client, db_session)
    db_session.add(SiteReview(name="Оксана Топ", text="ReviewFiveText", rating=5, status="approved"))
    db_session.add(SiteReview(name="Марко Другий", text="ReviewTwoText", rating=2, status="pending"))
    db_session.commit()

    resp = client.get("/admin/reviews?rating=5")
    assert "ReviewFiveText" in resp.text and "ReviewTwoText" not in resp.text

    resp = client.get("/admin/reviews?status=pending")
    assert "ReviewTwoText" in resp.text and "ReviewFiveText" not in resp.text


def test_reviews_order_ratings_tab(client, db_session):
    _login_admin(client, db_session)
    user = User(login="u1", email="u1@example.com", password=hash_password("x"), client_name="Петро", client_surname="Іваненко")
    db_session.add(user)
    db_session.flush()
    db_session.add(OrderRating(order_id=42, user_id=user.client_id, rating=4))
    db_session.commit()

    resp = client.get("/admin/reviews?tab=order_ratings")
    assert resp.status_code == 200
    assert "#42" in resp.text
    assert "Петро" in resp.text


def test_review_approve(client, db_session):
    _login_admin(client, db_session)
    review = SiteReview(name="X", text="text", rating=3, status="pending")
    db_session.add(review)
    db_session.commit()
    review_id = review.id

    resp = client.post("/admin/reviews", headers={"X-Requested-With": "XMLHttpRequest"}, data={"action": "approved", "id": review_id})
    assert resp.json() == {"success": True}
    db_session.expire_all()
    assert db_session.get(SiteReview, review_id).status.value == "approved"


def test_review_decline(client, db_session):
    _login_admin(client, db_session)
    review = SiteReview(name="X", text="text", rating=3, status="approved")
    db_session.add(review)
    db_session.commit()
    review_id = review.id

    client.post("/admin/reviews", headers={"X-Requested-With": "XMLHttpRequest"}, data={"action": "declined", "id": review_id})
    db_session.expire_all()
    assert db_session.get(SiteReview, review_id).status.value == "declined"


def test_review_delete(client, db_session):
    _login_admin(client, db_session)
    review = SiteReview(name="X", text="text", rating=3, status="approved")
    db_session.add(review)
    db_session.commit()
    review_id = review.id

    resp = client.post("/admin/reviews", headers={"X-Requested-With": "XMLHttpRequest"}, data={"action": "delete", "id": review_id})
    assert resp.json() == {"success": True}
    assert db_session.get(SiteReview, review_id) is None


def test_review_action_requires_reviews_permission(client, db_session):
    _login_admin(client, db_session, role="staff", perms='["products"]')
    resp = client.post(
        "/admin/reviews", headers={"X-Requested-With": "XMLHttpRequest"},
        data={"action": "delete", "id": 1}, follow_redirects=False,
    )
    assert resp.status_code == 303


def test_review_action_rejects_unknown_action(client, db_session):
    _login_admin(client, db_session)
    review = SiteReview(name="X", text="text", rating=3, status="approved")
    db_session.add(review)
    db_session.commit()
    resp = client.post("/admin/reviews", headers={"X-Requested-With": "XMLHttpRequest"}, data={"action": "bogus", "id": review.id})
    assert resp.json() == {"success": False}
