import base64
from datetime import datetime, UTC
from motor.motor_asyncio import AsyncIOMotorClient
from db.models import Token
from core.config import get_settings

settings = get_settings()

class TokenService:
    def __init__(self):
        self.client = AsyncIOMotorClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.collection = self.db.tokens

    async def get_token_from_db(self) -> bytes:
        """Veritabanından token'ı alır ve decode eder."""
        token_doc = await self.collection.find_one({"_id": "google_token"})
        if not token_doc:
            return None
        return base64.b64decode(token_doc["token_data"])

    async def save_token_to_db(self, token_data: bytes) -> None:
        """Token'ı base64'e çevirip veritabanına kaydeder."""
        base64_token = base64.b64encode(token_data).decode('utf-8')
        
        token = Token(
            token_data=base64_token,
            updated_at=datetime.now(UTC)
        )
        
        # _id alanını hariç tutarak güncelle
        update_data = token.model_dump(exclude={'id'})
        
        await self.collection.update_one(
            {"_id": "google_token"},
            {"$set": update_data},
            upsert=True
        )
