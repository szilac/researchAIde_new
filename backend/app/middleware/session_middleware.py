from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response, HTTPException, status
from uuid import UUID
from typing import Callable

from ..services import session_storage

# Paths that do not require session validation
EXCLUDED_PATHS = {
    "/docs", 
    "/openapi.json", 
    "/redoc", 
    "/api/v1/health/health",
}
# Endpoint for creating sessions (also excluded)
CREATE_SESSION_PATH = "/api/v1/sessions/"

class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        
        # Skip middleware for excluded paths and session creation
        if request.url.path in EXCLUDED_PATHS or \
           (request.method == "POST" and request.url.path == CREATE_SESSION_PATH):
            return await call_next(request)

        # Get session ID from header
        session_id_str = request.headers.get("X-Session-ID")
        if not session_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session ID header (X-Session-ID) missing"
            )

        # Validate UUID format
        try:
            session_id_uuid = UUID(session_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Session ID format"
            )

        # Validate session using the storage service (checks existence, status, expiry)
        session = session_storage.get_session(session_id_uuid)
        if session is None:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session"
            )

        # Attach valid session to request state
        request.state.session = session

        # Proceed with the request
        response = await call_next(request)
        return response 