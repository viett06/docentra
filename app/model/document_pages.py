from sqlalchemy import CheckConstraint, Column, ForeignKeyConstraint, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class DocumentPage(Base):
    __tablename__ = "document_pages"

    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "session_id"],
            ["documents.id", "documents.session_id"],
            name="fk_document_pages_document_session",
        ),
        ForeignKeyConstraint(
            ["scan_page_id", "session_id"],
            ["scan_pages.id", "scan_pages.session_id"],
            name="fk_document_pages_scan_page_session",
        ),
        UniqueConstraint("scan_page_id", name="uq_document_pages_scan_page"),
        UniqueConstraint(
            "document_id", "page_order", name="uq_document_pages_document_order", deferrable=True, initially="IMMEDIATE"
        ),
        CheckConstraint("page_order > 0", name="ck_document_pages_order"),
    )

    document_id = Column(UUID(as_uuid=True), primary_key=True)
    scan_page_id = Column(UUID(as_uuid=True), primary_key=True)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    page_order = Column(Integer, nullable=False)
