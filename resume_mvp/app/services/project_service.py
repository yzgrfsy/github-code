import json
import os
import re
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import JdProfile, ResumeProject, ResumeScore, ResumeSection, UsageLedger


SECTION_MAP = {
    "profile": 1,
    "education": 2,
    "experience": 3,
    "project": 4,
    "skills": 5,
}


def ensure_storage_dirs() -> None:
    settings = get_settings()
    os.makedirs(settings.storage_dir, exist_ok=True)
    os.makedirs(os.path.join(settings.storage_dir, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(settings.storage_dir, "exports"), exist_ok=True)


def create_project_from_text(
    db: Session,
    user_id: int,
    title: str,
    target_role: str,
    target_city: str | None,
    years_experience: int | None,
    source_text: str,
) -> ResumeProject:
    project = ResumeProject(
        user_id=user_id,
        title=title,
        target_role=target_role,
        target_city=target_city,
        years_experience=years_experience,
        source_type=2,
        source_text=source_text.strip(),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def create_project_from_file(
    db: Session,
    user_id: int,
    title: str,
    target_role: str,
    target_city: str | None,
    years_experience: int | None,
    filename: str,
    content: bytes,
) -> ResumeProject:
    ensure_storage_dirs()
    safe_name = f"{int(datetime.utcnow().timestamp())}_{filename}"
    file_path = os.path.join(get_settings().storage_dir, "uploads", safe_name)
    with open(file_path, "wb") as f:
        f.write(content)

    source_text = extract_text_from_file(file_path)
    project = ResumeProject(
        user_id=user_id,
        title=title,
        target_role=target_role,
        target_city=target_city,
        years_experience=years_experience,
        source_type=1,
        source_file_url=file_path,
        source_text=source_text,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def extract_text_from_file(file_path: str) -> str:
    # MVP fallback parser:
    # - txt: read directly
    # - docx/pdf: currently fall back to file-name marker, to keep service runnable
    lower = file_path.lower()
    if lower.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    return "文件已上传。MVP 当前对 PDF/DOCX 采用占位解析，请改用文本粘贴以获得最佳结果。"


def parse_project(db: Session, project: ResumeProject) -> list[ResumeSection]:
    # Replace existing sections for re-parse.
    old_sections = db.execute(select(ResumeSection).where(ResumeSection.project_id == project.id)).scalars().all()
    for s in old_sections:
        db.delete(s)
    db.flush()

    text = (project.source_text or "").strip()
    if not text:
        raise ValueError("source_text is empty")

    chunks = split_sections(text)
    sections: list[ResumeSection] = []
    order = 0
    for section_name, section_text in chunks:
        section = ResumeSection(
            project_id=project.id,
            section_type=SECTION_MAP.get(section_name, 1),
            origin_text=section_text.strip(),
            sort_order=order,
        )
        db.add(section)
        sections.append(section)
        order += 1

    project.parse_status = 1
    project.updated_at = datetime.utcnow()
    db.commit()
    for s in sections:
        db.refresh(s)
    return sections


def split_sections(text: str) -> list[tuple[str, str]]:
    markers = [
        ("education", ["教育", "education"]),
        ("experience", ["工作经历", "experience", "经历"]),
        ("project", ["项目经历", "projects", "project"]),
        ("skills", ["技能", "skills"]),
    ]
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    if not lines:
        return [("profile", text)]

    out: list[tuple[str, str]] = []
    current_type = "profile"
    buf: list[str] = []
    for line in lines:
        lowered = line.lower()
        matched = None
        for name, keys in markers:
            if any(key in lowered for key in keys):
                matched = name
                break
        if matched:
            if buf:
                out.append((current_type, "\n".join(buf)))
            current_type = matched
            buf = []
            continue
        buf.append(line)
    if buf:
        out.append((current_type, "\n".join(buf)))
    if not out:
        out.append(("profile", text))
    return out


def score_project(db: Session, project: ResumeProject) -> ResumeScore:
    sections = db.execute(select(ResumeSection).where(ResumeSection.project_id == project.id)).scalars().all()
    all_text = "\n".join([s.origin_text for s in sections]).lower()
    issues = []

    ats = 70
    if len(all_text) < 300:
        ats -= 15
        issues.append("简历内容偏短，建议补充可量化成果。")
    if "@" not in all_text and "邮箱" not in all_text:
        ats -= 10
        issues.append("缺少联系方式字段，可能影响 HR 回访。")

    completeness = min(95, 30 + len(sections) * 15)
    required = {"education", "experience", "skills"}
    found = set()
    for s in sections:
        for k, v in SECTION_MAP.items():
            if s.section_type == v:
                found.add(k)
    for key in required - found:
        issues.append(f"缺少 {key} 模块。")
        completeness -= 8

    role_keywords = role_to_keywords(project.target_role)
    hit = sum(1 for k in role_keywords if k in all_text)
    match = int(40 + min(55, hit * 8))
    if hit < 3:
        issues.append(f"与目标岗位 `{project.target_role}` 的关键词匹配偏低。")

    existing = db.execute(select(ResumeScore).where(ResumeScore.project_id == project.id)).scalars().first()
    payload = json.dumps(issues, ensure_ascii=False)
    if existing:
        existing.ats_score = max(1, min(100, ats))
        existing.completeness_score = max(1, min(100, completeness))
        existing.match_score = max(1, min(100, match))
        existing.issues_json = payload
        score = existing
    else:
        score = ResumeScore(
            project_id=project.id,
            ats_score=max(1, min(100, ats)),
            completeness_score=max(1, min(100, completeness)),
            match_score=max(1, min(100, match)),
            issues_json=payload,
        )
        db.add(score)
    db.commit()
    db.refresh(score)
    return score


def analyze_jd(db: Session, project: ResumeProject, jd_text: str) -> JdProfile:
    keywords = extract_keywords(jd_text)
    all_text = (project.source_text or "").lower()
    missing = [k for k in keywords if k not in all_text]
    existing = db.execute(select(JdProfile).where(JdProfile.project_id == project.id)).scalars().first()
    if existing:
        existing.jd_text = jd_text
        existing.keywords_json = json.dumps(keywords, ensure_ascii=False)
        existing.missing_keywords_json = json.dumps(missing, ensure_ascii=False)
        profile = existing
    else:
        profile = JdProfile(
            project_id=project.id,
            jd_text=jd_text,
            keywords_json=json.dumps(keywords, ensure_ascii=False),
            missing_keywords_json=json.dumps(missing, ensure_ascii=False),
        )
        db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def rewrite_sections(db: Session, project: ResumeProject, mode: str, use_jd: bool) -> list[ResumeSection]:
    sections = db.execute(select(ResumeSection).where(ResumeSection.project_id == project.id).order_by(ResumeSection.sort_order)).scalars().all()
    jd_missing: list[str] = []
    if use_jd:
        jd = db.execute(select(JdProfile).where(JdProfile.project_id == project.id)).scalars().first()
        if jd:
            jd_missing = json.loads(jd.missing_keywords_json)

    for sec in sections:
        sec.optimized_text = optimize_text(sec.origin_text, mode, jd_missing)
        sec.is_accepted = False
    db.add(UsageLedger(user_id=project.user_id, project_id=project.id, action_type=1, used_units=1))
    db.commit()
    return sections


def optimize_text(origin: str, mode: str, missing_keywords: list[str]) -> str:
    lines = [x.strip("- ").strip() for x in origin.splitlines() if x.strip()]
    out: list[str] = []
    prefix = {
        "conservative": "优化建议：",
        "balanced": "成果导向：",
        "aggressive": "高强度改写：",
    }.get(mode, "成果导向：")

    for line in lines:
        if re.search(r"\d+%|\d+人|\d+个|\d+万", line):
            out.append(f"{prefix}{line}")
        else:
            out.append(f"{prefix}{line}，并通过量化指标体现业务影响。")
    if missing_keywords:
        top = "、".join(missing_keywords[:5])
        out.append(f"关键词补齐建议：可结合实际补充 {top}。")
    return "\n".join(out) if out else origin


def role_to_keywords(role: str) -> list[str]:
    role = role.lower()
    if "python" in role:
        return ["python", "fastapi", "flask", "sql", "redis", "docker", "api"]
    if "前端" in role or "frontend" in role:
        return ["vue", "react", "javascript", "typescript", "css", "webpack"]
    return ["沟通", "协作", "项目", "交付", "优化"]


def extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+.#-]{1,20}|[\u4e00-\u9fa5]{2,8}", text)
    stop = {"我们", "负责", "要求", "相关", "优先", "经验", "能力", "以上", "以及", "进行"}
    seen = set()
    result: list[str] = []
    for w in words:
        lw = w.lower()
        if lw in stop:
            continue
        if lw not in seen:
            seen.add(lw)
            result.append(w)
    return result[:30]

