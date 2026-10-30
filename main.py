import logging
from uuid import uuid4

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import auth, capture, catalog, demo, documents
from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_session
from app.services import storage

logger = logging.getLogger("docentra.api")
app = FastAPI(title="Docentra", description="Synthetic MVP · capture, verify and retrieve HR records", version="0.1.0")


@app.middleware("http")
async def request_policy(request: Request, call_next):
    request.state.request_id = str(uuid4())
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
            return JSONResponse(
                {"error": {"code": "ORIGIN_DENIED", "message": "Nguồn yêu cầu không hợp lệ."}}, status_code=403
            )
    if request.url.path.endswith("/pages") and request.method == "POST":
        length = request.headers.get("content-length")
        try:
            valid_length = length is not None and 0 < int(length) <= get_settings().MAX_UPLOAD_BYTES + 64 * 1024
        except ValueError:
            valid_length = False
        if not valid_length:
            return JSONResponse(
                {"error": {"code": "UPLOAD_LIMIT", "message": "Ảnh vượt quá giới hạn hoặc không có kích thước gửi."}},
                status_code=413,
            )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    return response


def error_response(request, status, code, message):
    return JSONResponse(
        {"error": {"code": code, "message": message, "request_id": getattr(request.state, "request_id", None)}},
        status_code=status,
    )


@app.exception_handler(AppError)
async def app_error(request, exc):
    return error_response(request, exc.status, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    return error_response(
        request, 422, "VALIDATION_ERROR", "Dữ liệu chưa hợp lệ. Vui lòng kiểm tra các trường đã nhập."
    )


@app.exception_handler(IntegrityError)
async def conflict(request, exc):
    return error_response(
        request, 409, "DATA_CONFLICT", "Dữ liệu đã thay đổi hoặc bị trùng. Vui lòng tải lại và thử lại."
    )


@app.exception_handler(BotoCoreError)
@app.exception_handler(ClientError)
async def storage_error(request, exc):
    logger.warning("storage_unavailable request_id=%s error=%s", request.state.request_id, type(exc).__name__)
    return error_response(
        request,
        503,
        "STORAGE_UNAVAILABLE",
        "Kho lưu trữ tạm thời chưa sẵn sàng. Dữ liệu chưa gửi cần được giữ ở tab này để thử lại.",
    )


@app.exception_handler(Exception)
async def unexpected(request, exc):
    logger.error("request_failed request_id=%s error=%s", request.state.request_id, type(exc).__name__)
    return error_response(request, 500, "INTERNAL_ERROR", "Không thể hoàn tất thao tác. Vui lòng thử lại.")


@app.get("/health")
def health():
    return {"status": "ok", "app": "Docentra"}


@app.get("/ready")
def ready(db: Session = Depends(get_session)):
    checks = {"database": False, "storage": False}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
        storage.client().head_bucket(Bucket=get_settings().S3_BUCKET)
        checks["storage"] = True
    except Exception:
        pass
    return JSONResponse(
        {"status": "ready" if all(checks.values()) else "not_ready", "checks": checks},
        status_code=200 if all(checks.values()) else 503,
    )


for router in [auth.router, catalog.router, capture.router, documents.router, demo.router]:
    app.include_router(router, prefix="/api/v1")

if get_settings().FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=get_settings().FRONTEND_DIR, html=True), name="web")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True, access_log=False)
