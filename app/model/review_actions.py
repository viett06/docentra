from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class ReviewAction(Base):
    __tablename__ = "review_actions"

    __table_args__ = (
        UniqueConstraint("document_id", "document_version", name="uq_review_actions_document_version"),
        CheckConstraint("document_version > 0", name="ck_review_actions_document_version"),
        CheckConstraint(
            "action IN ('EDIT_FIELDS', 'CHANGE_TYPE', 'REGROUP_PAGES', 'CONFIRM_IDENTITY', "
            "'VERIFY', 'REOPEN', 'REJECT', 'ACCEPT_PROCESSING')",
            name="ck_review_actions_action",
        ),
        CheckConstraint("jsonb_typeof(changes) = 'object'", name="ck_review_actions_changes"),
        Index("idx_review_actions_actor_id", "actor_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    document_version = Column(Integer, nullable=False)
    action = Column(String(50), nullable=False)
    changes = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
