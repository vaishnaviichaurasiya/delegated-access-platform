from app.models import AuditLog
from tests.helpers import ADMIN, BIG, PM1, PM2, SMALL, login, make_grant, view_as


def logs(session_factory, **filters):
    with session_factory() as db:
        return db.query(AuditLog).filter_by(**filters).all()


def test_on_behalf_approval_is_audited(client, session_factory):
    make_grant(client)
    client.post(f"/approvals/{SMALL}/approve", headers=login(client, "pm2@demo.com"))
    rows = logs(session_factory, action="approve_on_behalf", result="success")
    assert len(rows) == 1
    assert rows[0].actor_id == PM2
    assert f"for user:{PM1}" in rows[0].resource


def test_denied_attempt_is_audited(client, session_factory):
    client.post(f"/approvals/{SMALL}/approve", headers=login(client, "pm2@demo.com"))
    rows = logs(session_factory, action="approve_on_behalf", result="denied")
    assert len(rows) == 1
    assert rows[0].actor_id == PM2


def test_view_as_start_records_actor_and_target(client, session_factory):
    view_as(client, login(client, "admin@demo.com"), PM1)
    rows = logs(session_factory, action="view_as_start", result="success")
    assert len(rows) == 1
    assert rows[0].actor_id == ADMIN
    assert rows[0].effective_user_id == PM1


def test_blocked_write_in_view_as_is_audited(client, session_factory):
    headers = view_as(client, login(client, "admin@demo.com"), PM1)
    client.post(f"/approvals/{BIG}/approve", headers=headers)
    rows = logs(session_factory, action="write_blocked_in_view_as")
    assert len(rows) == 1
    assert rows[0].actor_id == ADMIN
    assert rows[0].effective_user_id == PM1
    assert rows[0].result == "denied"


def test_non_admin_cannot_read_audit_logs(client):
    r = client.get("/audit-logs", headers=login(client, "pm1@demo.com"))
    assert r.status_code == 403


def test_admin_can_read_audit_logs(client):
    make_grant(client)
    r = client.get("/audit-logs", headers=login(client, "admin@demo.com"))
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_audit_log_is_append_only(client):
    headers = login(client, "admin@demo.com")
    assert client.delete("/audit-logs", headers=headers).status_code == 405
    assert client.put("/audit-logs", headers=headers).status_code == 405
    assert client.patch("/audit-logs", headers=headers).status_code == 405