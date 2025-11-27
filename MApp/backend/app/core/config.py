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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # OTP
    OTP_EXPIRE_SECONDS: int = 300  # 5 minutes
    OTP_LENGTH: int = 6
    
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
    RATE_LIMIT_OTP_PER_MOBILE: int = 3
    RATE_LIMIT_WINDOW_SECONDS: int = 1800  # 30 minutes
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
