from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
    decided_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)    # who clicked approve
    on_behalf_of_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # whose authority was used
    grant_id = Column(Integer, nullable=True)
    decided_at = Column(DateTime, nullable=True)


class DelegationGrant(Base):
    __tablename__ = "delegation_grants"
    id = Column(Integer, primary_key=True)
    grantor_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    grantee_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    scopes = Column(String, nullable=False)       # comma-separated, e.g. "expense_approval"
    max_amount = Column(Float, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    status = Column(String, default="active")     # active or revoked
    created_at = Column(DateTime, default=utcnow)
    revoked_at = Column(DateTime, nullable=True)


class ImpersonationSession(Base):
    __tablename__ = "impersonation_sessions"
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    target_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mode = Column(String, default="view_as")
    started_at = Column(DateTime, default=utcnow)
    expires_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, index=True)            # who really did it
    effective_user_id = Column(Integer, index=True)   # whose view/permissions were used
    action = Column(String, nullable=False)
    resource = Column(String)
    result = Column(String)                           # success or denied
    timestamp = Column(DateTime, default=utcnow, index=True)