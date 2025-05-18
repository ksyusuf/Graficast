from motor.motor_asyncio import AsyncIOMotorClient
from core.config import get_settings
from models.template import TemplateResponse, BatchTemplateResponse
from db.models import DatabaseTemplate
from models.template import CreateTemplateTypeRequest

class TemplateService:
    def __init__(self):
        settings = get_settings()
        self.client = AsyncIOMotorClient(settings.MONGO_URI)
        self.db = self.client.get_database(settings.MONGO_DB_NAME)
        self.collection = self.db.get_collection("image_templates")

    async def get_all_templates(self) -> BatchTemplateResponse:
        """Tüm şablonları veritabanından çeker ve döndürür."""
        cursor = self.collection.find({})
        templates = await cursor.to_list(length=None)
        
        template_responses = [
            TemplateResponse(data=DatabaseTemplate(**template))
            for template in templates
        ]
        
        return BatchTemplateResponse(templates=template_responses)


    async def upsert_template_type(self, request: CreateTemplateTypeRequest) -> TemplateResponse:
        """Şablon tipini günceller veya oluşturur."""
        # Aynı template_type daha önce eklenmiş mi kontrol et
        existing = await self.collection.find_one({"template_type": request.template_type})
        
        if existing:
            print(f"⚠️ Template zaten mevcut. ({request.template_type})")
            raise ValueError(f"Template zaten mevcut. '{request.template_type}'")
        
        # Yeni template oluştur
        template_data = DatabaseTemplate(
            template_type=request.template_type,
            name=request.name,
            size=request.size,
            description=request.description,
            template_path=f"templates/{request.template_type}.json" # şimdilik böyle
        )
        
        # Veritabanına ekle
        result = await self.collection.insert_one(template_data.model_dump())
        print(f"✅ Yeni template eklendi. ID: {result.inserted_id}")
        
        return TemplateResponse(data=template_data) 