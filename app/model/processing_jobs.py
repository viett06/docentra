from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    __table_args__ = (
        UniqueConstraint("session_id", "idempotency_key", name="uq_processing_jobs_session_key"),
        UniqueConstraint("id", "session_id", name="uq_processing_jobs_id_session"),
        CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED')", name="ck_processing_jobs_status"
        ),
        CheckConstraint("max_attempts BETWEEN 1 AND 5", name="ck_processing_jobs_max_attempts"),
        CheckConstraint("attempt_count BETWEEN 0 AND max_attempts", name="ck_processing_jobs_attempt_count"),
        CheckConstraint(
            "(status = 'RUNNING' AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL) OR "
            "(status <> 'RUNNING' AND lease_token IS NULL AND lease_expires_at IS NULL)",
            name="ck_processing_jobs_lease",
        ),
        CheckConstraint(
            "(status IN ('SUCCEEDED', 'FAILED', 'CANCELLED')) = (finished_at IS NOT NULL)",
            name="ck_processing_jobs_finished_at",
        ),
        CheckConstraint("jsonb_typeof(input_manifest) = 'object'", name="ck_processing_jobs_manifest"),
        CheckConstraint(
            "result_summary IS NULL OR jsonb_typeof(result_summary) = 'object'", name="ck_processing_jobs_summary"
        ),
        Index(
            "uq_processing_jobs_active_session",
            "session_id",
            unique=True,
            postgresql_where=text("status IN ('QUEUED', 'RUNNING')"),
        ),
        Index("idx_processing_jobs_dispatch", "available_at", "created_at", postgresql_where=text("status = 'QUEUED'")),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    session_id = Column(UUID(as_uuid=True), ForeignKey("scan_sessions.id"), nullable=False)
    requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    idempotency_key = Column(UUID(as_uuid=True), nullable=False)
    pipeline_version = Column(String(100), nullable=False)
    input_manifest = Column(JSONB, nullable=False)
    status = Column(String(50), nullable=False, default="QUEUED", server_default=text("'QUEUED'"))
    attempt_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    max_attempts = Column(Integer, nullable=False, default=3, server_default=text("3"))
    available_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    lease_token = Column(UUID(as_uuid=True), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error_code = Column(String(100), nullable=True)
    result_summary = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
