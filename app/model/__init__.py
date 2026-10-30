"""SQLAlchemy table definitions for the Docentra MVP."""

from app.model.audit_logs import AuditLog
from app.model.auth_sessions import AuthSession
from app.model.document_fields import DocumentField
from app.model.document_pages import DocumentPage
from app.model.document_types import DocumentType
from app.model.documents import Document
from app.model.employee_access import EmployeeAccess
from app.model.employees import Employee
from app.model.field_predictions import FieldPrediction
from app.model.page_ocr_results import PageOcrResult
from app.model.processing_jobs import ProcessingJob
from app.model.review_actions import ReviewAction
from app.model.scan_pages import ScanPage
from app.model.scan_sessions import ScanSession
from app.model.users import User

__all__ = [
    "AuditLog",
    "AuthSession",
    "Document",
    "DocumentField",
    "DocumentPage",
    "DocumentType",
    "Employee",
    "EmployeeAccess",
    "FieldPrediction",
    "PageOcrResult",
    "ProcessingJob",
    "ReviewAction",
    "ScanPage",
    "ScanSession",
    "User",
]
