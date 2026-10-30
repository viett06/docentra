from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class DocumentField(Base):
    __tablename__ = "document_fields"

    __table_args__ = (
        ForeignKeyConstraint(
            ["prediction_id", "document_id", "field_name"],
            ["field_predictions.id", "field_predictions.document_id", "field_predictions.field_name"],
            name="fk_document_fields_prediction_field",
        ),
        ForeignKeyConstraint(
            ["document_id", "source_page_id"],
            ["document_pages.document_id", "document_pages.scan_page_id"],
            name="fk_document_fields_source_document",
        ),
        CheckConstraint("btrim(field_name) <> ''", name="ck_document_fields_field_name"),
        CheckConstraint(
            "value_state IN ('PRESENT', 'NOT_FOUND', 'UNREADABLE', 'NOT_APPLICABLE')",
            name="ck_document_fields_value_state",
        ),
        CheckConstraint(
            "review_status IN ('PENDING', 'CONFIRMED', 'CORRECTED')", name="ck_document_fields_review_status"
        ),
        CheckConstraint(
            "(value_state = 'PRESENT' AND value IS NOT NULL AND btrim(value) <> '') OR "
            "(value_state <> 'PRESENT' AND value IS NULL)",
            name="ck_document_fields_value",
        ),
        CheckConstraint(
            "(review_status = 'PENDING' AND reviewed_by IS NULL AND reviewed_at IS NULL) OR "
            "(review_status <> 'PENDING' AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="ck_document_fields_review_metadata",
        ),
        CheckConstraint(
            "source_bbox IS NULL OR (jsonb_typeof(source_bbox) = 'array' AND jsonb_array_length(source_bbox) = 4)",
            name="ck_document_fields_bbox",
        ),
        CheckConstraint("source_bbox IS NULL OR source_page_id IS NOT NULL", name="ck_document_fields_bbox_source"),
        Index("idx_document_fields_lookup", "field_name", "value", postgresql_where=text("value IS NOT NULL")),
    )

    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), primary_key=True)
    field_name = Column(String(100), primary_key=True)
    prediction_id = Column(UUID(as_uuid=True), nullable=True)
    value = Column(String(500), nullable=True)
    value_state = Column(String(50), nullable=False)
    source_page_id = Column(UUID(as_uuid=True), nullable=True)
    source_bbox = Column(JSONB, nullable=True)
    review_status = Column(String(50), nullable=False, default="PENDING", server_default=text("'PENDING'"))
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=func.now()
    )
