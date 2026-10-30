from sqlalchemy import Boolean, CheckConstraint, Column, String, text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base
from app.model.timestamp import TimestampMixin


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"

    __table_args__ = (
        CheckConstraint("btrim(employee_code) <> ''", name="ck_employees_code_not_blank"),
        CheckConstraint("btrim(full_name) <> ''", name="ck_employees_name_not_blank"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    employee_code = Column(String(100), nullable=False, unique=True)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("TRUE"))
