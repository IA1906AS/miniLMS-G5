from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from uv_demo.database import Base, engine
from uv_demo.routers import (
    admin_router,
    assignments_router,
    auth_router,
    courses_router,
    forum_router,
    quizzes_router,
    users_router,
)
from uv_demo.seed import run_seed_if_needed

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


class HealthResponse(BaseModel):
    status: str
    message: str
    system: str


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    # Tự động tạo cấu trúc bảng cơ sở dữ liệu nếu chưa tồn tại
    Base.metadata.create_all(bind=engine)
    # Tự động nạp dữ liệu mẫu ban đầu (admin, gv, sv, khóa học, quiz)
    run_seed_if_needed()
    yield


app = FastAPI(
    title="Hệ thống Quản lý Học tập (LMS - Learning Management System)",
    description=(
        "Hệ thống LMS hoàn chỉnh với kiến trúc phân quyền nghiêm ngặt "
        "(Sinh viên SV, Giảng viên GV, Quản trị viên QT), chống leo thang đặc quyền "
        "dọc và ngang, bảo mật theo chuẩn OWASP."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Cấu hình CORS an toàn theo chuẩn bảo mật OWASP (không dùng wildcard *)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_hardening_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Tăng cường bảo vệ ứng dụng Web & Triệt tiêu Information Disclosure."""
    response = await call_next(request)
    # 1. Chống Clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    # 2. Chống MIME-type confusion / sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # 3. Kích hoạt bộ lọc XSS của trình duyệt
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # 4. Kiểm soát referrer an toàn
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # 5. Khóa quyền thiết bị nhạy cảm
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # 6. Chống Server Fingerprinting (xóa header Server nếu có)
    if "server" in response.headers:
        del response.headers["server"]
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    """Ngăn chặn rò rỉ mã nguồn, cấu trúc DB hoặc tracebacks (CWE-200)."""
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None) or {},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Đã xảy ra sự cố kỹ thuật trên máy chủ. Thông tin hệ thống đã được bảo vệ."
        },
    )


# Gắn các bộ định tuyến theo đúng 7 phần đặc tả chức năng LMS
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(courses_router)
app.include_router(assignments_router)
app.include_router(quizzes_router)
app.include_router(forum_router)
app.include_router(admin_router)

# Mount thư mục tĩnh để phục vụ Web Client
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", tags=["Giao diện & Sức khỏe"])
def root_or_client(request: Request) -> Response:
    accept_header = request.headers.get("accept", "")
    index_file = STATIC_DIR / "index.html"
    # Nếu client yêu cầu HTML (trình duyệt web), phục vụ trang giao diện Web Client
    if "text/html" in accept_header and index_file.exists():
        return FileResponse(index_file)

    # Mặc định trả về JSON HealthResponse cho các API test / health checks
    return JSONResponse(
        content={
            "status": "ok",
            "message": "Hệ thống LMS đang hoạt động bình thường",
            "system": "FastAPI + uv + SQLite/SQLAlchemy",
        }
    )


@app.get("/app", include_in_schema=False)
def serve_app_direct() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/login", include_in_schema=False)
def serve_login_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/register", include_in_schema=False)
def serve_register_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "register.html")


@app.get("/api/health", response_model=HealthResponse, tags=["Sức khỏe hệ thống"])
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        message="Hệ thống LMS đang hoạt động bình thường",
        system="FastAPI + uv + SQLite/SQLAlchemy",
    )


def main() -> None:
    import uvicorn

    # reload=False để đảm bảo tiêu chuẩn bảo mật cho môi trường sản xuất (Semgrep rule)
    uvicorn.run("uv_demo:app", host="127.0.0.1", port=8000, reload=False)
