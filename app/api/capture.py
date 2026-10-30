from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session
from app.model import Document, ProcessingJob, ScanPage, User
from app.schema.capture import CaptureSessionView, FinalizeRequest, JobView, PageReceipt, ProcessRequest, SessionCreate
from app.services import capture
from app.services.security import current_user

router = APIRouter(prefix="/scan-sessions", tags=["Capture"])


def job_view(job):
    return {
        "id": job.id,
        "status": job.status,
        "attempt_count": job.attempt_count,
        "max_attempts": job.max_attempts,
        "error_code": job.error_code,
        "created_at": job.created_at,
        "finished_at": job.finished_at,
    }


def session_view(db, row):
    pages = db.scalars(
        select(ScanPage)
        .where(ScanPage.session_id == row.id, ScanPage.discarded_at.is_(None))
        .order_by(ScanPage.page_order)
    ).all()
    job = db.scalar(
        select(ProcessingJob).where(ProcessingJob.session_id == row.id).order_by(ProcessingJob.created_at.desc())
    )
    docs = db.scalars(select(Document).where(Document.session_id == row.id).order_by(Document.created_at)).all()
    return {
        "id": row.id,
        "employee_id": row.employee_id,
        "status": row.status,
        "version": row.version,
        "pages": [PageReceipt.model_validate(p) for p in pages],
        "job": job_view(job) if job else None,
        "document_ids": [d.id for d in docs],
    }


@router.post("", response_model=CaptureSessionView)
def create(body: SessionCreate, db: Session = Depends(get_session), user: User = Depends(current_user)):
    return session_view(db, capture.create_session(db, user, body))


@router.get("/{session_id}", response_model=CaptureSessionView)
def get(session_id: UUID, db: Session = Depends(get_session), user: User = Depends(current_user)):
    return session_view(db, capture.load_session(db, user, session_id))


@router.post("/{session_id}/pages", response_model=PageReceipt)
def upload(
    session_id: UUID,
    client_page_id: UUID = Form(...),
    page_order: int = Form(..., ge=1, le=30),
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    data = file.file.read(get_settings().MAX_UPLOAD_BYTES + 1)
    return capture.upload_page(db, user, session_id, client_page_id, page_order, data)


@router.post("/{session_id}/finalize", response_model=CaptureSessionView)
def finalize(
    session_id: UUID, body: FinalizeRequest, db: Session = Depends(get_session), user: User = Depends(current_user)
):
    return session_view(db, capture.finalize(db, user, session_id, body))


@router.post("/{session_id}/process", response_model=JobView)
def process(
    session_id: UUID, body: ProcessRequest, db: Session = Depends(get_session), user: User = Depends(current_user)
):
    return job_view(capture.enqueue(db, user, session_id, body))
