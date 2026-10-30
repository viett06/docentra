import hashlib
from uuid import uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import AppError
from app.model import Document, DocumentPage, ProcessingJob, ScanPage, ScanSession
from app.services import storage
from app.services.audit import audit
from app.services.security import deny, require_access, utcnow


def load_session(db, user, session_id, lock=False):
    query = select(ScanSession).where(ScanSession.id == session_id)
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        deny(user, "scan_session", session_id)
    if user.role == "REVIEWER":
        require_access(db, user, row.employee_id, "review")
    else:
        require_access(db, user, row.employee_id, "capture")
        if row.created_by != user.id:
            deny(user, "scan_session", session_id)
    return row


def create_session(db, user, body):
    require_access(db, user, body.employee_id, "capture")
    row = db.scalar(
        select(ScanSession).where(
            ScanSession.created_by == user.id,
            ScanSession.client_session_id == body.client_session_id,
        )
    )
    if row:
        if row.employee_id != body.employee_id:
            raise AppError(409, "IDEMPOTENCY_CONFLICT", "Mã phiên đã dùng cho hồ sơ khác.")
        return row
    row = ScanSession(
        id=uuid4(), employee_id=body.employee_id, created_by=user.id, client_session_id=body.client_session_id
    )
    db.add(row)
    audit(db, user, "capture.created", "scan_session", row.id)
    db.commit()
    return row


def upload_page(db, user, session_id, client_page_id, order, data):
    row = load_session(db, user, session_id, lock=True)
    require_access(db, user, row.employee_id, "capture")
    if row.created_by != user.id:
        deny(user, "scan_session", session_id)
    sha = hashlib.sha256(data).hexdigest()
    previous = db.scalar(
        select(ScanPage).where(ScanPage.session_id == row.id, ScanPage.client_page_id == client_page_id)
    )
    if previous:
        if previous.sha256 != sha or previous.byte_size != len(data) or previous.page_order != order:
            raise AppError(409, "IDEMPOTENCY_CONFLICT", "Mã trang đã dùng cho ảnh khác.")
        return previous
    if row.status != "UPLOADING":
        raise AppError(409, "CAPTURE_FINALIZED", "Phiên đã chốt; hãy tạo phiên mới để chụp bổ sung.")
    pages = db.scalars(select(ScanPage).where(ScanPage.session_id == row.id)).all()
    if len(pages) >= get_settings().MAX_SESSION_PAGES or order != len(pages) + 1:
        raise AppError(409, "PAGE_ORDER", "Trang phải được gửi theo thứ tự, tối đa 30 trang mỗi phiên.")
    mime, width, height = storage.validate_image(data)
    page_id = uuid4()
    suffix = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[mime]
    key = f"originals/{row.id}/{page_id}.{suffix}"
    storage.put_object(key, data, mime)
    page = ScanPage(
        id=page_id,
        session_id=row.id,
        client_page_id=client_page_id,
        page_order=order,
        original_storage_key=key,
        sha256=sha,
        byte_size=len(data),
        mime_type=mime,
        width=width,
        height=height,
    )
    db.add(page)
    audit(db, user, "capture.page_uploaded", "scan_page", page_id, byte_size=len(data))
    db.commit()
    return page


def finalize(db, user, session_id, body):
    row = load_session(db, user, session_id, lock=True)
    require_access(db, user, row.employee_id, "capture")
    if row.created_by != user.id:
        deny(user, "scan_session", session_id)
    pages = db.scalars(
        select(ScanPage)
        .where(ScanPage.session_id == row.id, ScanPage.discarded_at.is_(None))
        .order_by(ScanPage.page_order)
    ).all()
    if [(p.id, p.sha256) for p in pages] != [(p.id, p.sha256) for p in body.pages]:
        raise AppError(409, "MANIFEST_MISMATCH", "Trang nhận được không khớp danh sách đã gửi. Vui lòng kiểm tra lại.")
    if row.status in {"UPLOADED", "FAILED"}:
        return row
    if row.status != "UPLOADING" or row.version != body.version:
        raise AppError(409, "VERSION_CONFLICT", "Phiên đã thay đổi. Vui lòng tải lại.")
    row.expected_page_count, row.finalized_at, row.status = len(pages), utcnow(), "UPLOADED"
    row.version += 1
    audit(db, user, "capture.finalized", "scan_session", row.id, page_count=len(pages))
    db.commit()
    return row


def enqueue(db, user, session_id, body):
    row = load_session(db, user, session_id, lock=True)
    require_access(db, user, row.employee_id, "capture")
    if row.created_by != user.id:
        deny(user, "scan_session", session_id)
    existing = db.scalar(
        select(ProcessingJob).where(
            ProcessingJob.session_id == row.id,
            ProcessingJob.idempotency_key == body.idempotency_key,
        )
    )
    request_groups = [{"title": group.title, "page_ids": [str(p) for p in group.page_ids]} for group in body.groups]
    if existing:
        if existing.input_manifest.get("request_groups") != request_groups:
            raise AppError(409, "IDEMPOTENCY_CONFLICT", "Mã xử lý đã dùng cho nhóm trang khác.")
        return existing
    if row.status not in {"UPLOADED", "FAILED"}:
        raise AppError(409, "SESSION_NOT_READY", "Phiên chưa sẵn sàng hoặc đã có kết quả xử lý.")
    pages = db.scalars(select(ScanPage).where(ScanPage.session_id == row.id, ScanPage.discarded_at.is_(None))).all()
    supplied = [page_id for group in body.groups for page_id in group.page_ids]
    if len(supplied) != len(set(supplied)) or set(supplied) != {p.id for p in pages}:
        raise AppError(
            422, "INVALID_GROUPING", "Mỗi trang phải nằm trong đúng một tài liệu; không được thiếu hoặc trùng."
        )
    prior_docs = db.scalars(select(Document).where(Document.session_id == row.id)).all()
    if prior_docs:
        previous = db.scalar(
            select(ProcessingJob).where(ProcessingJob.session_id == row.id).order_by(ProcessingJob.created_at.desc())
        )
        if previous.input_manifest.get("request_groups") != request_groups:
            raise AppError(409, "GROUPING_CHANGED", "Phiên lỗi chỉ được chạy lại với đúng nhóm trang ban đầu.")
        groups = previous.input_manifest["groups"]
    else:
        groups = []
        for group in body.groups:
            document = Document(id=uuid4(), session_id=row.id, title=group.title, type_code="unknown")
            db.add(document)
            db.flush()
            for index, page_id in enumerate(group.page_ids, 1):
                db.add(DocumentPage(document_id=document.id, scan_page_id=page_id, session_id=row.id, page_order=index))
            groups.append({"document_id": str(document.id), "page_ids": [str(p) for p in group.page_ids]})
    job = ProcessingJob(
        id=uuid4(),
        session_id=row.id,
        requested_by=user.id,
        idempotency_key=body.idempotency_key,
        pipeline_version="tesseract-rules-v1",
        input_manifest={
            "groups": groups,
            "request_groups": request_groups,
            "session_version": row.version,
            "pages": {str(p.id): p.sha256 for p in pages},
        },
    )
    db.add(job)
    row.status = "PROCESSING"
    audit(db, user, "processing.queued", "processing_job", job.id)
    db.commit()
    return job
