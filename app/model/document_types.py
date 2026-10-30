from sqlalchemy import Boolean, CheckConstraint, Column, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base
from app.model.timestamp import TimestampMixin


class DocumentType(TimestampMixin, Base):
    __tablename__ = "document_types"

    __table_args__ = (
        CheckConstraint("schema_version > 0", name="ck_document_types_schema_version"),
        CheckConstraint("jsonb_typeof(field_schema) = 'object'", name="ck_document_types_field_schema"),
    )

    code = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    schema_version = Column(Integer, nullable=False, default=1, server_default=text("1"))
    field_schema = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("TRUE"))
