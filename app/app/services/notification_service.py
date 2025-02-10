#services/notification_service
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional

from config import settings

class NotificationService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _create_email_message(
        self, 
        to_email: str, 
        subject: str, 
        body: str
    ) -> MIMEMultipart:
        """
        Create email message
        
        Args:
            to_email (str): Recipient email
            subject (str): Email subject
            body (str): Email body
        
        Returns:
            MIMEMultipart: Prepared email message
        """
        msg = MIMEMultipart()
        msg['From'] = settings.EMAIL_USERNAME
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        return msg

    def send_email(
        self, 
        to_email: str, 
        subject: str, 
        body: str
    ) -> bool:
        """
        Send email using configured SMTP settings
        
        Args:
            to_email (str): Recipient email
            subject (str): Email subject
            body (str): Email body
        
        Returns:
            bool: Whether email was sent successfully
        """
        try:
            msg = self._create_email_message(to_email, subject, body)

            with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                server.starttls()
                server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
                server.send_message(msg)
            
            self.logger.info(f"Email sent to {to_email}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False

    def send_compliance_report_notification(
        self, 
        user_email: str, 
        report_data: Dict
    ) -> None:
        """
        Send compliance report notification
        
        Args:
            user_email (str): Recipient email
            report_data (Dict): Compliance report details
        """
        subject = "Compliance Report Analysis Complete"
        body = f"""
        <html>
        <body>
        <h2>Compliance Report Analysis</h2>
        <p>Score: {report_data['score']}%</p>
        <p>Status: {report_data['status']}</p>
        <p>Details: {report_data['details']}</p>
        </body>
        </html>
        """
        self.send_email(user_email, subject, body)

    def send_session_reminder(
        self, 
        user_email: str, 
        session_details: Dict
    ) -> None:
        """
        Send session booking reminder
        
        Args:
            user_email (str): Recipient email
            session_details (Dict): Session booking details
        """
        subject = "Consultation Session Reminder"
        body = f"""
        <html>
        <body>
        <h2>Consultation Session Details</h2>
        <p>Date: {session_details['date']}</p>
        <p>Time: {session_details['time']}</p>
        <p>Type: {session_details.get('type', 'Online')}</p>
        </body>
        </html>
        """
        self.send_email(user_email, subject, body)
