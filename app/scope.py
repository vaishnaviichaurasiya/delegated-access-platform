from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import User, Project, ApprovalRequest


def team_user_ids(db: Session, user: User) -> set[int]:
    """All people reporting to this user, directly or indirectly."""
    if user.role == "admin":
        return {uid for (uid,) in db.query(User.id).filter(User.id != user.id).all()}
    ids: set[int] = set()
    frontier = [user.id]
    while frontier:
        rows = db.query(User.id).filter(User.manager_id.in_(frontier)).all()
        frontier = [uid for (uid,) in rows if uid not in ids]
        ids.update(frontier)
    return ids


def scoped_projects(db: Session, user: User):
    q = db.query(Project)
    if user.role == "admin":
        return q
    if user.role == "bu_head":
        return q.filter(Project.bu_head_id == user.id)
    if user.role == "delivery_head":
        return q.filter(Project.delivery_head_id == user.id)
    if user.role == "project_manager":
        return q.filter(Project.pm_id == user.id)
    return q.filter(Project.id == -1)  # employees: no project list


def scoped_approvals(db: Session, user: User):
    q = db.query(ApprovalRequest)
    if user.role == "admin":
        return q
    if user.role == "employee":
        return q.filter(ApprovalRequest.requester_id == user.id)
    project_ids = select(Project.id).where(
        {
            "bu_head": Project.bu_head_id,
            "delivery_head": Project.delivery_head_id,
            "project_manager": Project.pm_id,
        }[user.role] == user.id
    )
    return q.filter(ApprovalRequest.project_id.in_(project_ids))
