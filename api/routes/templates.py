from fastapi import APIRouter, Depends, status
from models.template import (
    BatchTemplateResponse,
    TemplateResponse,
    CreateTemplateTypeRequest
)
from models.response import ApiResponse
from services.template_service import TemplateService
from api.dependencies import verify_api_key, get_template_service

router = APIRouter(
    prefix="/templates",
    tags=["templates"],
    dependencies=[Depends(verify_api_key)]
)

@router.get("/", response_model=ApiResponse[BatchTemplateResponse])
async def get_all_templates(
        template_service: TemplateService = Depends(get_template_service)
) -> ApiResponse[BatchTemplateResponse]:
    """Tüm şablonları getirir."""
    try:
        templates = await template_service.get_all_templates()
        return ApiResponse.success_response(
            data=templates,
            code=status.HTTP_200_OK
        )
    except Exception as e:
        return ApiResponse.error_response(
            message=str(e),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 
    

@router.put("/template-types", response_model=ApiResponse[TemplateResponse])
async def upsert_template_type(
    request: CreateTemplateTypeRequest,
    template_service: TemplateService = Depends(get_template_service)
) -> ApiResponse[TemplateResponse]:
    """Şablon tipini günceller veya oluşturur."""
    try:
        template_type = await template_service.upsert_template_type(request)
        return ApiResponse.success_response(
            data=template_type,
            code=status.HTTP_200_OK  # 200 OK kullanıyoruz çünkü upsert işlemi
        )
    except ValueError as e:
        return ApiResponse.error_response(
            message=str(e),
            code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return ApiResponse.error_response(
            message=str(e),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 