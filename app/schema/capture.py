from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employee_id: UUID
    client_session_id: UUID


class PageReceipt(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    client_page_id: UUID
    page_order: int
    sha256: str
    byte_size: int
    mime_type: str
    width: int
    height: int


class ManifestPage(BaseModel):
    id: UUID
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class FinalizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)
    pages: list[ManifestPage] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def unique_pages(self):
        if len({page.id for page in self.pages}) != len(self.pages):
            raise ValueError("Danh sách trang bị trùng")
        return self


class DocumentGroup(BaseModel):
    title: str = Field(default="", max_length=500)
    page_ids: list[UUID] = Field(min_length=1, max_length=30)


class ProcessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: UUID
    groups: list[DocumentGroup] = Field(min_length=1, max_length=20)


class JobView(BaseModel):
    id: UUID
    status: str
    attempt_count: int
    max_attempts: int
    error_code: str | None
    created_at: datetime
    finished_at: datetime | None


class CaptureSessionView(BaseModel):
    id: UUID
    employee_id: UUID
    status: str
    version: int
    pages: list[PageReceipt]
    job: JobView | None
    document_ids: list[UUID]
