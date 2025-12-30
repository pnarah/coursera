from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import re

from app.core.config import settings
from app.db.redis import init_redis_pool, close_redis_pool
from app.api.v1 import auth, rooms, availability, pricing, hotels, bookings, payments, users, sessions
from app.api.v1.endpoints import subscriptions, notifications, vendor, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await init_redis_pool()
    yield
    # Shutdown
    await close_redis_pool()
    print("Application shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Hotel booking platform API with OTP authentication",
    lifespan=lifespan,
)

# Custom CORS middleware for development that allows all localhost origins
class DevelopmentCORSMiddleware(BaseHTTPMiddleware):
    """
    Development CORS middleware that dynamically allows any localhost/127.0.0.1 origin.
    In production, this should be replaced with specific allowed origins.
    """
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        
        # Check if origin is localhost or 127.0.0.1 (any port)
        is_allowed = False
        if origin:
            is_allowed = re.match(r'https?://(localhost|127\.0\.0\.1)(:\d+)?$', origin) is not None
        
        response = await call_next(request)
        
        # Handle CORS headers
        if is_allowed and origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Expose-Headers"] = "*"
        
        # Handle preflight requests
        if request.method == "OPTIONS" and is_allowed and origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Max-Age"] = "600"
        
        return response

# Apply custom CORS middleware
app.add_middleware(DevelopmentCORSMiddleware)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])
app.include_router(hotels.router, prefix="/api/v1", tags=["hotels"])
app.include_router(rooms.router, prefix="/api/v1", tags=["rooms"])
app.include_router(availability.router, prefix="/api/v1", tags=["availability"])
app.include_router(pricing.router, prefix="/api/v1", tags=["pricing"])
app.include_router(bookings.router, prefix="/api/v1", tags=["bookings"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])
app.include_router(subscriptions.router, prefix="/api/v1", tags=["subscriptions"])
app.include_router(notifications.router, prefix="/api/v1", tags=["notifications"])
app.include_router(vendor.router, prefix="/api/v1/vendor", tags=["vendor"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
