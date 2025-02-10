from datetime import datetime, timedelta
import logging
from typing import List
from sqlalchemy.orm import Session
from ..models.compliance import ComplianceReport
from ..services.notification_service import NotificationService

class ComplianceEmailHandler:
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService()
        self.logger = logging.getLogger(__name__)

    def process_pending_results(self) -> None:
        """
        Process all pending compliance results that need to be sent
        """
        try:
            # Get reports that:
            # - Haven't had results sent
            # - Don't have a session booked
            # - Were created 3 days ago
            three_days_ago = datetime.utcnow() - timedelta(days=3)
            
            pending_reports = self.db.query(ComplianceReport).filter(
                ComplianceReport.results_sent == False,
                ComplianceReport.has_session_booked == False,
                ComplianceReport.created_at <= three_days_ago
            ).all()

            for report in pending_reports:
                try:
                    self.send_compliance_results(report)
                    
                    # Update report status
                    report.results_sent = True
                    report.results_send_date = datetime.utcnow()
                    self.db.commit()

                except Exception as e:
                    self.logger.error(f"Error processing report {report.id}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error in process_pending_results: {e}")
            self.db.rollback()

    def send_compliance_results(self, report: ComplianceReport) -> None:
        """
        Send compliance results email for a specific report
        """
        try:
            self.notification_service.send_compliance_report_notification(
                report.user.email,
                {
                    'score': report.overall_score,
                    'status': report.compliance_status,
                    'details': report.markdown_report,
                    'auto_sent': True
                }
            )
        except Exception as e:
            self.logger.error(f"Error sending results for report {report.id}: {e}")
            raise