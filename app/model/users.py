from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base
from app.model.timestamp import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    __table_args__ = (CheckConstraint("role IN ('CAPTURE', 'REVIEWER', 'VIEWER', 'ADMIN')", name="ck_users_role"),)

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="CAPTURE", server_default=text("'CAPTURE'"))
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("TRUE"))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
