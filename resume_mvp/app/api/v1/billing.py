from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Plan, Subscription, UsageLedger, User
from app.db.session import get_db


router = APIRouter()


@router.get("/plans")
def get_plans(db: Session = Depends(get_db)):
    plans = db.execute(select(Plan).order_by(Plan.price_cents)).scalars().all()
    return {
        "code": 0,
        "message": "ok",
        "data": [
            {"plan_code": p.plan_code, "name": p.name, "price_cents": p.price_cents, "quota_per_month": p.quota_per_month}
            for p in plans
        ],
    }


@router.get("/me")
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = db.execute(
        select(Subscription).where(Subscription.user_id == current_user.id).order_by(desc(Subscription.id))
    ).scalars().first()

    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    used = (
        db.execute(
            select(func.coalesce(func.sum(UsageLedger.used_units), 0)).where(
                and_(UsageLedger.user_id == current_user.id, UsageLedger.created_at >= month_start)
            )
        )
        .scalars()
        .first()
    )
    quota = 3
    plan_code = "FREE"
    if sub and sub.status == 1 and sub.end_at > now:
        plan = db.execute(select(Plan).where(Plan.id == sub.plan_id)).scalars().first()
        if plan:
            quota = plan.quota_per_month
            plan_code = plan.plan_code

    return {
        "code": 0,
        "message": "ok",
        "data": {"plan_code": plan_code, "quota_per_month": quota, "used_this_month": used, "remaining": max(0, quota - int(used))},
    }


@router.post("/mock/activate-pro")
def activate_pro(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = db.execute(select(Plan).where(Plan.plan_code == "PRO_MONTHLY")).scalars().first()
    if not plan:
        return {"code": 1001, "message": "plan not found"}
    sub = Subscription(
        user_id=current_user.id,
        plan_id=plan.id,
        status=1,
        start_at=datetime.utcnow(),
        end_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(sub)
    db.commit()
    return {"code": 0, "message": "ok", "data": {"subscription_id": sub.id}}

