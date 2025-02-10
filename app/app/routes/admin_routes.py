from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from fastapi.responses import FileResponse
import os
from database import get_db
from ..models.compliance import ComplianceReport
from ..services.compliance_service import ComplianceService
from config import Settings
from functools import lru_cache

router = APIRouter()

@lru_cache()
def get_settings():
    return Settings()

@router.get("/reports")
async def get_reports(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    """Get all compliance reports with optional date filtering"""
    try:
        query = db.query(ComplianceReport)

        # Apply date filters if provided
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(ComplianceReport.created_at >= start)
        
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(ComplianceReport.created_at <= end)

        # Order by most recent first
        query = query.order_by(ComplianceReport.created_at.desc())
        
        # Apply pagination
        reports = query.offset(skip).limit(limit).all()

        return [{
            "id": report.id,
            "user_id": report.user_id,
            "file_name": report.file_name,
            "overall_score": report.overall_score,
            "compliance_status": report.compliance_status,
            "created_at": report.created_at,
            "pdf_report": report.pdf_report
        } for report in reports]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving reports: {str(e)}"
        )

@router.get("/reports/{report_id}")
async def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    """Get a specific compliance report by ID"""
    try:
        report = db.query(ComplianceReport).filter(ComplianceReport.id == report_id).first()
        
        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"Report with ID {report_id} not found"
            )

        return {
            "id": report.id,
            "user_id": report.user_id,
            "file_name": report.file_name,
            "overall_score": report.overall_score,
            "detailed_analysis": report.detailed_analysis,
            "compliance_status": report.compliance_status,
            "created_at": report.created_at,
            "pdf_report": report.pdf_report
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving report: {str(e)}"
        )

@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    """Download a specific report's PDF"""
    try:
        report = db.query(ComplianceReport).filter(ComplianceReport.id == report_id).first()
        
        if not report or not report.pdf_report:
            raise HTTPException(
                status_code=404,
                detail=f"Report PDF not found for ID {report_id}"
            )

        pdf_path = report.pdf_report
        
        if not os.path.exists(pdf_path):
            raise HTTPException(
                status_code=404,
                detail="PDF file not found on server"
            )

        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"compliance_report_{report_id}.pdf"
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading report: {str(e)}"
        )

@router.get("/reports/batch-download")
async def batch_download_reports(
    report_ids: List[int],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    """Download multiple reports as ZIP"""
    try:
        from zipfile import ZipFile
        import tempfile
        
        # Create a temporary ZIP file
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with ZipFile(tmp_zip.name, 'w') as zip_file:
                for report_id in report_ids:
                    report = db.query(ComplianceReport).filter(ComplianceReport.id == report_id).first()
                    if report and report.pdf_report and os.path.exists(report.pdf_report):
                        zip_file.write(
                            report.pdf_report, 
                            f"compliance_report_{report_id}.pdf"
                        )

            return FileResponse(
                tmp_zip.name,
                media_type="application/zip",
                filename="compliance_reports.zip"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating batch download: {str(e)}"
        )