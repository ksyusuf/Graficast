from fastapi import APIRouter, Depends
from core.config import get_settings
from core.version import __version__, __build__, __author__, __description__
from models.response import ApiResponse

router = APIRouter()

@router.get("/")
async def root():
    """Root endpoint, health endpoint'ine yönlendirir."""
    return ApiResponse.success_response(
        data={
            "message": "Welcome to Graficast API",
            "docs": "/docs",
            "health": "/health"
        }
    )

@router.get("/health")
async def health():
    """Servis sağlık durumunu döndürür. :)"""
    settings = get_settings()
    
    return ApiResponse.success_response(
        data={
            "status": "healthy",
            "version": __version__,
            "build": __build__,
            "environment": settings.ENVIRONMENT,
            "service": "graficast",
            "author": __author__,
            "description": __description__
        }
    )