PASSWORD = "password123"

ADMIN, BU, DH, PM1, PM2, EMP1, EMP2, ADMIN2 = 1, 2, 3, 4, 5, 6, 7, 8
SMALL, BIG, SMALL2, PM2_REQ, SELF_REQ = 1, 2, 3, 4, 5


def login(client, email):
    r = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def view_as(client, admin_headers, target_id):
    r = client.post("/impersonation/view-as", json={"target_id": target_id},
                    headers=admin_headers)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def make_grant(client, max_amount=50000, hours=24):
    """pm1 delegates expense approval to pm2."""
    r = client.post(
        "/delegations",
        json={"grantee_id": PM2, "scopes": ["expense_approval"],
              "max_amount": max_amount, "expires_in_hours": hours},
        headers=login(client, "pm1@demo.com"),
    )
    assert r.status_code == 200, r.text
    return r.json()