# routes/user.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.file_service import FileService
from app.services.auth_service import get_current_user
from app.models.user import User
from database import get_db

user_router = APIRouter(prefix='/user')

@user_router.post("/book-session/{report_id}")
async def book_session(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    file_service = FileService(db)
    report = file_service.get_compliance_result(report_id)
    
    # Check if the report belongs to the current user
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this report")
        
    file_service.schedule_compliance_session(report)
    return {"message": "Session booked successfully"}
