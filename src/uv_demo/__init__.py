from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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


class HealthResponse(BaseModel):
    status: str
    message: str
    system: str


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    # Tự động tạo cấu trúc bảng cơ sở dữ liệu nếu chưa tồn tại
    Base.metadata.create_all(bind=engine)
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


# Gắn các bộ định tuyến theo đúng 7 phần đặc tả chức năng LMS
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(courses_router)
app.include_router(assignments_router)
app.include_router(quizzes_router)
app.include_router(forum_router)
app.include_router(admin_router)


@app.get("/", response_model=HealthResponse, tags=["Sức khỏe hệ thống"])
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
