#main.property
from fastapi import FastAPI, File, UploadFile, HTTPException
from app.routes import compliance, session, user, auth_routes,admin_routes
from app.services.scheduler import ComplianceScheduler
from config import get_settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get settings instance
settings = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url=f"{settings.API_PREFIX}/docs",
    openapi_url=f"{settings.API_PREFIX}/openapi.json"
)

# Initialize scheduler
scheduler = ComplianceScheduler(settings.DATABASE_URL)

# Include routes
app.include_router(compliance.router, prefix=settings.API_PREFIX)
app.include_router(session.router, prefix=settings.API_PREFIX)
app.include_router(user.user_router, prefix=settings.API_PREFIX)
app.include_router(auth_routes.router, prefix=settings.API_PREFIX)
app.include_router(admin_routes.router, prefix=settings.API_PREFIX)

# Startup event to start scheduler
@app.on_event("startup")
async def start_scheduler():
    try:
        # Schedule the compliance check to run daily at 1 AM UTC
        scheduler.schedule_compliance_check(hour=1, minute=0)
        scheduler.start()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        # You might want to handle this error differently depending on your needs
        # For now, we'll let the application start even if the scheduler fails

# Shutdown event to stop scheduler
@app.on_event("shutdown")
async def shutdown_scheduler():
    try:
        scheduler.shutdown()
        logger.info("Scheduler shut down successfully")
    except Exception as e:
        logger.error(f"Failed to shutdown scheduler: {e}")

@app.get("/")
def root():
    return {
        "message": "Welcome to the Policy Compliance System API",
        "version": settings.VERSION,
        "docs_url": f"{settings.API_PREFIX}/docs"
    }