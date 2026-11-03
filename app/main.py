from fastapi import FastAPI
from app.database import Base, engine
from app.routers import auth

Base.metadata.create_all(engine)

app = FastAPI(title="Delegated Access & Impersonation Platform (Prototype)")
app.include_router(auth.router)


@app.get("/health")
def health():
    return {"status": "ok"}