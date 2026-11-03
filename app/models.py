from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # admin, bu_head, delivery_head, project_manager, employee
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    bu_head_id = Column(Integer, ForeignKey("users.id"))
    delivery_head_id = Column(Integer, ForeignKey("users.id"))
    pm_id = Column(Integer, ForeignKey("users.id"))


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    id = Column(Integer, primary_key=True)
    type = Column(String, default="expense")
    amount = Column(Float, nullable=False)
    status = Column(String, default="pending", index=True)  # pending, approved, rejected
    requester_id = Column(Integer, ForeignKey("users.id"), index=True)
    approver_id = Column(Integer, ForeignKey("users.id"), index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))