from pydantic import BaseModel
from typing import List, Optional
from db.models import DatabaseTemplate

class TemplateResponse(BaseModel):
    """Şablon yanıt modeli.
    DatabaseTemplate modelini API yanıtları için sarmalayan model.
    API yanıtlarını tutarlı ve yönetilebilir hale getirir.
    """
    data: DatabaseTemplate

class BatchTemplateResponse(BaseModel):
    """Toplu şablon yanıt modeli."""
    templates: List[TemplateResponse]

class CreateTemplateTypeRequest(BaseModel):
    """Şablon tipi oluşturma isteği modeli."""
    template_type: str
    name: str
    size: str
    description: str

    class Config:
        json_schema_extra = {
            "example": {
                "template_type": "instagram-post-square",
                "name": "Instagram Post",
                "size": "1080x1080",
                "description": "Kare oranlı gönderi şablonu."
            }
        } 