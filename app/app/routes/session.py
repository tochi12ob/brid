#routes/session.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.services.session_service import SessionService
from app.models.session import SessionModel, SessionCreate  # Import Pydantic models
from database import get_db
from app.services.auth_service import get_current_user
from app.models.user import User
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=SessionModel)
def create_session(
    session: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new session for the user
    """
    session_service = SessionService(db)
    return session_service.book_consultation_session(
        user=current_user,
        report_id=session.compliance_report_id,  # Changed from report_id to compliance_report_id
        session_date=session.session_date,
        session_type=session.session_type
    )

@router.get("/", response_model=List[SessionModel])
def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    completed: Optional[bool] = None
):
    """
    Retrieve all sessions for the current user, optionally filter by completion status
    """
    session_service = SessionService(db)
    return session_service.get_user_sessions(current_user, completed)

@router.put("/{session_id}/complete", response_model=SessionModel)
def complete_session(
    session_id: int,
    expert_notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a session as completed, optionally with expert notes
    """
    session_service = SessionService(db)
    try:
        return session_service.complete_session(session_id, current_user, expert_notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{session_id}", response_model=SessionModel)
def get_session_by_id(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve a specific session by its ID
    """
    session_service = SessionService(db)
    session = session_service.get_session_by_id(session_id, current_user)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# Pydantic model for request validation
class SessionReschedule(BaseModel):
    new_session_date: datetime
    reason: Optional[str] = None

@router.put("/{session_id}/reschedule", response_model=SessionModel)
def reschedule_session(
    session_id: int,
    reschedule_data: SessionReschedule,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reschedule an existing session to a new date/time.
    
    Args:
        session_id: ID of the session to reschedule
        reschedule_data: New session date and optional reason
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        Updated session details
        
    Raises:
        HTTPException: If session is not found, already completed, or user is not authorized
    """
    session_service = SessionService(db)
    
    # Get existing session
    session = session_service.get_session_by_id(session_id, current_user)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if session belongs to current user
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this session")
        
    # Check if session is already completed
    if session.completed:
        raise HTTPException(status_code=400, detail="Cannot reschedule completed session")
        
    # Check if new date is in the future
    if reschedule_data.new_session_date <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="New session date must be in the future")
    
    try:
        # Update session with new date
        updated_session = session_service.update_session(
            session_id=session_id,
            user=current_user,
            updates={
                "session_date": reschedule_data.new_session_date,
                "reschedule_reason": reschedule_data.reason,
                "last_modified": datetime.utcnow()
            }
        )
        
        return updated_session
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))