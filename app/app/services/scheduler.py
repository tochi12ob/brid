from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from sqlalchemy.orm import Session
from contextlib import contextmanager
import logging
from datetime import datetime
from typing import Optional

from database import SessionLocal  # Assuming this is where your DB session is defined
from app.utils.email_handler import ComplianceEmailHandler  # Your email handler

logger = logging.getLogger(__name__)

# The function that DOES the work (no scheduler instance here)
def _process_pending_results_task(db_url):  # Pass db_url
    try:
        with ComplianceScheduler.get_db(db_url) as db:  # Use static get_db with db_url passed
            handler = ComplianceEmailHandler(db)
            handler.process_pending_results()
            logger.info(f"Completed processing pending results at {datetime.utcnow()}")
    except Exception as e:
        logger.error(f"Error in scheduled task: {e}")


class ComplianceScheduler:
    def __init__(self, db_url: str):
        self.db_url = db_url  # Store db_url
        self.scheduler = self._setup_scheduler()

    def _setup_scheduler(self) -> BackgroundScheduler:
        try:
            jobstores = {'default': SQLAlchemyJobStore(url=self.db_url)}
            scheduler = BackgroundScheduler(jobstores=jobstores, timezone='UTC')
            scheduler.add_listener(self._handle_job_event, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)
            return scheduler
        except Exception as e:
            logger.error(f"Failed to setup scheduler: {e}")
            raise

    @staticmethod
    @contextmanager
    def get_db(db_url):  # Static method to get db, now takes db_url
        db = SessionLocal(db_url)  # Pass db_url to session
        try:
            yield db
        finally:
            db.close()

    def _handle_job_event(self, event):
        if event.exception:
            logger.error(f"Job {event.job_id} failed with exception: {event.exception}")
        else:
            logger.info(f"Job {event.job_id} executed successfully")


    def schedule_compliance_check(self, hour: int = 0, minute: int = 0):
        try:
            if self.scheduler.get_job('process_compliance_results'):
                self.scheduler.remove_job('process_compliance_results')

            self.scheduler.add_job(
                func=_process_pending_results_task,  # Schedule the function
                args=[self.db_url],  # Pass db_url as argument
                trigger=CronTrigger(hour=hour, minute=minute),
                id='process_compliance_results',
                name='Process pending compliance results',
                replace_existing=True,
                misfire_grace_time=3600
            )
            logger.info(f"Scheduled compliance check for {hour:02d}:{minute:02d} UTC daily")
        except Exception as e:
            logger.error(f"Failed to schedule compliance check: {e}")
            raise

    def start(self):
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("Scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise

    def shutdown(self):
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Scheduler shut down successfully")
        except Exception as e:
            logger.error(f"Failed to shutdown scheduler: {e}")
            raise