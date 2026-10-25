import os
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .db import Base, engine
from . import models  # noqa: F401 (registers models on Base)
from .routers import auth_router, contacts_router, templates_router, campaigns_router, webhook_router, tracking_router

Base.metadata.create_all(bind=engine)

# Lightweight auto-migration: adds any new columns that create_all() can't
# add to tables that already exist in the live database.
_MIGRATIONS = [
    "ALTER TABLE templates ADD COLUMN IF NOT EXISTS header_type VARCHAR(16) DEFAULT 'NONE'",
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS header_image_url VARCHAR(1024) DEFAULT ''",
]
try:
    with engine.begin() as conn:
        for stmt in _MIGRATIONS:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass
except Exception:
    pass

app = FastAPI(title="WhatsApp Campaign Dashboard")
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "dev-secret-change-me"))

app.include_router(auth_router.router)
app.include_router(contacts_router.router)
app.include_router(templates_router.router)
app.include_router(campaigns_router.router)
app.include_router(webhook_router.router)
app.include_router(tracking_router.router)


@app.get("/healthz")
def healthz():
    return {"ok": True}

# end of main.py
