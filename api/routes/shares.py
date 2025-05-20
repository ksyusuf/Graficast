from fastapi import APIRouter, Depends, HTTPException, status
from models.share import (
    BatchCommentRequest,
    BatchShareResponse,
    DatabaseShare,
    GenerateImageRequest,
    UpdateShareRequest,
    ShareResponse,
    UpdateErrorRequest,
    UpdateTagsRequest
)
from db.models import ApiShare
from services.share_service import ShareService
from services.google_photos_service import GooglePhotosError
from models.response import ApiResponse
from api.dependencies import verify_api_key, get_share_service

router = APIRouter(
    prefix="/shares", 
    tags=["shares"],
    dependencies=[Depends(verify_api_key)]  # Tüm shares endpoint'leri için API key kontrolü
)

@router.post("/batch", response_model=ApiResponse[BatchShareResponse])
async def get_shares_batch(
        request: BatchCommentRequest,
        share_service: ShareService = Depends(get_share_service)
) -> ApiResponse[BatchShareResponse]:
    """Toplu paylaşım bilgilerini getirir."""
    if not request.comment_ids:
        return ApiResponse.error_response(
            message="En az bir comment_id gerekli",
            code=status.HTTP_400_BAD_REQUEST
        )

    try:
        shares = await share_service.get_shares_batch(request.comment_ids)
        return ApiResponse.success_response(
            data=BatchShareResponse(shares=shares),
            code=status.HTTP_200_OK
        )
    except Exception as e:
        return ApiResponse.error_response(
            message=str(e),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/image-create", response_model=ApiResponse[ShareResponse])
async def image_create(
        request: GenerateImageRequest,
        share_service: ShareService = Depends(get_share_service)
) -> ApiResponse[ShareResponse]:
    """Görsel oluşturur ve Google Photos'a yükler. Yalnızca yetkilendirilmiş kullanıcılar tarafından çağrılabilir."""
    try:
        # GenerateImageRequest'i ApiShare'e dönüştür
        api_share_data = ApiShare(
            comment_id=request.comment_id,
            comment=request.comment,
            comment_date=request.comment_date,
            writer_name=request.writer_name,
            uni_name=request.uni_name,
            dep_name=request.dep_name,
            ins_name=request.ins_name,
            image_template_type=request.image_template_type
        )
        
        # Görsel oluştur ve paylaşım bilgilerini güncelle
        # gelen share: DatabaseShare'dir.
        share = await share_service.create_image(api_share_data)

        return ApiResponse.success_response(
            # DatabaseShare'i ShareResponse'a dönüştür
            data=ShareResponse(**share.model_dump())
        )

    except GooglePhotosError as e:
        print(f"Google Photos hatası: {str(e)}")
        ApiResponse.error_response(
            message=f"Google Photos hatası: {str(e)}",
            code=int(e.error_code)
        )
    except ValueError as e:
        print(f"Validasyon hatası yakalandı: {str(e)}")
        print(f"Hata tipi: {type(e)}")
        ApiResponse.error_response(
            message=str(e),
            code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        print(f"Beklenmeyen hata: {str(e)}")
        print(f"Hata tipi: {type(e)}")
        ApiResponse.error_response(
            message=str(e),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    

@router.put("/toggle-share", response_model=ApiResponse[DatabaseShare])
async def toggle_share_status(
        request: UpdateShareRequest,
        share_service: ShareService = Depends(get_share_service)
) -> ApiResponse[DatabaseShare]:
    """Paylaşım durumunu değiştirir."""
    try:
        share = await share_service.toggle_share_status(
            request.comment_id,
            request.image_template_type
        )
        return ApiResponse.success_response(
            data=share,
            code=status.HTTP_200_OK
        )
    except ValueError as e:
        return ApiResponse.error_response(
            message=str(e),
            code=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return ApiResponse.error_response(
            message=str(e),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/tags", response_model=ApiResponse[DatabaseShare])
async def update_tags(
        request: UpdateTagsRequest,
        share_service: ShareService = Depends(get_share_service)
) -> ApiResponse[DatabaseShare]:
    """Paylaşıma etiket ekler. Yeni etiketleri mevcut etiketlere ekler, var olanları atlar.
    Etiket silme özelliği henüz yok."""
    try:
        share = await share_service.update_tags(
            request.comment_id,
            request.template_type,
            request.tags
        )
        return ApiResponse.success_response(
            data=share,
            code=status.HTTP_200_OK
        )
    except ValueError as e:
        return ApiResponse.error_response(
            message=str(e),
            code=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return ApiResponse.error_response(
            message=str(e),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 


@router.put("/update-error", response_model=ApiResponse[DatabaseShare])
async def update_error_message(
        request: UpdateErrorRequest,
        share_service: ShareService = Depends(get_share_service)
) -> ApiResponse[DatabaseShare]:
    """Paylaşımın hata mesajını günceller."""
    try:
        share = await share_service.update_error_message(
            request.comment_id,
            request.template_type,
            request.error_message
        )
        return ApiResponse.success_response(
            data=share,
            code=status.HTTP_200_OK
        )
    except ValueError as e:
        return ApiResponse.error_response(
            message=str(e),
            code=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return ApiResponse.error_response(
            message=str(e),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
