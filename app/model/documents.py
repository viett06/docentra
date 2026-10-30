from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base
from app.model.timestamp import TimestampMixin


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    __table_args__ = (
        UniqueConstraint("id", "session_id", name="uq_documents_id_session"),
        ForeignKeyConstraint(
            ["latest_job_id", "session_id"],
            ["processing_jobs.id", "processing_jobs.session_id"],
            name="fk_documents_latest_job_session",
        ),
        CheckConstraint(
            "review_status IN ('DRAFT', 'NEEDS_REVIEW', 'VERIFIED', 'REJECTED')", name="ck_documents_review_status"
        ),
        CheckConstraint("version > 0", name="ck_documents_version"),
        CheckConstraint(
            "(identity_confirmed_by IS NULL) = (identity_confirmed_at IS NULL)",
            name="ck_documents_identity_confirmation",
        ),
        CheckConstraint(
            "(review_status = 'VERIFIED' AND verified_by IS NOT NULL AND verified_at IS NOT NULL) OR "
            "(review_status <> 'VERIFIED' AND verified_by IS NULL AND verified_at IS NULL)",
            name="ck_documents_verification_metadata",
        ),
        CheckConstraint(
            "review_status <> 'VERIFIED' OR (type_code <> 'unknown' AND identity_confirmed_by IS NOT NULL)",
            name="ck_documents_verified_identity",
        ),
        Index("idx_documents_session_id", "session_id"),
        Index("idx_documents_review_status_created_at", "review_status", "created_at"),
        Index(
            "idx_documents_verified_type",
            "type_code",
            "verified_at",
            postgresql_where=text("review_status = 'VERIFIED'"),
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    session_id = Column(UUID(as_uuid=True), ForeignKey("scan_sessions.id"), nullable=False)
    type_code = Column(
        String(50),
        ForeignKey("document_types.code"),
        nullable=False,
        default="unknown",
        server_default=text("'unknown'"),
    )
    latest_job_id = Column(UUID(as_uuid=True), nullable=True)
    title = Column(String(500), nullable=False, default="", server_default=text("''"))
    review_status = Column(String(50), nullable=False, default="DRAFT", server_default=text("'DRAFT'"))
    identity_confirmed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    identity_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default=text("1"))
