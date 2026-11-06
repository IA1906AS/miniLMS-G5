from uv_demo.routers.admin import router as admin_router
from uv_demo.routers.assignments import router as assignments_router
from uv_demo.routers.auth import router as auth_router
from uv_demo.routers.courses import router as courses_router
from uv_demo.routers.forum import router as forum_router
from uv_demo.routers.quizzes import router as quizzes_router
from uv_demo.routers.users import router as users_router

__all__ = [
    "auth_router",
    "users_router",
    "courses_router",
    "assignments_router",
    "quizzes_router",
    "forum_router",
    "admin_router",
]
