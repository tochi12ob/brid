#models/session.py 
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
from pydantic import BaseModel, validator
from typing import Optional

class Session(Base):
    __tablename__ = "consultation_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    compliance_report_id = Column(Integer, ForeignKey('compliance_reports.id'), nullable=False)
    session_date = Column(DateTime, nullable=False)
    session_type = Column(String(50))  # "Online", "Phone", "In-Person"
    is_confirmed = Column(Boolean, default=False)
    is_completed = Column(Boolean, default=False)
    expert_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # New fields for rescheduling
    reschedule_count = Column(Integer, default=0)
    last_rescheduled = Column(DateTime, nullable=True)
    reschedule_reason = Column(Text, nullable=True)
    is_cancelled = Column(Boolean, default=False)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    compliance_report = relationship("ComplianceReport", back_populates="sessions")

class SessionBase(BaseModel):
    compliance_report_id: int
    session_date: datetime
    session_type: str
    
    @validator('session_type')
    def validate_session_type(cls, v):
        valid_types = {"Online", "Phone", "In-Person"}
        if v not in valid_types:
            raise ValueError(f"session_type must be one of {valid_types}")
        return v

class SessionCreate(SessionBase):
    is_confirmed: bool = False

class SessionUpdate(BaseModel):
    session_date: Optional[datetime] = None
    is_confirmed: Optional[bool] = None
    expert_notes: Optional[str] = None
    
    @validator('session_date')
    def validate_future_date(cls, v):
        if v and v < datetime.utcnow():
            raise ValueError("Session date must be in the future")
        return v

class SessionReschedule(BaseModel):
    new_session_date: datetime
    reschedule_reason: Optional[str] = None
    
    @validator('new_session_date')
    def validate_future_date(cls, v):
        if v < datetime.utcnow():
            raise ValueError("New session date must be in the future")
        return v

class SessionModel(SessionBase):
    id: int
    user_id: int
    is_confirmed: bool
    is_completed: bool
    expert_notes: Optional[str]
    created_at: datetime
    reschedule_count: Optional[int] = 0
    last_rescheduled: Optional[datetime] = None
    reschedule_reason: Optional[str] = None
    is_cancelled: Optional[bool] = False
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    last_modified: datetime
    
    class Config:
        from_attributes = True