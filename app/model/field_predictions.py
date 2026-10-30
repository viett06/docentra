from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class FieldPrediction(Base):
    __tablename__ = "field_predictions"

    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "session_id"],
            ["documents.id", "documents.session_id"],
            name="fk_field_predictions_document_session",
        ),
        ForeignKeyConstraint(
            ["job_id", "session_id"],
            ["processing_jobs.id", "processing_jobs.session_id"],
            name="fk_field_predictions_job_session",
        ),
        ForeignKeyConstraint(
            ["source_page_id", "session_id"],
            ["scan_pages.id", "scan_pages.session_id"],
            name="fk_field_predictions_source_session",
        ),
        UniqueConstraint("job_id", "document_id", "field_name", name="uq_field_predictions_job_document_field"),
        UniqueConstraint("id", "document_id", "field_name", name="uq_field_predictions_id_document_field"),
        CheckConstraint("btrim(field_name) <> ''", name="ck_field_predictions_field_name"),
        CheckConstraint(
            "value_state IN ('PRESENT', 'NOT_FOUND', 'UNREADABLE')", name="ck_field_predictions_value_state"
        ),
        CheckConstraint("confidence IS NULL OR confidence BETWEEN 0 AND 1", name="ck_field_predictions_confidence"),
        CheckConstraint(
            "(value_state = 'PRESENT' AND predicted_value IS NOT NULL AND btrim(predicted_value) <> '') OR "
            "(value_state <> 'PRESENT' AND predicted_value IS NULL)",
            name="ck_field_predictions_value",
        ),
        CheckConstraint(
            "source_bbox IS NULL OR (jsonb_typeof(source_bbox) = 'array' AND jsonb_array_length(source_bbox) = 4)",
            name="ck_field_predictions_bbox",
        ),
        CheckConstraint("source_bbox IS NULL OR source_page_id IS NOT NULL", name="ck_field_predictions_bbox_source"),
        Index("idx_field_predictions_document_job", "document_id", "job_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    document_id = Column(UUID(as_uuid=True), nullable=False)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    job_id = Column(UUID(as_uuid=True), nullable=False)
    field_name = Column(String(100), nullable=False)
    predicted_value = Column(Text, nullable=True)
    value_state = Column(String(50), nullable=False)
    confidence = Column(Numeric(5, 4), nullable=True)
    source_page_id = Column(UUID(as_uuid=True), nullable=True)
    source_bbox = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
