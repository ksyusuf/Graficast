from fastapi import Header, HTTPException
from core.config import get_settings
from models.response import ApiResponse
from fastapi import status
from services.template_service import TemplateService
from services.share_service import ShareService

async def verify_api_key(api_key: str = Header(alias="api-key", description="API Key for authentication")):
    """API anahtarını doğrular."""
    settings = get_settings()
    if not api_key:
        # api key gönderilmediği zaman
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ApiResponse.error_response(
                message="API key gerekli",
                code=status.HTTP_401_UNAUTHORIZED
            ).model_dump()
        )
    if api_key != settings.API_KEY:
        # api key yanlışsa
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ApiResponse.error_response(
                message="Geçersiz API key",
                code=status.HTTP_401_UNAUTHORIZED
            ).model_dump()
        )
    return api_key

def get_template_service() -> TemplateService:
    """Template servisi için dependency fonksiyonu."""
    return TemplateService()

def get_share_service() -> ShareService:
    """Paylaşım servisi için dependency fonksiyonu."""
    return ShareService() 