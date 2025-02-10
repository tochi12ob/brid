#routes/compliance
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from typing import List
from ..services.compliance_service import ComplianceService
from ..models.compliance import ComplianceReport
from database import get_db
from sqlalchemy.orm import Session
from ..utils.file_handler import save_file
from config import Settings
from functools import lru_cache
import logging

router = APIRouter()

@lru_cache()
def get_settings():
    return Settings()

def get_compliance_service(settings: Settings = Depends(get_settings)) -> ComplianceService:
    """Initialize and return ComplianceService instance"""
    try:
        return ComplianceService()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize compliance service: {str(e)}"
        )

@router.post("/check-compliance")
async def check_compliance(
    files: List[UploadFile] = File(...),
    service: ComplianceService = Depends(get_compliance_service),
    db: Session = Depends(get_db)
):
    """Process uploaded files and check compliance"""
    try:
        # Validate file types
        allowed_types = {"application/pdf"}
        for file in files:
            if file.content_type not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {file.content_type}. Only PDF files are supported."
                )
        
        results = []
        for file in files:
            # Read file content
            file_content = await file.read()
            
            try:
                # Call analyze_policy with all required parameters
                user_id = 1  # Replace with actual user ID from auth system
                db_record = service.analyze_policy(
                    file_content=file_content,
                    user_id=user_id,
                    file_name=file.filename
                )
                
                # Create report record using the returned db_record
                report = ComplianceReport(**db_record)
                db.add(report)
                db.commit()
                db.refresh(report)
                
                results.append({
                    "file_name": file.filename,
                    "report_id": report.id,
                    "overall_score": report.overall_score,
                    "detailed_analysis": report.detailed_analysis,
                    "compliance_status": report.compliance_status,
                    "pdf_report_path": report.pdf_report
                })
                
            except Exception as e:
                logging.error(f"Error analyzing file {file.filename}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error analyzing file {file.filename}: {str(e)}"
                )
        
        return {
            "message": "Compliance check completed successfully",
            "results": results
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error processing compliance check: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing compliance check: {str(e)}"
        )