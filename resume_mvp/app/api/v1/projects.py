import json
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import ExportFile, JdProfile, ResumeProject, ResumeScore, ResumeSection, User
from app.db.session import get_db
from app.schemas.project import AnalyzeJdIn, CreateProjectTextIn, ExportIn, RewriteIn, UpdateSectionIn
from app.services.export_service import export_project_to_pdf
from app.services.project_service import (
    analyze_jd,
    create_project_from_file,
    create_project_from_text,
    parse_project,
    rewrite_sections,
    score_project,
)
from app.services.task_service import create_task, set_task_done, set_task_failed, set_task_running


router = APIRouter()


def _require_owned_project(db: Session, user_id: int, project_id: int) -> ResumeProject:
    project = db.execute(
        select(ResumeProject).where(ResumeProject.id == project_id, ResumeProject.user_id == user_id, ResumeProject.is_deleted.is_(False))
    ).scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.post("")
def create_project_text(payload: CreateProjectTextIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = create_project_from_text(
        db=db,
        user_id=current_user.id,
        title=payload.title,
        target_role=payload.target_role,
        target_city=payload.target_city,
        years_experience=payload.years_experience,
        source_text=payload.source_text,
    )
    return {"code": 0, "message": "ok", "data": {"project_id": project.id}}


@router.post("/from-file")
async def create_project_file(
    title: str = Form(...),
    target_role: str = Form(...),
    target_city: str | None = Form(None),
    years_experience: int | None = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = await file.read()
    project = create_project_from_file(
        db=db,
        user_id=current_user.id,
        title=title,
        target_role=target_role,
        target_city=target_city,
        years_experience=years_experience,
        filename=file.filename,
        content=content,
    )
    return {"code": 0, "message": "ok", "data": {"project_id": project.id}}


@router.get("")
def list_projects(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(ResumeProject)
        .where(ResumeProject.user_id == current_user.id, ResumeProject.is_deleted.is_(False))
        .order_by(desc(ResumeProject.id))
    ).scalars().all()
    return {
        "code": 0,
        "message": "ok",
        "data": [
            {
                "id": p.id,
                "title": p.title,
                "target_role": p.target_role,
                "parse_status": p.parse_status,
                "created_at": p.created_at.isoformat(),
            }
            for p in rows
        ],
    }


@router.get("/{project_id}")
def get_project(project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _require_owned_project(db, current_user.id, project_id)
    sections = db.execute(select(ResumeSection).where(ResumeSection.project_id == project.id).order_by(ResumeSection.sort_order)).scalars().all()
    score = db.execute(select(ResumeScore).where(ResumeScore.project_id == project.id)).scalars().first()
    jd = db.execute(select(JdProfile).where(JdProfile.project_id == project.id)).scalars().first()
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "project": {
                "id": project.id,
                "title": project.title,
                "target_role": project.target_role,
                "target_city": project.target_city,
                "years_experience": project.years_experience,
                "parse_status": project.parse_status,
            },
            "sections": [
                {
                    "id": s.id,
                    "section_type": s.section_type,
                    "origin_text": s.origin_text,
                    "optimized_text": s.optimized_text,
                    "is_accepted": s.is_accepted,
                }
                for s in sections
            ],
            "score": (
                {
                    "ats_score": score.ats_score,
                    "completeness_score": score.completeness_score,
                    "match_score": score.match_score,
                    "issues": json.loads(score.issues_json),
                }
                if score
                else None
            ),
            "jd_profile": (
                {
                    "keywords": json.loads(jd.keywords_json),
                    "missing_keywords": json.loads(jd.missing_keywords_json),
                }
                if jd
                else None
            ),
        },
    }


@router.delete("/{project_id}")
def delete_project(project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _require_owned_project(db, current_user.id, project_id)
    project.is_deleted = True
    db.commit()
    return {"code": 0, "message": "ok"}


@router.post("/{project_id}/parse")
def parse(project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _require_owned_project(db, current_user.id, project_id)
    task = create_task(db, current_user.id, "parse", project.id)
    try:
        set_task_running(db, task)
        sections = parse_project(db, project)
        set_task_done(db, task, {"section_count": len(sections)})
    except Exception as e:
        project.parse_status = 2
        db.commit()
        set_task_failed(db, task, str(e))
    return {"code": 0, "message": "ok", "data": {"task_id": task.id}}


@router.post("/{project_id}/score")
def score(project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _require_owned_project(db, current_user.id, project_id)
    task = create_task(db, current_user.id, "score", project.id)
    try:
        set_task_running(db, task)
        score_obj = score_project(db, project)
        set_task_done(
            db,
            task,
            {
                "ats_score": score_obj.ats_score,
                "completeness_score": score_obj.completeness_score,
                "match_score": score_obj.match_score,
            },
        )
    except Exception as e:
        set_task_failed(db, task, str(e))
    return {"code": 0, "message": "ok", "data": {"task_id": task.id}}


@router.post("/{project_id}/jd/analyze")
def jd_analyze(project_id: int, payload: AnalyzeJdIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _require_owned_project(db, current_user.id, project_id)
    profile = analyze_jd(db, project, payload.jd_text)
    return {
        "code": 0,
        "message": "ok",
        "data": {"keywords": json.loads(profile.keywords_json), "missing_keywords": json.loads(profile.missing_keywords_json)},
    }


@router.post("/{project_id}/rewrite")
def rewrite(project_id: int, payload: RewriteIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _require_owned_project(db, current_user.id, project_id)
    task = create_task(db, current_user.id, "rewrite", project.id)
    try:
        set_task_running(db, task)
        sections = rewrite_sections(db, project, payload.mode, payload.use_jd)
        set_task_done(db, task, {"section_count": len(sections)})
    except Exception as e:
        set_task_failed(db, task, str(e))
    return {"code": 0, "message": "ok", "data": {"task_id": task.id}}


@router.put("/sections/{section_id}")
def update_section(section_id: int, payload: UpdateSectionIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    section = db.execute(
        select(ResumeSection)
        .join(ResumeProject, ResumeProject.id == ResumeSection.project_id)
        .where(ResumeSection.id == section_id, ResumeProject.user_id == current_user.id)
    ).scalars().first()
    if not section:
        raise HTTPException(status_code=404, detail="section not found")
    if payload.optimized_text is not None:
        section.optimized_text = payload.optimized_text
    if payload.is_accepted is not None:
        section.is_accepted = payload.is_accepted
    db.commit()
    return {"code": 0, "message": "ok"}


@router.post("/{project_id}/export")
def export(project_id: int, payload: ExportIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.format.lower() != "pdf":
        raise HTTPException(status_code=400, detail="MVP only supports pdf")
    project = _require_owned_project(db, current_user.id, project_id)
    task = create_task(db, current_user.id, "export", project.id)
    try:
        set_task_running(db, task)
        export = export_project_to_pdf(db, project)
        set_task_done(db, task, {"export_id": export.id, "format": export.format})
    except Exception as e:
        set_task_failed(db, task, str(e))
    return {"code": 0, "message": "ok", "data": {"task_id": task.id}}


@router.get("/exports/{export_id}/download")
def download_export(export_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.execute(
        select(ExportFile)
        .join(ResumeProject, ResumeProject.id == ExportFile.project_id)
        .where(ExportFile.id == export_id, ResumeProject.user_id == current_user.id)
    ).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="export not found")
    if not os.path.exists(row.file_path):
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(row.file_path, filename=os.path.basename(row.file_path), media_type="application/pdf")
