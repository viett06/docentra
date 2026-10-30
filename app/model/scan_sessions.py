from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base
from app.model.timestamp import TimestampMixin


class ScanSession(TimestampMixin, Base):
    __tablename__ = "scan_sessions"

    __table_args__ = (
        UniqueConstraint("created_by", "client_session_id", name="uq_scan_sessions_creator_client"),
        CheckConstraint(
            "status IN ('UPLOADING', 'UPLOADED', 'PROCESSING', 'NEEDS_REVIEW', 'COMPLETED', 'FAILED', 'CANCELLED')",
            name="ck_scan_sessions_status",
        ),
        CheckConstraint("expected_page_count IS NULL OR expected_page_count > 0", name="ck_scan_sessions_page_count"),
        CheckConstraint("version > 0", name="ck_scan_sessions_version"),
        CheckConstraint(
            "status IN ('UPLOADING', 'CANCELLED') OR (finalized_at IS NOT NULL AND expected_page_count IS NOT NULL)",
            name="ck_scan_sessions_finalized",
        ),
        Index("idx_scan_sessions_employee_created_at", "employee_id", "created_at"),
        Index("idx_scan_sessions_created_by_status", "created_by", "status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    client_session_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(50), nullable=False, default="UPLOADING", server_default=text("'UPLOADING'"))
    expected_page_count = Column(Integer, nullable=True)
    finalized_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default=text("1"))
