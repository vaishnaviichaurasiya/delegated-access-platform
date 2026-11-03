# Delegated Access & Impersonation Platform (Prototype)

A backend prototype showing how an enterprise can let authorised users **view the system as another person (read-only)** and **approve requests on someone's behalf within strict limits**, with a full audit trail.

> **Prototype:** built to demonstrate access-control design, not production-ready security.

## Features

- **Role-based views:** Admin, BU Head, Delivery Head, Project Manager and Employee each see only the data in their scope.
- **View-As (read-only impersonation):** an Admin sees exactly what another user sees. All writes are blocked.
- **Scoped delegation:** a head can let someone approve on their behalf, limited by request type, amount and expiry. It can be revoked instantly.
- **Audit trail:** every sensitive action and every denied attempt is logged with both the real actor and the effective user.
- **Pagination and indexed queries** for large datasets.

## Tech stack

Python, FastAPI, SQLAlchemy, SQLite, JWT (PyJWT), bcrypt, Pytest, pytest-cov, Faker

## Architecture

```
Client
  │  Authorization: Bearer <JWT>
  ▼
FastAPI routers  (auth, dashboard, approvals, impersonation, delegations, audit-logs)
  │
  ├─ deps.py        → decodes the token, finds the ACTOR and the EFFECTIVE user,
  │                   validates the impersonation session, blocks writes in View-As
  ├─ scope.py       → role-based query scoping (one place for visibility rules)
  ├─ delegation.py  → one function that decides if a delegated approval is allowed
  └─ audit.py       → writes success and denied events
  ▼
SQLAlchemy models → SQLite
```

**Token design:** a normal token holds `sub` (the user). A View-As token also holds `act_as` (the target), `mode` and `sid` (a session id). The session is checked in the database on every request, so ending a session invalidates its token immediately.

**Actor vs effective user:** the *actor* is who really made the request. The *effective user* is whose view and permissions are used. Both are always recorded in the audit log.

## Who sees what

| Role | Approval requests visible |
|---|---|
| Admin | All |
| BU Head | Projects in their business unit |
| Delivery Head | Projects they deliver |
| Project Manager | Their own projects |
| Employee | Only requests they raised |

## Security rules and threat model

| Threat | Mitigation |
|---|---|
| A normal user impersonates someone | Only Admins can start View-As |
| Impersonating an Admin or yourself | Blocked (403 / 400) |
| Chained impersonation (A views as B, then B views as C) | Blocked |
| Writing data while impersonating | All POST/PUT/PATCH/DELETE return 403 during View-As |
| Using an old impersonation token | Session is checked in the DB on every request, with a 30-minute expiry. `/impersonation/end` kills it immediately |
| Over-broad delegation | Delegation is limited by scope, maximum amount and expiry (max 7 days) |
| Delegating to an Admin or to yourself | Blocked |
| Approving beyond your grant | Amount, scope, expiry and revoked state are checked on every approval |
| Self-approval | Blocked |
| Delegation used in the wrong direction | A grant works only from grantor to grantee |
| Tampering with the audit log | No update or delete endpoints exist (append-only by design) |
| Unauthenticated access | Invalid or missing tokens return 401 |
| Plain-text passwords | Passwords are stored as bcrypt hashes |

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/login` | Log in and get a JWT |
| GET | `/auth/me` | Current effective user and actor |
| GET | `/dashboard` | Summary for the effective user |
| GET | `/approvals` | Scoped, paginated approval requests |
| POST | `/approvals/{id}/approve` | Approve directly or on behalf of someone |
| POST | `/impersonation/view-as` | Start a read-only View-As session (Admin only) |
| POST | `/impersonation/end` | End the session |
| POST | `/delegations` | Create a scoped delegation grant |
| GET | `/delegations` | Grants given and received |
| DELETE | `/delegations/{id}` | Revoke a grant (grantor only) |
| GET | `/audit-logs` | View the audit trail (Admin only) |

Interactive docs are available at `/docs` when the server is running.

## Run locally

```bash
git clone https://github.com/vaishnaviichaurasiya/delegated-access-platform.git
cd delegated-access-platform
python -m venv venv
venv\Scripts\activate        # Windows (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
python -m app.seed           # creates demo data (1 admin, 2 BU heads, 4 delivery heads, 8 PMs, 120 employees, 240 requests)
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs

**Demo logins** (password for all: `password123`)

| Email | Role |
|---|---|
| admin@demo.com | Admin |
| bu1@demo.com | BU Head |
| dh11@demo.com | Delivery Head |
| pm111@demo.com | Project Manager |
| pm112@demo.com | Project Manager (use as a delegate) |
| emp1@demo.com | Employee |

## Demo walkthrough

1. Log in as `pm111@demo.com`, then `POST /delegations` with `{"grantee_id": 20, "max_amount": 50000}`.
2. Log in as `pm112@demo.com` and approve a request of 50,000 or less. The response says "Approved by ... on behalf of ...".
3. Try approving a larger request. It returns 403 (amount above the limit).
4. Log in as `admin@demo.com`, call `POST /impersonation/view-as` with `{"target_id": 4}`, then use the new token. `/dashboard` now shows the Project Manager's data.
5. While in View-As, try to approve. It returns 403 (read-only).
6. As Admin, open `GET /audit-logs` to see every action with actor and effective user.


## Testing

```bash
pytest -v
pytest --cov=app --cov-report=term-missing
```

**45 tests** with **[87]% coverage**, using an isolated in-memory database for each test. They cover:

- Authentication and token handling
- Role-based scoping, including cross-project isolation
- Delegation: no grant, over limit, expired, revoked, wrong direction, double approval, self-approval
- Impersonation: admin-only, chained, self, read-only enforcement, session end and expiry
- Audit logging of both successful and denied actions

## Design decisions

- **Rules in one place:** `scope.py` for visibility and `delegation.py` for delegation make the rules easy to test and change.
- **Session stored server-side:** lets View-As be revoked immediately, which a pure stateless JWT cannot do.
- **Deny and log:** blocked attempts are written to the audit log, not just successful actions.
- **Revoke, don't delete:** grants are marked revoked so history is preserved.

## Limitations and future work

- SQLite for simplicity, with PostgreSQL planned for production.
- Single approval type (expense). The scope model supports adding more.
- Production would add SSO and MFA, an approval step for starting impersonation, rate limiting, and anomaly detection on impersonation use.
- Demo secret key and shared demo password are for local use only.

## Author

**Vaishnavi Chaurasiya** · [LinkedIn](https://www.linkedin.com/in/vaishnavi-chaurasiya-19917024a)