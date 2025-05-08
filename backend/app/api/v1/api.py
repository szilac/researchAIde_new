from fastapi import APIRouter

from .endpoints import health, sessions, papers, llm, pdf, orchestration

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
api_router.include_router(llm.router, prefix="/llm", tags=["llm_utilities"])
api_router.include_router(pdf.router, prefix="/pdf", tags=["pdf_utilities"])
api_router.include_router(orchestration.router, prefix="/orchestration", tags=["orchestration_workflows"]) 