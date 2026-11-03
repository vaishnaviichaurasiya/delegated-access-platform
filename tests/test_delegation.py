from datetime import timedelta

from app.delegation import find_valid_grant
from app.models import ApprovalRequest, DelegationGrant, User, utcnow
from tests.helpers import (ADMIN, BIG, EMP1, PM1, PM2, PM2_REQ, SELF_REQ, SMALL,
                           SMALL2, login, make_grant)


def approve(client, who, request_id):
    return client.post(f"/approvals/{request_id}/approve", headers=login(client, who))


def test_approve_without_grant_is_denied(client):
    r = approve(client, "pm2@demo.com", SMALL)
    assert r.status_code == 403
    assert "No delegation" in r.json()["detail"]


def test_approve_within_limit_succeeds_and_records_on_behalf(client, session_factory):
    make_grant(client, max_amount=50000)
    r = approve(client, "pm2@demo.com", SMALL)
    assert r.status_code == 200
    assert "on behalf of" in r.json()["message"]
    with session_factory() as db:
        req = db.get(ApprovalRequest, SMALL)
        assert req.status == "approved"
        assert req.decided_by_id == PM2
        assert req.on_behalf_of_id == PM1


def test_amount_above_limit_is_denied(client):
    make_grant(client, max_amount=50000)
    r = approve(client, "pm2@demo.com", BIG)
    assert r.status_code == 403
    assert "exceeds" in r.json()["detail"]


def test_revoked_grant_is_denied(client):
    grant = make_grant(client)
    r = client.delete(f"/delegations/{grant['id']}", headers=login(client, "pm1@demo.com"))
    assert r.status_code == 200
    r = approve(client, "pm2@demo.com", SMALL)
    assert r.status_code == 403
    assert "revoked" in r.json()["detail"]


def test_expired_grant_is_denied(client, session_factory):
    grant = make_grant(client)
    with session_factory() as db:
        db.get(DelegationGrant, grant["id"]).expires_at = utcnow() - timedelta(hours=1)
        db.commit()
    r = approve(client, "pm2@demo.com", SMALL)
    assert r.status_code == 403
    assert "expired" in r.json()["detail"]


def test_double_approval_is_blocked(client):
    make_grant(client)
    assert approve(client, "pm2@demo.com", SMALL).status_code == 200
    r = approve(client, "pm2@demo.com", SMALL)
    assert r.status_code == 409


def test_cannot_approve_own_request(client):
    r = approve(client, "pm1@demo.com", SELF_REQ)
    assert r.status_code == 403
    assert "own request" in r.json()["detail"]


def test_grant_is_directional(client):
    make_grant(client)  # pm1 -> pm2 only
    r = approve(client, "pm1@demo.com", PM2_REQ)  # pm2's request, pm1 tries to approve
    assert r.status_code == 403


def test_only_grantor_can_revoke(client):
    grant = make_grant(client)
    r = client.delete(f"/delegations/{grant['id']}", headers=login(client, "pm2@demo.com"))
    assert r.status_code == 403


def test_employee_cannot_create_grant(client):
    r = client.post("/delegations",
                    json={"grantee_id": PM2, "max_amount": 1000},
                    headers=login(client, "emp1@demo.com"))
    assert r.status_code == 403


def test_cannot_delegate_to_self(client):
    r = client.post("/delegations",
                    json={"grantee_id": PM1, "max_amount": 1000},
                    headers=login(client, "pm1@demo.com"))
    assert r.status_code == 400


def test_invalid_scope_is_rejected(client):
    r = client.post("/delegations",
                    json={"grantee_id": PM2, "scopes": ["delete_everything"], "max_amount": 1000},
                    headers=login(client, "pm1@demo.com"))
    assert r.status_code == 400


def test_cannot_delegate_to_admin(client):
    r = client.post("/delegations",
                    json={"grantee_id": ADMIN, "max_amount": 1000},
                    headers=login(client, "pm1@demo.com"))
    assert r.status_code == 403


def test_approve_unknown_request_returns_404(client):
    assert approve(client, "pm1@demo.com", 9999).status_code == 404


def test_grant_expiry_cannot_exceed_seven_days(client):
    r = client.post("/delegations",
                    json={"grantee_id": PM2, "max_amount": 1000, "expires_in_hours": 500},
                    headers=login(client, "pm1@demo.com"))
    assert r.status_code == 422


def test_find_valid_grant_rule_directly(session_factory):
    """Unit test of the rule function, with no HTTP involved."""
    with session_factory() as db:
        db.add(DelegationGrant(grantor_id=PM1, grantee_id=PM2, scopes="expense_approval",
                               max_amount=20000, expires_at=utcnow() + timedelta(hours=1)))
        db.commit()
        pm2 = db.get(User, PM2)
        ok, _ = find_valid_grant(db, pm2, db.get(ApprovalRequest, SMALL2))   # 10000
        too_big, reason = find_valid_grant(db, pm2, db.get(ApprovalRequest, SMALL))  # 25000
        assert ok is not None
        assert too_big is None and "exceeds" in reason