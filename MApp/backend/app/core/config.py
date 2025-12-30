from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "MApp Hotel Booking API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://mapp_user:mapp_password@localhost:5432/mapp_hotel_booking"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days
    
    # OTP
    OTP_EXPIRE_SECONDS: int = 600  # 10 minutes
    OTP_LENGTH: int = 6
    OTP_MAX_ATTEMPTS: int = 3
    OTP_RATE_LIMIT_SECONDS: int = 1800  # 30 minutes
    
    # CORS - Allow all localhost ports for development
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",
        # Add wildcard for Flutter web dev server (runs on random ports)
        "*"
    ]
    
    # Rate Limiting
    RATE_LIMIT_OTP_PER_MOBILE: int = 100  # Increased for testing
    RATE_LIMIT_WINDOW_SECONDS: int = 300  # 5 minutes (reduced for testing)
    
    # Session Management (TASK_03)
    SESSION_TIMEOUT_GUEST: int = 86400  # 24 hours
    SESSION_TIMEOUT_EMPLOYEE: int = 28800  # 8 hours
    SESSION_TIMEOUT_VENDOR: int = 43200  # 12 hours
    SESSION_TIMEOUT_ADMIN: int = 14400  # 4 hours
    
    MAX_SESSIONS_GUEST: int = 5
    MAX_SESSIONS_EMPLOYEE: int = 2
    MAX_SESSIONS_VENDOR: int = 3
    MAX_SESSIONS_ADMIN: int = 2
    
    SESSION_REFRESH_THRESHOLD: int = 300  # 5 minutes
    
    # JWT
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
