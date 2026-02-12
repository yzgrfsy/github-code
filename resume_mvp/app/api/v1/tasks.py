import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import AsyncTask, User
from app.db.session import get_db


router = APIRouter()


@router.get("/{task_id}")
def get_task(task_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.execute(select(AsyncTask).where(AsyncTask.id == task_id, AsyncTask.user_id == current_user.id)).scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    result = json.loads(task.result_json) if task.result_json else None
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "id": task.id,
            "task_type": task.task_type,
            "status": task.status,
            "error_message": task.error_message,
            "result": result,
        },
    }

