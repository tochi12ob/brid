##models/user.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
from passlib.hash import bcrypt
from pydantic import BaseModel, EmailStr
from typing import Optional



class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255))
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    compliance_reports = relationship("ComplianceReport", back_populates="user")
    sessions = relationship("Session", back_populates="user")

    def verify_password(self, plain_password):
        return bcrypt.verify(plain_password, self.hashed_password)

    @classmethod
    def hash_password(cls, plain_password):
        return bcrypt.hash(plain_password)
    

class UserCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    password: str  # Plain password, will be hashed later
