from sqlalchemy import (
    Column, 
    Integer, 
    String, 
    Float, 
    DateTime, 
    ForeignKey, 
    Text, 
    JSON,
    Boolean  # Add this import
)
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class ComplianceReport(Base):
    __tablename__ = "compliance_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    file_name = Column(String(255))
    overall_score = Column(Float, nullable=False)
    detailed_analysis = Column(JSON, nullable=True)
    markdown_report = Column(Text, nullable=True)  
    pdf_report = Column(Text, nullable=True)  
    compliance_status = Column(String(50))  
    created_at = Column(DateTime, default=datetime.utcnow)
    results_sent = Column(Boolean, default=False)
    results_send_date = Column(DateTime, nullable=True)
    has_session_booked = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="compliance_reports")
    sessions = relationship("Session", back_populates="compliance_report")

    @staticmethod
    def calculate_compliance_status(score: float) -> str:
        if score >= 80:
            return "Compliant"
        elif score >= 60:
            return "Partially Compliant"
        else:
            return "Non-Compliant"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if hasattr(self, 'overall_score'):
            self.compliance_status = self.calculate_compliance_status(self.overall_score)