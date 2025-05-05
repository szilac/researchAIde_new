from typing import Dict, Optional, List
from uuid import UUID
from datetime import datetime, timedelta

from ..models.session import ResearchSession, SessionStatus
from ..config import SESSION_IDLE_TIMEOUT_SECONDS, SESSION_ABSOLUTE_TIMEOUT_SECONDS

# In-memory storage for sessions. Can be replaced with a persistent store.
_session_store: Dict[UUID, ResearchSession] = {}


def create_session(session: ResearchSession) -> ResearchSession:
    """Adds a new session to the store, calculating absolute expiry."""
    if session.session_id in _session_store:
        # Or update? For now, let's raise error or handle differently
        raise ValueError(f"Session ID {session.session_id} already exists.") 
    
    # Calculate absolute expiry time
    absolute_expiry = datetime.utcnow() + timedelta(seconds=SESSION_ABSOLUTE_TIMEOUT_SECONDS)
    session.expires_at = absolute_expiry
    # Ensure status is active and last activity is set initially
    session.status = SessionStatus.ACTIVE
    session.last_activity_at = datetime.utcnow()

    _session_store[session.session_id] = session
    return session


def get_session(session_id: UUID) -> Optional[ResearchSession]:
    """Retrieves a session, checks expiry, and updates activity time."""
    session = _session_store.get(session_id)

    # Check if session exists and is currently active
    if not session or session.status != SessionStatus.ACTIVE:
        return None

    now = datetime.utcnow()

    # Check absolute expiration
    if session.expires_at and now >= session.expires_at:
        session.status = SessionStatus.EXPIRED
        update_session(session_id, session) # Update status in store
        return None

    # Check idle expiration
    if now >= session.last_activity_at + timedelta(seconds=SESSION_IDLE_TIMEOUT_SECONDS):
        session.status = SessionStatus.EXPIRED
        update_session(session_id, session) # Update status in store
        return None

    # Session is valid, update last activity time
    session.last_activity_at = now
    update_session(session_id, session) # Update activity time in store
    
    return session


def update_session(session_id: UUID, updated_session_data: ResearchSession) -> Optional[ResearchSession]:
    """Updates an existing session."""
    if session_id in _session_store:
        _session_store[session_id] = updated_session_data
        return updated_session_data
    return None


def delete_session(session_id: UUID) -> bool:
    """Deletes a session by its ID. Returns True if deleted, False otherwise."""
    if session_id in _session_store:
        del _session_store[session_id]
        return True
    return False


def list_sessions() -> List[ResearchSession]:
    """Returns a list of all current sessions."""
    return list(_session_store.values()) 