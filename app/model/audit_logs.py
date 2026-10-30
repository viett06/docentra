from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    __table_args__ = (
        CheckConstraint("outcome IN ('ALLOWED', 'DENIED', 'FAILED')", name="ck_audit_logs_outcome"),
        CheckConstraint("jsonb_typeof(metadata) = 'object'", name="ck_audit_logs_metadata"),
        Index("idx_audit_logs_resource_created_at", "resource_type", "resource_id", "created_at"),
        Index("idx_audit_logs_actor_created_at", "actor_id", "created_at"),
        Index("idx_audit_logs_request_id", "request_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    request_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    outcome = Column(String(50), nullable=False)
    audit_metadata = Column("metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
