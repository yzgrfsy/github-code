from fastapi import APIRouter

from app.api.v1 import auth, billing, projects, tasks


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])

