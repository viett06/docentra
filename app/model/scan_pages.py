from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ScanPage(Base):
    __tablename__ = "scan_pages"

    __table_args__ = (
        UniqueConstraint("session_id", "client_page_id", name="uq_scan_pages_session_client"),
        UniqueConstraint("id", "session_id", name="uq_scan_pages_id_session"),
        UniqueConstraint(
            "session_id", "page_order", name="uq_scan_pages_session_order", deferrable=True, initially="IMMEDIATE"
        ),
        CheckConstraint("page_order IS NULL OR page_order > 0", name="ck_scan_pages_order"),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_scan_pages_sha256"),
        CheckConstraint("byte_size > 0 AND width > 0 AND height > 0", name="ck_scan_pages_dimensions"),
        CheckConstraint("mime_type IN ('image/jpeg', 'image/png', 'image/webp')", name="ck_scan_pages_mime_type"),
        CheckConstraint(
            "(discarded_at IS NULL AND page_order IS NOT NULL) OR (discarded_at IS NOT NULL AND page_order IS NULL)",
            name="ck_scan_pages_discarded_order",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    session_id = Column(UUID(as_uuid=True), ForeignKey("scan_sessions.id"), nullable=False)
    client_page_id = Column(UUID(as_uuid=True), nullable=False)
    page_order = Column(Integer, nullable=True)
    original_storage_key = Column(String(1000), nullable=False, unique=True)
    sha256 = Column(String(64), nullable=False)
    byte_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    discarded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
