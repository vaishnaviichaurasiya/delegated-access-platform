import random
from faker import Faker
from app.database import Base, engine, SessionLocal
from app.models import User, Project, ApprovalRequest
from app.security import hash_password


def seed():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    fake = Faker()
    pw = hash_password("password123")  # same demo password for all users
    counter = {"emp": 0}

    def add_user(name, email, role, manager=None):
        u = User(name=name, email=email, password_hash=pw, role=role,
                 manager_id=manager.id if manager else None)
        db.add(u)
        db.flush()
        return u

    add_user("Asha Admin", "admin@demo.com", "admin")

    for b in range(1, 3):
        bu = add_user(fake.name(), f"bu{b}@demo.com", "bu_head")
        for d in range(1, 3):
            dh = add_user(fake.name(), f"dh{b}{d}@demo.com", "delivery_head", bu)
            for p in range(1, 3):
                pm = add_user(fake.name(), f"pm{b}{d}{p}@demo.com", "project_manager", dh)
                project = Project(name=fake.bs().title(), bu_head_id=bu.id,
                                  delivery_head_id=dh.id, pm_id=pm.id)
                db.add(project)
                db.flush()
                for _ in range(15):
                    counter["emp"] += 1
                    emp = add_user(fake.name(), f"emp{counter['emp']}@demo.com", "employee", pm)
                    for _ in range(2):
                        db.add(ApprovalRequest(
                            type="expense",
                            amount=random.choice([2000, 8000, 25000, 45000, 80000, 120000]),
                            requester_id=emp.id, approver_id=pm.id, project_id=project.id))
    db.commit()
    db.close()
    print("Seeded: 1 admin, 2 BU heads, 4 delivery heads, 8 PMs, 120 employees, 240 requests")


if __name__ == "__main__":
    seed()
