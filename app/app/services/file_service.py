from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
import os
from app.models.compliance import ComplianceReport
from app.models.session import Session as SessionModel
from config import get_settings

class FileService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.uploads_dir = self.settings.UPLOADS_DIR

    def get_compliance_result(self, result_id: int) -> ComplianceReport:
        """
        Retrieve a compliance report by its ID
        """
        report = self.db.query(ComplianceReport).filter(
            ComplianceReport.id == result_id
        ).first()
        
        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"Compliance report with ID {result_id} not found"
            )
        
        return report

    def save_file(self, filename: str, file_content: bytes) -> str:
        """
        Save an uploaded file to the filesystem
        """
        # Validate file type
        file_extension = os.path.splitext(filename)[1].lower()
        if not self._is_allowed_file_type(file_extension):
            raise HTTPException(
                status_code=400,
                detail="File type not allowed"
            )
            
        # Validate file size
        if len(file_content) > self.settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {self.settings.MAX_FILE_SIZE} bytes"
            )
            
        file_path = os.path.join(self.uploads_dir, filename)
        try:
            with open(file_path, 'wb') as f:
                f.write(file_content)
            return file_path
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error saving file: {str(e)}"
            )

    def _is_allowed_file_type(self, file_extension: str) -> bool:
        """Check if the file type is allowed"""
        extension_to_mime = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain'
        }
        return extension_to_mime.get(file_extension) in self.settings.ALLOWED_FILE_TYPES

    def create_compliance_report(self, user_id: int, filename: str, score: float, analysis: str) -> ComplianceReport:
        """Create a new compliance report"""
        status = self._determine_compliance_status(score)
        
        report = ComplianceReport(
            user_id=user_id,
            file_name=filename,
            overall_score=score,
            detailed_analysis=analysis,
            compliance_status=status
        )
        
        try:
            self.db.add(report)
            self.db.commit()
            self.db.refresh(report)
            return report
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error creating compliance report: {str(e)}"
            )

    def _determine_compliance_status(self, score: float) -> str:
        """Determine compliance status based on score"""
        if score >= 80:
            return "Compliant"
        elif score >= 60:
            return "Partially Compliant"
        else:
            return "Non-Compliant"

    def schedule_compliance_session(self, report: ComplianceReport):
        """Schedule a compliance session for a given report"""
        try:
            session = SessionModel(
                user_id=report.user_id,
                compliance_report_id=report.id,
                session_date=datetime.utcnow(),
                session_type="Online",
                is_confirmed=False
            )
            
            self.db.add(session)
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error scheduling compliance session: {str(e)}"
            )

    def delete_compliance_report(self, report_id: int):
        """Delete a compliance report and its associated file"""
        report = self.get_compliance_result(report_id)
        
        try:
            if report.file_name:
                file_path = os.path.join(self.uploads_dir, report.file_name)
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            self.db.delete(report)
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting compliance report: {str(e)}"
            )