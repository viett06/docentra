from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_session
from app.demo.fixtures import render
from app.model import Employee, User
from app.services.security import current_user, require_access

router = APIRouter(prefix="/demo", tags=["Synthetic demo"])


@router.get("/samples/{employee_id}/{type_code}/{page}")
def sample(
    employee_id: UUID,
    type_code: Literal["employment_contract", "degree", "practice_certificate", "unknown"],
    page: int,
    page_count: int = Query(default=1, ge=1, le=3),
    db: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    if not get_settings().DEMO_MODE:
        raise AppError(404, "NOT_FOUND", "Không có dữ liệu mẫu trong môi trường này.")
    require_access(db, user, employee_id, "capture")
    employee = db.get(Employee, employee_id)
    if not employee or not employee.employee_code.startswith("SYN-EMP-") or page not in range(1, page_count + 1):
        raise AppError(422, "INVALID_SAMPLE", "Chỉ tạo tài liệu demo cho nhân viên giả lập.")
    return Response(
        render(type_code, employee.employee_code, employee.full_name, page, page_count), media_type="image/png"
    )
