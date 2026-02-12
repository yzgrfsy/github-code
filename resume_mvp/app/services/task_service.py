import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import AsyncTask


def create_task(db: Session, user_id: int, task_type: str, project_id: int | None = None) -> AsyncTask:
    task = AsyncTask(user_id=user_id, project_id=project_id, task_type=task_type, status="queued")
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def set_task_running(db: Session, task: AsyncTask) -> None:
    task.status = "running"
    task.updated_at = datetime.utcnow()
    db.commit()


def set_task_done(db: Session, task: AsyncTask, result: dict | list | None = None) -> None:
    task.status = "done"
    task.result_json = json.dumps(result or {}, ensure_ascii=False)
    task.updated_at = datetime.utcnow()
    db.commit()


def set_task_failed(db: Session, task: AsyncTask, error_message: str) -> None:
    task.status = "failed"
    task.error_message = error_message
    task.updated_at = datetime.utcnow()
    db.commit()

