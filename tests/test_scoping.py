from tests.helpers import login


def total(client, email):
    r = client.get("/approvals?page_size=100", headers=login(client, email))
    assert r.status_code == 200
    return r.json()["total"], r.json()["items"]


def test_employee_sees_only_own_requests(client):
    count, items = total(client, "emp1@demo.com")
    assert count == 3
    assert {i["requester"] for i in items} == {"Esha Emp"}


def test_pm_sees_only_own_project(client):
    count, items = total(client, "pm1@demo.com")
    assert count == 4
    assert {i["project"] for i in items} == {"Project One"}


def test_other_pm_cannot_see_first_pms_requests(client):
    count, items = total(client, "pm2@demo.com")
    assert count == 1
    assert items[0]["project"] == "Project Two"


def test_bu_head_sees_all_projects_in_unit(client):
    assert total(client, "bu1@demo.com")[0] == 5


def test_admin_sees_everything(client):
    assert total(client, "admin@demo.com")[0] == 5


def test_dashboard_numbers_for_pm(client):
    r = client.get("/dashboard", headers=login(client, "pm1@demo.com"))
    body = r.json()
    assert body["projects"] == 1
    assert body["team_size"] == 1
    assert body["total_requests"] == 4
