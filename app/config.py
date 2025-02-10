from pydantic_settings import BaseSettings
from typing import Optional, Set
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:q5O0kXexRsuOCqGu@timely-clear-slug.data-1.use1.tembo.io:5432/postgres")
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Groq Configuration
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    
    # Compliance Checker Configuration
    COMPLIANCE_PDF_PATH: str = os.getenv(
        "COMPLIANCE_PDF_PATH", 
        str(Path(__file__).parent.parent / "Cybersecurity_Framework.pdf")
    )
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "8192"))
    RESERVED_TOKENS: int = int(os.getenv("RESERVED_TOKENS", "1000"))
    MODEL_NAME: str = os.getenv("MODEL_NAME", "llama3-70b-8192")
    
    # File Processing Configuration
    ALLOWED_FILE_TYPES: Set[str] = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain"
    }
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB default
    
    # Dynamic path for logs
    LOG_FILE: str = os.getenv(
        "LOG_FILE", 
        str(Path(__file__).parent.parent / "logs" / "compliance_check.log")
    )
    
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    BASE_WAIT_TIME: float = float(os.getenv("BASE_WAIT_TIME", "1.0"))
    SIMILARITY_THRESHOLD: int = int(os.getenv("SIMILARITY_THRESHOLD", "50"))
    
    # Authentication Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Email Configuration
    EMAIL_HOST: str = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USERNAME: Optional[str] = os.getenv("EMAIL_USERNAME")
    EMAIL_PASSWORD: Optional[str] = os.getenv("EMAIL_PASSWORD")
    
    # Application Configuration
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    API_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Compliance Checker Service"
    VERSION: str = "1.0.0"
    
    # File Storage Configuration
    BASE_DIR: str = str(Path(__file__).parent.parent)
    REPORT_OUTPUT_DIR: str = os.getenv(
        "REPORT_OUTPUT_DIR", 
        str(Path(BASE_DIR) / "reports")
    )
    UPLOADS_DIR: str = os.getenv(
        "UPLOADS_DIR", 
        str(Path(REPORT_OUTPUT_DIR) / "uploads")
    )
    REPORT_FORMAT: str = os.getenv("REPORT_FORMAT", "docx")
    
    # Cache and Rate Limiting
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "True").lower() == "true"
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", "3600"))

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._init_directories()
        self._validate_settings()
        
        # Handle Render PostgreSQL URL
        if self.DATABASE_URL.startswith("postgres://"):
            self.DATABASE_URL = self.DATABASE_URL.replace("postgres://", "postgresql://", 1)

    def _init_directories(self):
        """Initialize necessary directories"""
        os.makedirs(self.REPORT_OUTPUT_DIR, exist_ok=True)
        os.makedirs(self.UPLOADS_DIR, exist_ok=True)

    def _validate_settings(self):
        """Validate critical settings"""
        # In production, we'll handle the PDF path differently
        if not os.getenv("RENDER"):  # Only check locally
            if not os.path.exists(self.COMPLIANCE_PDF_PATH):
                raise ValueError(f"Compliance PDF not found at {self.COMPLIANCE_PDF_PATH}")

        if not self.GROQ_API_KEY and not self.OPENAI_API_KEY:
            raise ValueError("Either GROQ_API_KEY or OPENAI_API_KEY must be provided")

        # Only check directory permissions locally
        if not os.getenv("RENDER"):
            for directory in [self.REPORT_OUTPUT_DIR, self.UPLOADS_DIR]:
                if not os.access(directory, os.W_OK):
                    raise ValueError(f"Directory {directory} is not writable")

def get_settings() -> Settings:
    """Get settings instance with debug output if enabled"""
    settings = Settings()
    if settings.DEBUG:
        debug_settings = {
            key: value if not key.endswith(('KEY', 'PASSWORD')) else '[HIDDEN]'
            for key, value in settings.dict().items()
        }
        print("Current configuration:", debug_settings)
    return settings

# Create and export settings instance
settings = get_settings()