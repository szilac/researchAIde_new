from fastapi import APIRouter

from .endpoints import health, sessions, papers

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(papers.router, prefix="/papers", tags=["papers"]) 