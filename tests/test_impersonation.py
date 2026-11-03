from datetime import timedelta

from app.models import ImpersonationSession, utcnow
from tests.helpers import ADMIN, ADMIN2, BIG, PM1, login, view_as


def admin(client):
    return login(client, "admin@demo.com")


def test_view_as_shows_target_users_data(client):
    headers = view_as(client, admin(client), PM1)
    me = client.get("/auth/me", headers=headers).json()
    assert me["role"] == "project_manager"
    assert me["impersonating"] is True
    assert me["actor"]["role"] == "admin"
    dash = client.get("/dashboard", headers=headers).json()
    assert dash["total_requests"] == 4          # pm1's view, not the admin's 5


def test_non_admin_cannot_use_view_as(client):
    r = client.post("/impersonation/view-as", json={"target_id": 5},
                    headers=login(client, "pm1@demo.com"))
    assert r.status_code == 403


def test_cannot_view_as_yourself(client):
    r = client.post("/impersonation/view-as", json={"target_id": ADMIN}, headers=admin(client))
    assert r.status_code == 400


def test_cannot_impersonate_another_admin(client):
    r = client.post("/impersonation/view-as", json={"target_id": ADMIN2}, headers=admin(client))
    assert r.status_code == 403


def test_unknown_target_returns_404(client):
    r = client.post("/impersonation/view-as", json={"target_id": 9999}, headers=admin(client))
    assert r.status_code == 404


def test_chained_impersonation_is_blocked(client):
    headers = view_as(client, admin(client), PM1)
    r = client.post("/impersonation/view-as", json={"target_id": 5}, headers=headers)
    assert r.status_code == 403
    assert "Chained" in r.json()["detail"]


def test_view_as_blocks_approving(client):
    headers = view_as(client, admin(client), PM1)
    r = client.post(f"/approvals/{BIG}/approve", headers=headers)
    assert r.status_code == 403
    assert "read-only" in r.json()["detail"]


def test_view_as_blocks_creating_grants(client):
    headers = view_as(client, admin(client), PM1)
    r = client.post("/delegations", json={"grantee_id": 5, "max_amount": 1000}, headers=headers)
    assert r.status_code == 403


def test_ending_session_invalidates_token(client):
    headers = view_as(client, admin(client), PM1)
    assert client.post("/impersonation/end", headers=headers).status_code == 200
    assert client.get("/dashboard", headers=headers).status_code == 401


def test_expired_session_is_rejected(client, session_factory):
    headers = view_as(client, admin(client), PM1)
    with session_factory() as db:
        for s in db.query(ImpersonationSession).all():
            s.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()
    assert client.get("/dashboard", headers=headers).status_code == 401


def test_end_without_session_is_rejected(client):
    r = client.post("/impersonation/end", headers=admin(client))
    assert r.status_code == 400