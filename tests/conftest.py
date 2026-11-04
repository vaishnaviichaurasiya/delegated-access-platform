import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User, Project, ApprovalRequest
from app.security import hash_password
from tests.helpers import PASSWORD

PASSWORD_HASH = hash_password(PASSWORD)  # hash once, reuse for every test user


def seed_basic(factory):
    db = factory()

    def user(id_, name, email, role, manager_id=None):
        db.add(User(id=id_, name=name, email=email, password_hash=PASSWORD_HASH,
                    role=role, manager_id=manager_id))

    user(1, "Asha Admin", "admin@demo.com", "admin")
    user(2, "Bala BU", "bu1@demo.com", "bu_head")
    user(3, "Dev Delivery", "dh1@demo.com", "delivery_head", 2)
    user(4, "Priya PM", "pm1@demo.com", "project_manager", 3)
    user(5, "Rahul PM", "pm2@demo.com", "project_manager", 3)
    user(6, "Esha Emp", "emp1@demo.com", "employee", 4)
    user(7, "Farhan Emp", "emp2@demo.com", "employee", 5)
    user(8, "Zoya Admin", "admin2@demo.com", "admin")
    db.flush()

    db.add(Project(id=1, name="Project One", bu_head_id=2, delivery_head_id=3, pm_id=4))
    db.add(Project(id=2, name="Project Two", bu_head_id=2, delivery_head_id=3, pm_id=5))
    db.flush()

    def request(id_, amount, requester, approver, project):
        db.add(ApprovalRequest(id=id_, type="expense", amount=amount, status="pending",
                               requester_id=requester, approver_id=approver,
                               project_id=project))

    request(1, 25000, 6, 4, 1)   # SMALL
    request(2, 80000, 6, 4, 1)   # BIG
    request(3, 10000, 6, 4, 1)   # SMALL2
    request(4, 5000, 7, 5, 2)    # PM2_REQ
    request(5, 1000, 4, 4, 1)    # SELF_REQ (pm1 raised it and is its approver)
    db.commit()
    db.close()


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    seed_basic(factory)
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
