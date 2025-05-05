from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from uuid import UUID
from typing import Optional

from ....services import session_storage
from ....models.session import ResearchSession, SessionStatus

router = APIRouter()

class SessionCreateRequest(BaseModel):
    user_id: Optional[str] = None

@router.post("/", response_model=ResearchSession, status_code=status.HTTP_201_CREATED)
async def create_new_session(request_data: SessionCreateRequest):
    """Creates a new research session."""
    new_session = ResearchSession(user_id=request_data.user_id)
    try:
        created_session = session_storage.create_session(new_session)
        return created_session
    except ValueError as e:
        # Should be rare with UUIDs, but handle just in case
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.get("/{session_id}", response_model=ResearchSession)
async def get_existing_session(session_id: UUID):
    """Retrieves an existing, active session by its ID."""
    session = session_storage.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Session not found or invalid"
        )
    return session

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_session(session_id: UUID):
    """Deletes a session by its ID."""
    deleted = session_storage.delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Session not found"
        )
    # No content to return for 204
    return None 