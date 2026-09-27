"""Admin reviews management endpoints."""
from __future__ import annotations

from app.models.auth import User
from app.models.cms import SiteReview
from app.models.orders import OrderRating
from app.services.auth import hash_password
from tests.helpers import login_admin


def test_reviews_require_reviews_permission(api, db_session):
    login_admin(api, db_session, role="staff", perms='["products"]')
    assert api.get("/api/admin/reviews").status_code == 403


def test_reviews_list(api, db_session):
    login_admin(api, db_session)
    db_session.add(SiteReview(name="Іван", text="Дуже смачно, дякую!", rating=5, status="approved"))
    db_session.commit()
    data = api.get("/api/admin/reviews").json()
    assert data["reviews"][0]["author"] == "Іван"
    assert data["reviews"][0]["text"] == "Дуже смачно, дякую!"
    assert data["avg_rating"] == 5.0
    assert data["rating_dist"][0] == {"stars": 5, "count": 1}


def test_reviews_filter_by_rating_and_status(api, db_session):
    login_admin(api, db_session)
    db_session.add(SiteReview(name="Оксана Топ", text="ReviewFiveText", rating=5, status="approved"))
    db_session.add(SiteReview(name="Марко Другий", text="ReviewTwoText", rating=2, status="pending"))
    db_session.commit()
    texts = lambda url: [r["text"] for r in api.get(url).json()["reviews"]]  # noqa: E731
    assert texts("/api/admin/reviews?rating=5") == ["ReviewFiveText"]
    assert texts("/api/admin/reviews?status=pending") == ["ReviewTwoText"]


def test_order_ratings(api, db_session):
    login_admin(api, db_session)
    user = User(login="u1", email="u1@example.com", password=hash_password("x"), client_name="Петро", client_surname="Іваненко")
    db_session.add(user)
    db_session.flush()
    db_session.add(OrderRating(order_id=42, user_id=user.client_id, rating=4))
    db_session.commit()
    data = api.get("/api/admin/reviews/order-ratings").json()
    assert data["order_ratings"][0]["order_id"] == 42
    assert data["order_ratings"][0]["uname"] == "Петро Іваненко"
    assert data["avg"] == 4.0


def test_review_approve(api, db_session):
    login_admin(api, db_session)
    review = SiteReview(name="X", text="text", rating=3, status="pending")
    db_session.add(review)
    db_session.commit()
    assert api.patch(f"/api/admin/reviews/{review.id}", json={"status": "approved"}).json()["success"] is True
    db_session.expire_all()
    assert db_session.get(SiteReview, review.id).status.value == "approved"


def test_review_decline(api, db_session):
    login_admin(api, db_session)
    review = SiteReview(name="X", text="text", rating=3, status="approved")
    db_session.add(review)
    db_session.commit()
    api.patch(f"/api/admin/reviews/{review.id}", json={"status": "declined"})
    db_session.expire_all()
    assert db_session.get(SiteReview, review.id).status.value == "declined"


def test_review_delete(api, db_session):
    login_admin(api, db_session)
    review = SiteReview(name="X", text="text", rating=3, status="approved")
    db_session.add(review)
    db_session.commit()
    review_id = review.id
    assert api.delete(f"/api/admin/reviews/{review_id}").json()["success"] is True
    assert db_session.get(SiteReview, review_id) is None


def test_review_action_requires_reviews_permission(api, db_session):
    login_admin(api, db_session, role="staff", perms='["products"]')
    assert api.delete("/api/admin/reviews/1").status_code == 403


def test_review_rejects_unknown_status(api, db_session):
    login_admin(api, db_session)
    review = SiteReview(name="X", text="text", rating=3, status="approved")
    db_session.add(review)
    db_session.commit()
    assert api.patch(f"/api/admin/reviews/{review.id}", json={"status": "bogus"}).status_code == 422
