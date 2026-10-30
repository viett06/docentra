from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FieldUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field_name: str = Field(min_length=1, max_length=100)
    value: str | None = Field(default=None, max_length=500)
    value_state: Literal["PRESENT", "NOT_FOUND", "UNREADABLE", "NOT_APPLICABLE"]
    source_page_id: UUID | None = None
    reviewed: bool = False

    @model_validator(mode="after")
    def validate_value(self):
        if self.value_state == "PRESENT":
            if not self.value or not self.value.strip():
                raise ValueError("Trường có giá trị không được để trống")
            self.value = self.value.strip()
        elif self.value is not None:
            raise ValueError("Trường thiếu/không áp dụng phải có value=null")
        return self


class DocumentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)
    type_code: str = Field(min_length=1, max_length=50)
    title: str = Field(max_length=500)
    fields: list[FieldUpdate] = Field(max_length=20)


class VerifyRequest(BaseModel):
    version: int = Field(ge=1)
    identity_confirmed: Literal[True]


class ReasonRequest(BaseModel):
    version: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=1000)


class FieldView(BaseModel):
    field_name: str
    label: str
    field_type: str
    required: bool
    value: str | None
    value_state: str
    source_page_id: UUID | None
    review_status: str
    predicted_value: str | None
    confidence: float | None


class PageView(BaseModel):
    id: UUID
    page_order: int
    image_url: str


class DocumentView(BaseModel):
    id: UUID
    session_id: UUID
    employee_id: UUID
    employee_code: str
    employee_name: str
    type_code: str
    title: str
    review_status: str
    version: int
    identity_match: bool | None
    identity_note: str | None
    created_at: datetime
    verified_at: datetime | None
    pages: list[PageView]
    fields: list[FieldView]
