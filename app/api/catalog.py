from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, literal_column, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_session
from app.model import (
    AuditLog,
    Document,
    DocumentField,
    DocumentPage,
    DocumentType,
    Employee,
    EmployeeAccess,
    PageOcrResult,
    ProcessingJob,
    ScanPage,
    ScanSession,
    User,
)
from app.schema.catalog import AuditView, CoverageView, DashboardView, DocumentListView, DocumentTypeView, EmployeeView
from app.services import documents, storage
from app.services.audit import audit
from app.services.security import current_user, deny, require_access

router = APIRouter(tags=["Catalog & retrieval"])


def scope_ids(user):
    grant = select(EmployeeAccess.employee_id).where(EmployeeAccess.user_id == user.id)
    if user.role == "CAPTURE":
        return grant.where(EmployeeAccess.can_capture.is_(True))
    if user.role == "REVIEWER":
        return grant.where(EmployeeAccess.can_review.is_(True))
    if user.role == "VIEWER":
        return grant.where(EmployeeAccess.can_view.is_(True))
    return grant.where(False)


def scoped_documents(user):
    return select(Document).join(ScanSession).where(ScanSession.employee_id.in_(scope_ids(user)))


@router.get("/document-types", response_model=list[DocumentTypeView])
def types(db: Session = Depends(get_session), user: User = Depends(current_user)):
    return [
        {"code": t.code, "name": t.name, "fields": t.field_schema}
        for t in db.scalars(select(DocumentType).where(DocumentType.is_active.is_(True)).order_by(DocumentType.code))
    ]


@router.get("/employees", response_model=list[EmployeeView])
def employees(
    q: str = Query(default="", max_length=100), db: Session = Depends(get_session), user: User = Depends(current_user)
):
    rows = db.scalars(
        select(Employee)
        .where(
            Employee.id.in_(scope_ids(user)),
            Employee.is_active.is_(True),
            or_(Employee.full_name.ilike(f"%{q}%"), Employee.employee_code.ilike(f"%{q}%")),
        )
        .order_by(Employee.employee_code)
        .limit(100)
    ).all()
    counts = db.execute(
        select(ScanSession.employee_id, Document.review_status, func.count(Document.id))
        .join(Document, Document.session_id == ScanSession.id)
        .where(ScanSession.employee_id.in_([e.id for e in rows]))
        .group_by(ScanSession.employee_id, Document.review_status)
    ).all()
    mapping = {}
    for employee_id, status, count in counts:
        mapping.setdefault(employee_id, {})[status] = count
    return [
        {"id": e.id, "employee_code": e.employee_code, "full_name": e.full_name, "counts": mapping.get(e.id, {})}
        for e in rows
    ]


@router.get("/employees/{employee_id}/coverage", response_model=list[CoverageView])
def coverage(employee_id: UUID, db: Session = Depends(get_session), user: User = Depends(current_user)):
    require_access(db, user, employee_id, "view")
    rows = db.execute(
        select(Document.type_code, Document.review_status, func.count(Document.id))
        .join(ScanSession)
        .where(ScanSession.employee_id == employee_id)
        .group_by(Document.type_code, Document.review_status)
    ).all()
    counts = {}
    for code, state, count in rows:
        counts.setdefault(code, {})[state] = count
    return [
        {"type_code": t.code, "name": t.name, "counts": counts.get(t.code, {})}
        for t in db.scalars(
            select(DocumentType).where(DocumentType.code != "unknown", DocumentType.is_active.is_(True))
        )
    ]


def list_documents(db, user, state, q="", type_code=None, employee_id=None, limit=30, offset=0):
    if user.role not in {"REVIEWER", "VIEWER"}:
        raise AppError(403, "FORBIDDEN", "Tài khoản này chưa có quyền tra cứu tài liệu.")
    query = scoped_documents(user).where(Document.review_status == state)
    if type_code:
        query = query.where(Document.type_code == type_code)
    if employee_id:
        query = query.where(ScanSession.employee_id == employee_id)
    if q:
        employee_matches = select(Employee.id).where(
            or_(Employee.full_name.ilike(f"%{q}%"), Employee.employee_code.ilike(f"%{q}%"))
        )
        field_matches = select(DocumentField.document_id).where(DocumentField.value.ilike(f"%{q}%"))
        ocr_match = (
            select(PageOcrResult.id)
            .join(DocumentPage, DocumentPage.scan_page_id == PageOcrResult.scan_page_id)
            .where(
                DocumentPage.document_id == Document.id,
                PageOcrResult.job_id == Document.latest_job_id,
                PageOcrResult.search_vector.op("@@")(
                    func.websearch_to_tsquery(literal_column("'simple'::regconfig"), q)
                ),
            )
            .exists()
        )
        query = query.where(
            or_(
                ScanSession.employee_id.in_(employee_matches),
                Document.title.ilike(f"%{q}%"),
                Document.id.in_(field_matches),
                ocr_match,
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(Document.created_at.desc(), Document.id).offset(offset).limit(limit)).all()
    items = []
    for row in rows:
        capture = db.get(ScanSession, row.session_id)
        employee = db.get(Employee, capture.employee_id)
        catalog = db.get(DocumentType, row.type_code)
        page_count = db.scalar(select(func.count()).select_from(DocumentPage).where(DocumentPage.document_id == row.id))
        items.append(
            {
                "id": row.id,
                "employee_code": employee.employee_code,
                "employee_name": employee.full_name,
                "title": row.title or catalog.name,
                "type_code": row.type_code,
                "type_name": catalog.name,
                "review_status": row.review_status,
                "version": row.version,
                "page_count": page_count,
                "created_at": row.created_at,
                "verified_at": row.verified_at,
            }
        )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/search", response_model=DocumentListView)
def search(
    q: str = Query(default="", max_length=100),
    type_code: str | None = None,
    employee_id: UUID | None = None,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    return list_documents(db, user, "VERIFIED", q, type_code, employee_id, limit, offset)


@router.get("/review-queue", response_model=DocumentListView)
def queue(
    q: str = Query(default="", max_length=100),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    if user.role != "REVIEWER":
        raise AppError(403, "FORBIDDEN", "Chỉ HR reviewer được kiểm tra tài liệu.")
    return list_documents(db, user, "NEEDS_REVIEW", q=q, limit=limit, offset=offset)


@router.get("/dashboard", response_model=DashboardView)
def dashboard(db: Session = Depends(get_session), user: User = Depends(current_user)):
    employee_count = db.scalar(select(func.count()).select_from(Employee).where(Employee.id.in_(scope_ids(user))))
    base = scoped_documents(user)
    # One subquery instance avoids an accidental Cartesian product in aggregations.
    scoped = base.subquery()
    counts = dict(db.execute(select(scoped.c.review_status, func.count()).group_by(scoped.c.review_status)).all())
    pages = db.scalar(
        select(func.count())
        .select_from(ScanPage)
        .join(ScanSession)
        .where(ScanSession.employee_id.in_(scope_ids(user)), ScanPage.discarded_at.is_(None))
    )
    jobs = db.execute(
        select(ProcessingJob.status, func.count())
        .join(ScanSession)
        .where(ScanSession.employee_id.in_(scope_ids(user)))
        .group_by(ProcessingJob.status)
    ).all()
    return {
        "employee_count": employee_count,
        "page_count": pages,
        "documents": counts,
        "jobs": dict(jobs),
        "demo_mode": get_settings().DEMO_MODE,
    }


@router.get("/pages/{page_id}/image")
def image(page_id: UUID, db: Session = Depends(get_session), user: User = Depends(current_user)):
    page = db.get(ScanPage, page_id)
    if not page or page.discarded_at is not None:
        deny(user, "scan_page", page_id)
    capture = db.get(ScanSession, page.session_id)
    if user.role == "CAPTURE":
        require_access(db, user, capture.employee_id, "capture")
        if capture.created_by != user.id or capture.status not in {"UPLOADING", "UPLOADED", "PROCESSING", "FAILED"}:
            deny(user, "scan_page", page_id)
    else:
        mapping = db.scalar(select(DocumentPage).where(DocumentPage.scan_page_id == page_id))
        if not mapping:
            if user.role != "REVIEWER":
                deny(user, "scan_page", page_id)
            require_access(db, user, capture.employee_id, "review")
        else:
            documents.load_document(db, user, mapping.document_id)
    data = storage.read_object(page.original_storage_key)
    audit(db, user, "scan.viewed", "scan_page", page.id)
    db.commit()
    return Response(
        data, media_type=page.mime_type, headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
    )


@router.get("/audit", response_model=list[AuditView])
def audit_list(db: Session = Depends(get_session), user: User = Depends(current_user)):
    query = select(AuditLog)
    if user.role != "ADMIN":
        query = query.where(AuditLog.actor_id == user.id)
    return [
        {
            "id": r.id,
            "action": r.action,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "outcome": r.outcome,
            "created_at": r.created_at,
        }
        for r in db.scalars(query.order_by(AuditLog.created_at.desc()).limit(100))
    ]
