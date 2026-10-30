import hashlib
import secrets
from datetime import UTC, datetime

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import SessionLocal, get_session
from app.model import AuthSession, EmployeeAccess, User
from app.services.audit import audit

password_hasher = PasswordHasher()
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def utcnow():
    return datetime.now(UTC)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def verify_password(encoded: str, password: str) -> bool:
    try:
        return password_hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def current_user(request: Request, session: Session = Depends(get_session)) -> User:
    token = request.cookies.get("docentra_session", "")
    auth = (
        session.scalar(
            select(AuthSession).where(
                AuthSession.token_hash == digest(token),
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > utcnow(),
            )
        )
        if token
        else None
    )
    user = session.get(User, auth.user_id) if auth else None
    if not user or not user.is_active or user.deleted_at is not None:
        raise AppError(401, "AUTH_REQUIRED", "Vui lòng đăng nhập để tiếp tục.")
    if request.method not in SAFE_METHODS:
        supplied = request.headers.get("X-CSRF-Token", "")
        if not secrets.compare_digest(auth.csrf_hash, digest(supplied)):
            raise AppError(403, "CSRF_FAILED", "Phiên thao tác không hợp lệ. Vui lòng tải lại trang.")
    request.state.auth = auth
    return user


def deny(user, resource_type: str, resource_id=None):
    # Persist denials without committing any pending changes in the request transaction.
    with SessionLocal() as session:
        audit(session, user, "access.denied", resource_type, resource_id, outcome="DENIED")
        session.commit()
    raise AppError(404, "NOT_FOUND", "Không tìm thấy dữ liệu hoặc bạn chưa được cấp quyền.")


def require_access(session, user, employee_id, permission: str):
    grant = session.get(EmployeeAccess, (employee_id, user.id))
    roles = {
        "capture": {"CAPTURE", "REVIEWER"},
        "review": {"REVIEWER"},
        "view": {"VIEWER", "REVIEWER"},
    }
    allowed = grant and user.role in roles[permission]
    if permission == "view":
        allowed = allowed and (grant.can_view or grant.can_review)
    else:
        allowed = allowed and getattr(grant, f"can_{permission}")
    if not allowed:
        deny(user, "employee", employee_id)
    return grant
