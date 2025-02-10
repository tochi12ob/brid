import logging
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.session import Session as SessionModel
from ..models.user import User
from ..models.compliance import ComplianceReport
from .notification_service import NotificationService

class SessionService:
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService()
        self.logger = logging.getLogger(__name__)

    def book_consultation_session(
        self, 
        user: User, 
        report_id: int, 
        session_date: datetime,
        session_type: Optional[str] = "Online"
    ) -> SessionModel:
        """
        Book a consultation session and update the compliance report status
        
        Args:
            user (User): User booking the session
            report_id (int): Related compliance report ID
            session_date (datetime): Proposed session date
            session_type (Optional[str]): Type of session
        
        Returns:
            SessionModel: Created session
        """
        try:
            # Validate report belongs to user
            report = self.db.query(ComplianceReport).filter(
                ComplianceReport.id == report_id, 
                ComplianceReport.user_id == user.id
            ).first()

            if not report:
                raise ValueError("Report not found")

            # Validate session date
            if session_date < datetime.utcnow():
                raise ValueError("Session date cannot be in the past")

            # Update report to indicate session is booked
            report.has_session_booked = True

            # Create new session
            new_session = SessionModel(
                user_id=user.id,
                compliance_report_id=report_id,
                session_date=session_date,
                session_type=session_type,
                is_confirmed=False
            )

            self.db.add(new_session)
            self.db.commit()
            self.db.refresh(new_session)

            # Send session booking notification
            self.notification_service.send_session_reminder(
                user.email, 
                {
                    'date': session_date.strftime("%Y-%m-%d"),
                    'time': session_date.strftime("%H:%M"),
                    'type': session_type
                }
            )

            return new_session

        except Exception as e:
            self.logger.error(f"Session booking error: {e}")
            self.db.rollback()
            raise

    def get_user_sessions(
        self,
        user: User,
        completed: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[SessionModel]:
        """
        Get all sessions for a user with optional filters
        
        Args:
            user (User): User to get sessions for
            completed (Optional[bool]): Filter by completion status
            start_date (Optional[datetime]): Filter sessions after this date
            end_date (Optional[datetime]): Filter sessions before this date
        
        Returns:
            List[SessionModel]: List of matching sessions
        """
        try:
            query = self.db.query(SessionModel).filter(SessionModel.user_id == user.id)

            if completed is not None:
                query = query.filter(SessionModel.is_completed == completed)

            if start_date:
                query = query.filter(SessionModel.session_date >= start_date)

            if end_date:
                query = query.filter(SessionModel.session_date <= end_date)

            return query.order_by(SessionModel.session_date.desc()).all()

        except Exception as e:
            self.logger.error(f"Error fetching user sessions: {e}")
            raise

    def get_session_by_id(self, session_id: int, user: User) -> Optional[SessionModel]:
        """
        Get a specific session by ID
        
        Args:
            session_id (int): ID of the session to retrieve
            user (User): User requesting the session
        
        Returns:
            Optional[SessionModel]: Session if found and belongs to user, None otherwise
        """
        try:
            return self.db.query(SessionModel).filter(
                SessionModel.id == session_id,
                SessionModel.user_id == user.id
            ).first()

        except Exception as e:
            self.logger.error(f"Error fetching session {session_id}: {e}")
            raise

    def complete_session(
        self, 
        session_id: int, 
        user: User, 
        expert_notes: Optional[str] = None
    ) -> SessionModel:
        """
        Mark a consultation session as completed
        
        Args:
            session_id (int): ID of the session to be marked as completed
            user (User): User completing the session
            expert_notes (Optional[str]): Notes provided by the expert
        
        Returns:
            SessionModel: Updated session
        """
        try:
            session = self.get_session_by_id(session_id, user)

            if not session:
                raise ValueError("Session not found or does not belong to the user")

            if session.is_completed:
                raise ValueError("Session has already been marked as completed")

            if not session.is_confirmed:
                raise ValueError("Cannot complete unconfirmed session")

            session.is_completed = True
            session.completed_at = datetime.utcnow()
            if expert_notes:
                session.expert_notes = expert_notes

            self.db.commit()
            self.db.refresh(session)

            self.notification_service.send_session_completion_notification(
                user.email,
                {
                    'session_id': session_id,
                    'completion_date': session.completed_at.strftime("%Y-%m-%d %H:%M"),
                    'notes': expert_notes or "No additional notes provided."
                }
            )

            return session

        except Exception as e:
            self.logger.error(f"Session completion error: {e}")
            self.db.rollback()
            raise

    def update_session(
        self,
        session_id: int,
        user: User,
        updates: Dict
    ) -> SessionModel:
        """
        Update session details, with enhanced support for rescheduling
        
        Args:
            session_id (int): ID of the session to update
            user (User): User requesting the update
            updates (Dict): Dictionary of fields to update
        
        Returns:
            SessionModel: Updated session
            
        Raises:
            ValueError: If session is not found, completed, or update is invalid
        """
        try:
            session = self.get_session_by_id(session_id, user)

            if not session:
                raise ValueError("Session not found or does not belong to the user")

            if session.is_completed:
                raise ValueError("Cannot modify completed session")

            if session.is_cancelled:
                raise ValueError("Cannot modify cancelled session")

            # Extended set of allowed fields
            allowed_fields = {
                'session_date', 
                'session_type', 
                'is_confirmed',
                'reschedule_reason',
                'last_modified'
            }

            previous_date = None
            for field, value in updates.items():
                if field in allowed_fields:
                    if field == 'session_date':
                        if value < datetime.utcnow():
                            raise ValueError("Session date cannot be in the past")
                        
                        # Store the previous date for notification
                        previous_date = session.session_date
                        
                        # Track rescheduling
                        session.reschedule_count = (session.reschedule_count or 0) + 1
                        session.last_rescheduled = datetime.utcnow()
                    
                    setattr(session, field, value)

            # Update last modified timestamp
            session.last_modified = datetime.utcnow()

            self.db.commit()
            self.db.refresh(session)

            # Send notification if date was changed
            if previous_date:
                self.notification_service.send_session_update_notification(
                    user.email,
                    {
                        'session_id': session_id,
                        'previous_date': previous_date.strftime("%Y-%m-%d %H:%M"),
                        'new_date': updates['session_date'].strftime("%Y-%m-%d %H:%M"),
                        'reason': updates.get('reschedule_reason', 'No reason provided'),
                        'reschedule_count': session.reschedule_count
                    }
                )

            return session

        except Exception as e:
            self.logger.error(f"Session update error: {e}")
            self.db.rollback()
            raise

    def cancel_session(
        self,
        session_id: int,
        user: User,
        cancellation_reason: Optional[str] = None
    ) -> SessionModel:
        """
        Cancel a session
        
        Args:
            session_id (int): ID of the session to cancel
            user (User): User requesting the cancellation
            cancellation_reason (Optional[str]): Reason for cancellation
        
        Returns:
            SessionModel: Cancelled session
        """
        try:
            session = self.get_session_by_id(session_id, user)

            if not session:
                raise ValueError("Session not found or does not belong to the user")

            if session.is_completed:
                raise ValueError("Cannot cancel completed session")

            if session.is_cancelled:
                raise ValueError("Session is already cancelled")

            # Get the associated compliance report
            report = self.db.query(ComplianceReport).filter(
                ComplianceReport.id == session.compliance_report_id
            ).first()

            if report:
                report.has_session_booked = False

            session.is_cancelled = True
            session.cancellation_reason = cancellation_reason
            session.cancelled_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(session)

            self.notification_service.send_session_cancellation_notification(
                user.email,
                {
                    'session_id': session_id,
                    'cancellation_date': session.cancelled_at.strftime("%Y-%m-%d %H:%M"),
                    'reason': cancellation_reason or "No reason provided"
                }
            )

            return session

        except Exception as e:
            self.logger.error(f"Session cancellation error: {e}")
            self.db.rollback()
            raise