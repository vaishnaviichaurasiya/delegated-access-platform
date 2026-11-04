from tests.helpers import PASSWORD, login


def test_login_success_returns_token(client):
    r = client.post("/auth/login", json={"email": "pm1@demo.com", "password": PASSWORD})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"


def test_login_wrong_password_is_rejected(client):
    r = client.post("/auth/login", json={"email": "pm1@demo.com", "password": "wrong"})
    assert r.status_code == 401


def test_request_without_token_is_rejected(client):
    r = client.get("/dashboard")
    assert r.status_code in (401, 403)


def test_tampered_token_is_rejected(client):
    r = client.get("/dashboard", headers={"Authorization": "Bearer abc.def.ghi"})
    assert r.status_code == 401


def test_me_returns_logged_in_user(client):
    r = client.get("/auth/me", headers=login(client, "pm1@demo.com"))
    assert r.status_code == 200
    assert r.json()["role"] == "project_manager"
    assert r.json()["impersonating"] is False
