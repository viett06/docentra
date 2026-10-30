from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class EmployeeView(BaseModel):
    id: UUID
    employee_code: str
    full_name: str
    counts: dict[str, int]


class FieldDefinition(BaseModel):
    label: str
    type: Literal["string", "date"]
    required: bool = False


class DocumentTypeView(BaseModel):
    code: str
    name: str
    fields: dict[str, FieldDefinition]


class CoverageView(BaseModel):
    type_code: str
    name: str
    counts: dict[str, int]


class DocumentListItem(BaseModel):
    id: UUID
    title: str
    employee_code: str
    employee_name: str
    type_code: str
    type_name: str
    review_status: str
    version: int
    page_count: int
    created_at: datetime
    verified_at: datetime | None


class DocumentListView(BaseModel):
    items: list[DocumentListItem]
    total: int
    limit: int
    offset: int


class DashboardView(BaseModel):
    employee_count: int
    page_count: int
    documents: dict[str, int]
    jobs: dict[str, int]
    demo_mode: bool


class AuditView(BaseModel):
    id: UUID
    action: str
    resource_type: str
    resource_id: UUID | None
    outcome: str
    created_at: datetime


class ReviewHistoryView(BaseModel):
    id: UUID
    version: int
    action: str
    changes: dict[str, Any]
    reason: str | None
    created_at: datetime
