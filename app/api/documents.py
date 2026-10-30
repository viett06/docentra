import csv
from io import StringIO
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.model import ReviewAction, User
from app.schema.catalog import ReviewHistoryView
from app.schema.documents import DocumentUpdate, DocumentView, ReasonRequest, VerifyRequest
from app.services import documents
from app.services.audit import audit
from app.services.security import current_user

router = APIRouter(prefix="/documents", tags=["Documents & review"])


@router.get("/{document_id}", response_model=DocumentView)
def get(document_id: UUID, db: Session = Depends(get_session), user: User = Depends(current_user)):
    return documents.detail(db, documents.load_document(db, user, document_id))


@router.patch("/{document_id}", response_model=DocumentView)
def save(
    document_id: UUID, body: DocumentUpdate, db: Session = Depends(get_session), user: User = Depends(current_user)
):
    return documents.detail(db, documents.save(db, user, document_id, body))


@router.post("/{document_id}/verify", response_model=DocumentView)
def verify(
    document_id: UUID, body: VerifyRequest, db: Session = Depends(get_session), user: User = Depends(current_user)
):
    return documents.detail(db, documents.verify(db, user, document_id, body))


@router.post("/{document_id}/reject", response_model=DocumentView)
def reject(
    document_id: UUID, body: ReasonRequest, db: Session = Depends(get_session), user: User = Depends(current_user)
):
    return documents.detail(db, documents.change_status(db, user, document_id, body))


@router.post("/{document_id}/reopen", response_model=DocumentView)
def reopen(
    document_id: UUID, body: ReasonRequest, db: Session = Depends(get_session), user: User = Depends(current_user)
):
    return documents.detail(db, documents.change_status(db, user, document_id, body, reopen=True))


@router.get("/{document_id}/history", response_model=list[ReviewHistoryView])
def history(document_id: UUID, db: Session = Depends(get_session), user: User = Depends(current_user)):
    documents.load_document(db, user, document_id, review=True)
    rows = db.scalars(
        select(ReviewAction).where(ReviewAction.document_id == document_id).order_by(ReviewAction.created_at.desc())
    ).all()
    return [
        {
            "id": r.id,
            "version": r.document_version,
            "action": r.action,
            "changes": r.changes,
            "reason": r.reason,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/{document_id}/export")
def export(document_id: UUID, db: Session = Depends(get_session), user: User = Depends(current_user)):
    document = documents.load_document(db, user, document_id)
    if document.review_status != "VERIFIED":
        from app.core.errors import AppError

        raise AppError(409, "NOT_VERIFIED", "Chỉ xuất dữ liệu đã xác minh.")
    view = documents.detail(db, document)
    stream = StringIO()
    writer = csv.writer(stream)
    writer.writerow(["employee_code", "document_type", "field_name", "value", "source_page_id"])

    def safe(value):
        value = str(value or "")
        risky = value.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n"))
        return "'" + value if risky else value

    for field in view["fields"]:
        writer.writerow(
            [
                safe(view["employee_code"]),
                safe(document.type_code),
                safe(field["field_name"]),
                safe(field["value"]),
                safe(field["source_page_id"]),
            ]
        )
    audit(db, user, "document.exported", "document", document.id)
    db.commit()
    return Response(
        "\ufeff" + stream.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="docentra-{document_id}.csv"'},
    )
