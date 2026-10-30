from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class EmployeeAccess(Base):
    __tablename__ = "employee_access"

    __table_args__ = (
        CheckConstraint("can_capture OR can_review OR can_view", name="ck_employee_access_has_permission"),
        Index("idx_employee_access_user_id", "user_id"),
    )

    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    can_capture = Column(Boolean, nullable=False, default=False, server_default=text("FALSE"))
    can_review = Column(Boolean, nullable=False, default=False, server_default=text("FALSE"))
    can_view = Column(Boolean, nullable=False, default=False, server_default=text("FALSE"))
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
