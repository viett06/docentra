from datetime import date

from sqlalchemy import select

from app.core.errors import AppError
from app.model import (
    Document,
    DocumentField,
    DocumentPage,
    DocumentType,
    Employee,
    FieldPrediction,
    PageOcrResult,
    ProcessingJob,
    ReviewAction,
    ScanSession,
)
from app.services.audit import audit
from app.services.security import deny, require_access, utcnow


def load_document(db, user, document_id, review=False, lock=False):
    query = select(Document).where(Document.id == document_id)
    document = db.scalar(query.with_for_update() if lock else query)
    if not document:
        deny(user, "document", document_id)
    capture = db.get(ScanSession, document.session_id)
    if review or user.role == "REVIEWER":
        require_access(db, user, capture.employee_id, "review")
    else:
        require_access(db, user, capture.employee_id, "view")
        if document.review_status != "VERIFIED":
            deny(user, "document", document_id)
    return document


def detail(db, document):
    capture = db.get(ScanSession, document.session_id)
    employee = db.get(Employee, capture.employee_id)
    catalog = db.get(DocumentType, document.type_code)
    rows = {f.field_name: f for f in db.scalars(select(DocumentField).where(DocumentField.document_id == document.id))}
    pages = db.scalars(
        select(DocumentPage).where(DocumentPage.document_id == document.id).order_by(DocumentPage.page_order)
    ).all()
    job = db.get(ProcessingJob, document.latest_job_id) if document.latest_job_id else None
    summary = (job.result_summary or {}).get("documents", {}).get(str(document.id), {}) if job else {}
    fields = []
    for key, spec in catalog.field_schema.items():
        row = rows.get(key)
        prediction = db.get(FieldPrediction, row.prediction_id) if row and row.prediction_id else None
        fields.append(
            {
                "field_name": key,
                "label": spec.get("label", key),
                "field_type": spec.get("type", "string"),
                "required": spec.get("required", False),
                "value": row.value if row else None,
                "value_state": row.value_state if row else "NOT_FOUND",
                "source_page_id": row.source_page_id if row else None,
                "review_status": row.review_status if row else "PENDING",
                "predicted_value": prediction.predicted_value if prediction else None,
                "confidence": float(prediction.confidence)
                if prediction and prediction.confidence is not None
                else None,
            }
        )
    return {
        "id": document.id,
        "session_id": capture.id,
        "employee_id": employee.id,
        "employee_code": employee.employee_code,
        "employee_name": employee.full_name,
        "title": document.title,
        "type_code": document.type_code,
        "review_status": document.review_status,
        "version": document.version,
        "created_at": document.created_at,
        "verified_at": document.verified_at,
        "identity_match": summary.get("identity_match"),
        "identity_note": summary.get("identity_note"),
        "pages": [
            {"id": p.scan_page_id, "page_order": p.page_order, "image_url": f"/api/v1/pages/{p.scan_page_id}/image"}
            for p in pages
        ],
        "fields": fields,
    }


def expect_version(document, version):
    if document.version != version:
        raise AppError(409, "VERSION_CONFLICT", "Tài liệu đã được người khác cập nhật. Vui lòng tải lại trước khi sửa.")


def action(db, user, document, verb, changes=None, reason=None):
    document.version += 1
    db.add(
        ReviewAction(
            document_id=document.id,
            actor_id=user.id,
            document_version=document.version,
            action=verb,
            changes=changes or {},
            reason=reason,
        )
    )
    audit(db, user, f"document.{verb.lower()}", "document", document.id)


def sync_session(db, session_id):
    db.flush()
    states = db.scalars(select(Document.review_status).where(Document.session_id == session_id)).all()
    capture = db.get(ScanSession, session_id)
    capture.status = "COMPLETED" if states and all(s in {"VERIFIED", "REJECTED"} for s in states) else "NEEDS_REVIEW"


def check_field_value(field, spec):
    if field.value_state == "PRESENT" and spec.get("type") == "date":
        try:
            if date.fromisoformat(field.value).isoformat() != field.value:
                raise ValueError
        except (TypeError, ValueError):
            raise AppError(
                422, "INVALID_DATE", f"{spec.get('label', field.field_name)} phải là ngày hợp lệ YYYY-MM-DD."
            ) from None


def save(db, user, document_id, body):
    document = load_document(db, user, document_id, review=True, lock=True)
    expect_version(document, body.version)
    if document.review_status != "NEEDS_REVIEW":
        raise AppError(409, "REOPEN_REQUIRED", "Chỉ sửa tài liệu đang chờ kiểm tra. Hãy mở lại tài liệu đã duyệt.")
    catalog = db.get(DocumentType, body.type_code)
    if not catalog or not catalog.is_active:
        raise AppError(422, "INVALID_TYPE", "Loại tài liệu không hợp lệ.")
    names = [f.field_name for f in body.fields]
    if len(names) != len(set(names)) or set(names) != set(catalog.field_schema):
        raise AppError(422, "INVALID_FIELDS", "Cần gửi đúng các trường của loại tài liệu đang chọn.")
    sources = set(db.scalars(select(DocumentPage.scan_page_id).where(DocumentPage.document_id == document.id)))
    old_fields = {
        f.field_name: f for f in db.scalars(select(DocumentField).where(DocumentField.document_id == document.id))
    }
    before = {
        k: {"value": f.value, "state": f.value_state, "source": str(f.source_page_id) if f.source_page_id else None}
        for k, f in old_fields.items()
    }
    for key, row in list(old_fields.items()):
        if key not in catalog.field_schema:
            db.delete(row)
            del old_fields[key]
    for field in body.fields:
        check_field_value(field, catalog.field_schema[field.field_name])
        if field.source_page_id and field.source_page_id not in sources:
            raise AppError(422, "INVALID_SOURCE", "Trang nguồn không thuộc tài liệu này.")
        if field.reviewed and field.value_state == "PRESENT" and not field.source_page_id:
            raise AppError(422, "SOURCE_REQUIRED", "Trường đã đối chiếu cần chọn trang nguồn.")
        row = old_fields.get(field.field_name)
        if not row:
            row = DocumentField(document_id=document.id, field_name=field.field_name)
            db.add(row)
        prediction = db.get(FieldPrediction, row.prediction_id) if row.prediction_id else None
        row.value, row.value_state, row.source_page_id = field.value, field.value_state, field.source_page_id
        row.source_bbox = None
        if field.reviewed:
            unchanged = prediction and (
                prediction.predicted_value,
                prediction.value_state,
                prediction.source_page_id,
            ) == (field.value, field.value_state, field.source_page_id)
            row.review_status = "CONFIRMED" if unchanged else "CORRECTED"
            row.reviewed_by, row.reviewed_at = user.id, utcnow()
        else:
            row.review_status, row.reviewed_by, row.reviewed_at = "PENDING", None, None
    changes = {
        "before": before,
        "after": {f.field_name: f.model_dump(mode="json") for f in body.fields},
        "type_before": document.type_code,
        "type_after": body.type_code,
    }
    document.type_code, document.title = body.type_code, body.title
    action(db, user, document, "EDIT_FIELDS", changes)
    db.commit()
    return document


def verify(db, user, document_id, body):
    document = load_document(db, user, document_id, review=True, lock=True)
    expect_version(document, body.version)
    if document.review_status != "NEEDS_REVIEW" or document.type_code == "unknown":
        raise AppError(409, "NOT_VERIFIABLE", "Tài liệu cần được phân loại và đang ở trạng thái chờ kiểm tra.")
    catalog = db.get(DocumentType, document.type_code)
    fields = {
        f.field_name: f for f in db.scalars(select(DocumentField).where(DocumentField.document_id == document.id))
    }
    if not catalog.is_active or set(fields) != set(catalog.field_schema):
        raise AppError(422, "FIELDS_INCOMPLETE", "Chưa có đủ trường dữ liệu theo loại giấy tờ.")
    for key, spec in catalog.field_schema.items():
        row = fields[key]
        check_field_value(row, spec)
        if row.review_status == "PENDING" or (row.value_state == "PRESENT" and not row.source_page_id):
            raise AppError(422, "REVIEW_INCOMPLETE", "Cần đối chiếu từng trường và chọn trang nguồn.")
        if spec.get("required") and row.value_state != "PRESENT":
            raise AppError(422, "REQUIRED_FIELD", f"Thiếu trường bắt buộc: {spec.get('label', key)}.")
    job = db.get(ProcessingJob, document.latest_job_id) if document.latest_job_id else None
    if not job or job.status != "SUCCEEDED":
        raise AppError(409, "PROCESSING_INCOMPLETE", "Chưa có kết quả xử lý thành công.")
    pages = db.scalars(
        select(DocumentPage).where(DocumentPage.document_id == document.id).order_by(DocumentPage.page_order)
    ).all()
    group = next((g for g in job.input_manifest["groups"] if g["document_id"] == str(document.id)), None)
    if not pages or not group or [str(p.scan_page_id) for p in pages] != group["page_ids"]:
        raise AppError(409, "STALE_PROCESSING", "Nhóm trang đã thay đổi sau lần xử lý. Cần xử lý lại.")
    ocr_pages = set(db.scalars(select(PageOcrResult.scan_page_id).where(PageOcrResult.job_id == job.id)))
    if any(p.scan_page_id not in ocr_pages for p in pages):
        raise AppError(409, "MISSING_OCR", "Chưa xử lý đủ trang của tài liệu.")
    summary = (job.result_summary or {}).get("documents", {}).get(str(document.id), {})
    if summary.get("identity_match") is False:
        raise AppError(
            422, "IDENTITY_MISMATCH", "Mã nhân viên đọc được khác hồ sơ đã chọn. Từ chối và tạo phiên đúng nhân viên."
        )
    for row in fields.values():
        if row.prediction_id and db.get(FieldPrediction, row.prediction_id).job_id != job.id:
            raise AppError(409, "STALE_PREDICTION", "Đề xuất trường không thuộc lần xử lý hiện tại.")
    document.identity_confirmed_by, document.identity_confirmed_at = user.id, utcnow()
    document.verified_by, document.verified_at, document.review_status = user.id, utcnow(), "VERIFIED"
    action(db, user, document, "VERIFY")
    sync_session(db, document.session_id)
    db.commit()
    return document


def change_status(db, user, document_id, body, reopen=False):
    document = load_document(db, user, document_id, review=True, lock=True)
    expect_version(document, body.version)
    allowed = {"VERIFIED", "REJECTED"} if reopen else {"NEEDS_REVIEW"}
    if document.review_status not in allowed:
        raise AppError(409, "INVALID_TRANSITION", "Trạng thái tài liệu đã thay đổi.")
    document.review_status = "NEEDS_REVIEW" if reopen else "REJECTED"
    document.verified_by, document.verified_at = None, None
    document.identity_confirmed_by, document.identity_confirmed_at = None, None
    action(db, user, document, "REOPEN" if reopen else "REJECT", reason=body.reason)
    sync_session(db, document.session_id)
    db.commit()
    return document
