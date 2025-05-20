from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from db.models import DatabaseShare

class GenerateImageRequest(BaseModel):
    """Görsel oluşturma isteği modeli."""
    comment_id: int
    comment: str
    comment_date: datetime
    writer_name: str
    uni_name: str
    dep_name: Optional[str] = None
    ins_name: Optional[str] = None
    image_template_type: Optional[str] = None

class UpdateShareRequest(BaseModel):
    """Paylaşım güncelleme isteği modeli."""
    comment_id: int
    image_template_type: str

    class Config:
        json_schema_extra = {
            "example": {
                "comment_id": 1,
                "image_template_type": "instagram-post-square"
            }
        }

class BatchCommentRequest(BaseModel):
    """Toplu yorum ID'lerini içeren istek modeli."""
    comment_ids: List[int]

    class Config:
        json_schema_extra = {
            "example": {
                "comment_ids": [1, 2, 3, 4, 5]
            }
        }

class ShareResponse(DatabaseShare):
    """Paylaşım yanıt modeli.
    ** API Response Wrapper Kullanımı:
    ShareResponse gibi wrapper modeller kullanmak,
    API yanıtlarını daha tutarlı ve yönetilebilir hale getirir
    İleride yanıta ek bilgiler eklemek gerekirse
    (örneğin metadata, pagination bilgileri vb.) kolayca genişletilebilir
    API versiyonlama ve değişiklik yönetimi daha kolay olur

    ** Doğrudan Model Kullanımı:
    Daha basit ve düz bir yapı
    Gereksiz katmanı ortadan kaldırır
    Daha az kod ve daha az karmaşıklık

    ** Best Practices Açısından:
    REST API'lerde genellikle response wrapper'lar kullanılır
    Bu, API'nin tutarlılığını ve öngörülebilirliğini artırır
    Hata durumları ve başarılı yanıtlar için standart bir format sağlar
    """
    pass

class BatchShareResponse(BaseModel):
    """Toplu paylaşım yanıt modeli."""
    shares: List[ShareResponse]

class UpdateErrorRequest(BaseModel):
    """Hata mesajı güncelleme isteği modeli."""
    comment_id: int
    template_type: str
    error_message: str

    class Config:
        json_schema_extra = {
            "example": {
                "comment_id": 123,
                "template_type": "instagram-post-square",
                "error_message": "Bu görselde bir problem var sanki."
            }
        }

class UpdateTagsRequest(BaseModel):
    """Etiket güncelleme isteği modeli."""
    comment_id: int
    template_type: str
    tags: List[str]

    class Config:
        json_schema_extra = {
            "example": {
                "comment_id": 123,
                "template_type": "instagram-post-square",
                "tags": ["yorum", "olumlu", "dikkat çekici"]
            }
        }

"""
yarın şunları yapacağız:

* yeni bir endpoint oluşturacağız, bu endpoint GenerateImageRequest modelinde gelecek. daha sonra model içerisinde gelen veriler ile image_renderer sınıfı ile resim üreteceğiz.
 - ardından resmi google fotoğraflar api'si kullanarak google fotoğraflara yükleyeceğiz (eğer bu işlemde zorlanırsak başka bir yol izleyebiliriz)
 - ardından ilgili  GenerateImageRequest içerisindeki comment_id değerindeki veriyi veritabanında bulunup ilgili alanlarının güncellenmesini sağlayacağız. bu alanları sırasıyla da güncelleyebiliriz tüm işlemler tamamlanınca toplu olarak da güncelleyebiliriz. 
""" 