from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.redis import init_redis_pool, close_redis_pool
from app.api.v1 import auth, rooms, availability, pricing, hotels, bookings


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

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(hotels.router, prefix="/api/v1", tags=["hotels"])
app.include_router(rooms.router, prefix="/api/v1", tags=["rooms"])
app.include_router(availability.router, prefix="/api/v1", tags=["availability"])
app.include_router(pricing.router, prefix="/api/v1", tags=["pricing"])
app.include_router(bookings.router, prefix="/api/v1", tags=["bookings"])


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
