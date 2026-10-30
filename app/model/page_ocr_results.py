from sqlalchemy import (
    CheckConstraint,
    Column,
    Computed,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID

from app.db.base import Base


class PageOcrResult(Base):
    __tablename__ = "page_ocr_results"

    __table_args__ = (
        ForeignKeyConstraint(
            ["job_id", "session_id"],
            ["processing_jobs.id", "processing_jobs.session_id"],
            name="fk_page_ocr_results_job_session",
        ),
        ForeignKeyConstraint(
            ["scan_page_id", "session_id"],
            ["scan_pages.id", "scan_pages.session_id"],
            name="fk_page_ocr_results_scan_page_session",
        ),
        UniqueConstraint("job_id", "scan_page_id", name="uq_page_ocr_results_job_page"),
        CheckConstraint("jsonb_typeof(blocks) = 'array'", name="ck_page_ocr_results_blocks"),
        CheckConstraint("jsonb_typeof(quality_flags) = 'array'", name="ck_page_ocr_results_quality_flags"),
        Index("idx_page_ocr_results_scan_page_id", "scan_page_id"),
        Index("idx_page_ocr_results_search_vector", "search_vector", postgresql_using="gin"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    job_id = Column(UUID(as_uuid=True), nullable=False)
    scan_page_id = Column(UUID(as_uuid=True), nullable=False)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    engine_version = Column(String(100), nullable=False)
    text_content = Column(Text, nullable=False)
    blocks = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    processed_storage_key = Column(String(1000), nullable=True, unique=True)
    quality_flags = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    search_vector = Column(
        TSVECTOR, Computed("to_tsvector('simple'::regconfig, text_content)", persisted=True), nullable=False
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
