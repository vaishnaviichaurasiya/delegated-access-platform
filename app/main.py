from fastapi import FastAPI
from app.database import Base, engine
from app.routers import auth, dashboard, approvals, impersonation, audit_logs, delegations

Base.metadata.create_all(engine)

app = FastAPI(title="Delegated Access & Impersonation Platform (Prototype)")
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(approvals.router)
app.include_router(impersonation.router)
app.include_router(audit_logs.router)
app.include_router(delegations.router)


@app.get("/health")
def health():
    return {"status": "ok"}