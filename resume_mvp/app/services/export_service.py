import os
import re
from datetime import datetime

from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import ExportFile, ResumeProject, ResumeSection


def _safe_pdf_text(text: str) -> str:
    # Keep export stable even when there are unsupported font glyphs.
    return re.sub(r"[^\x00-\x7F]+", "?", text)


def export_project_to_pdf(db: Session, project: ResumeProject) -> ExportFile:
    sections = db.execute(select(ResumeSection).where(ResumeSection.project_id == project.id).order_by(ResumeSection.sort_order)).scalars().all()
    settings = get_settings()
    export_dir = os.path.join(settings.storage_dir, "exports")
    os.makedirs(export_dir, exist_ok=True)
    filename = f"resume_{project.id}_{int(datetime.utcnow().timestamp())}.pdf"
    file_path = os.path.join(export_dir, filename)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, _safe_pdf_text(project.title), ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, _safe_pdf_text(f"Target Role: {project.target_role}"), ln=True)

    for sec in sections:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, f"Section {sec.section_type}", ln=True)
        pdf.set_font("Helvetica", "", 10)
        final_text = sec.optimized_text or sec.origin_text
        for line in final_text.splitlines():
            pdf.multi_cell(0, 6, _safe_pdf_text(line))

    pdf.output(file_path)
    record = ExportFile(project_id=project.id, format="pdf", file_path=file_path)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

