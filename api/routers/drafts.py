import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from api.deps import get_db
from api.export import render_draft_html, render_draft_pdf
from api.schemas import DraftPatch, DraftResponse
from db.models import EmailDraft

router = APIRouter(prefix="/api/drafts", tags=["drafts"])


@router.get("", response_model=list[DraftResponse])
def list_drafts(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(EmailDraft)
    if status:
        query = query.filter(EmailDraft.status == status)
    return query.order_by(EmailDraft.created_at.desc()).all()


@router.patch("/{draft_id}", response_model=DraftResponse)
def patch_draft(draft_id: uuid.UUID, payload: DraftPatch, db: Session = Depends(get_db)):
    draft = db.query(EmailDraft).filter_by(id=draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if payload.subject is not None:
        draft.subject = payload.subject
    if payload.body is not None:
        draft.body = payload.body
    if payload.status is not None:
        draft.status = payload.status
    db.commit()
    db.refresh(draft)
    return draft


@router.get("/{draft_id}/export")
def export_draft(draft_id: uuid.UUID, format: str = "html", db: Session = Depends(get_db)):
    draft = db.query(EmailDraft).filter_by(id=draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    clinic_name = draft.clinic.name if draft.clinic else "Clinic"
    html = render_draft_html(clinic_name=clinic_name, subject=draft.subject, body=draft.body)

    draft.exported_at = datetime.now(timezone.utc)
    draft.export_format = format
    db.commit()

    if format == "pdf":
        pdf = render_draft_pdf(html)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="draft_{draft_id}.pdf"'},
        )
    return HTMLResponse(content=html)


@router.post("/export-batch")
def export_batch(db: Session = Depends(get_db)):
    approved = db.query(EmailDraft).filter_by(status="approved").all()
    if not approved:
        raise HTTPException(status_code=404, detail="No approved drafts found")

    from io import BytesIO
    import zipfile

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for draft in approved:
            clinic_name = draft.clinic.name if draft.clinic else "Clinic"
            html = render_draft_html(clinic_name=clinic_name, subject=draft.subject, body=draft.body)
            pdf = render_draft_pdf(html)
            zf.writestr(f"draft_{draft.id}.pdf", pdf)
            draft.exported_at = datetime.now(timezone.utc)

    db.commit()
    buffer.seek(0)
    return Response(
        content=buffer.read(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=drafts_export.zip"},
    )
