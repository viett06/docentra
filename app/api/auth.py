import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_session
from app.model import AuthSession, User
from app.schema.auth import AuthView, LoginRequest, UserView
from app.services.audit import audit
from app.services.security import current_user, digest, password_hasher, utcnow, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])
_attempts: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()
_dummy_hash = password_hasher.hash(secrets.token_urlsafe(24))


@router.post("/login", response_model=AuthView)
def login(body: LoginRequest, request: Request, response: Response, session: Session = Depends(get_session)):
    email = body.email.strip().lower()
    key = digest((request.client.host if request.client else "local") + "\0" + email)
    with _lock:
        recent = _attempts[key]
        while recent and recent[0] < time.monotonic() - 300:
            recent.popleft()
        if len(recent) >= 8:
            raise AppError(429, "LOGIN_THROTTLED", "Quá nhiều lần thử. Vui lòng đợi 5 phút.")
        recent.append(time.monotonic())
    user = session.scalar(select(User).where(User.email == email))
    valid = verify_password(user.password_hash if user else _dummy_hash, body.password)
    if not user or not valid or not user.is_active or user.deleted_at is not None:
        audit(session, None, "auth.login_failed", "authentication", outcome="DENIED")
        session.commit()
        raise AppError(401, "LOGIN_FAILED", "Email hoặc mật khẩu không đúng.")
    with _lock:
        _attempts.pop(key, None)
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    expires = utcnow() + timedelta(hours=get_settings().SESSION_HOURS)
    session.add(AuthSession(user_id=user.id, token_hash=digest(token), csrf_hash=digest(csrf), expires_at=expires))
    audit(session, user, "auth.login", "user", user.id)
    session.commit()
    for name, value, http_only in [("docentra_session", token, True), ("docentra_csrf", csrf, False)]:
        response.set_cookie(
            name,
            value,
            httponly=http_only,
            secure=get_settings().COOKIE_SECURE,
            samesite="strict",
            max_age=get_settings().SESSION_HOURS * 3600,
            path="/",
        )
    return AuthView(user=UserView.model_validate(user), csrf_token=csrf, expires_at=expires)


@router.get("/me", response_model=AuthView)
def me(request: Request, user: User = Depends(current_user)):
    csrf = request.cookies.get("docentra_csrf", "")
    if not secrets.compare_digest(digest(csrf), request.state.auth.csrf_hash):
        raise AppError(401, "AUTH_REQUIRED", "Vui lòng đăng nhập lại.")
    return AuthView(user=UserView.model_validate(user), csrf_token=csrf, expires_at=request.state.auth.expires_at)


@router.post("/logout")
def logout(
    request: Request, response: Response, user: User = Depends(current_user), session: Session = Depends(get_session)
):
    request.state.auth.revoked_at = utcnow()
    audit(session, user, "auth.logout", "user", user.id)
    session.commit()
    response.delete_cookie("docentra_session", path="/")
    response.delete_cookie("docentra_csrf", path="/")
    return {"ok": True}
