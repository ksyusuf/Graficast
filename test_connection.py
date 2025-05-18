import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import get_settings

settings = get_settings()

async def test_connection():
    # GEREKTİĞİNDE BURADAN KONTROL SAĞLA.
    try:
        client = AsyncIOMotorClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB_NAME]
        count = await db["shares"].count_documents({})
        print(f"✅ MongoDB bağlantısı başarılı. 'shares' koleksiyonunda {count} belge var.")
        print(f"🔄 Kullanılan ortam: {settings.ENVIRONMENT}")
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
