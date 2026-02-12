from fastapi import FastAPI
from sqlalchemy import select

from app.api.router import api_router
from app.core.config import get_settings
from app.db.models import Plan
from app.db.session import SessionLocal, init_db
from app.services.project_service import ensure_storage_dirs


settings = get_settings()
app = FastAPI(title=settings.app_name, debug=settings.app_debug)
app.include_router(api_router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.on_event("startup")
def startup():
    ensure_storage_dirs()
    init_db()
    seed_plans()


def seed_plans() -> None:
    db = SessionLocal()
    try:
        existing = db.execute(select(Plan)).scalars().all()
        if existing:
            return
        db.add_all(
            [
                Plan(plan_code="FREE", name="Free", price_cents=0, quota_per_month=3),
                Plan(plan_code="PRO_MONTHLY", name="Pro Monthly", price_cents=3900, quota_per_month=200),
            ]
        )
        db.commit()
    finally:
        db.close()

