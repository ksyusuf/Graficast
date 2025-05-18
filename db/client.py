from motor.motor_asyncio import AsyncIOMotorClient
from core.config import get_settings

# Uygulama ayarlarını al
settings = get_settings()

# MongoDB bağlantısını oluştur
# motor.motor_asyncio, MongoDB için asenkron Python sürücüsüdür
client = AsyncIOMotorClient(settings.MONGO_URI)

# Veritabanı bağlantısını al
# settings.MONGO_DB_NAME ile belirtilen veritabanına bağlanır
db = client.get_database(settings.MONGO_DB_NAME)

# Veritabanı koleksiyonlarını tanımla
# shares: Paylaşımların tutulduğu koleksiyon
shares_collection = db["shares"]
# image_templates: Görsel şablonlarının tutulduğu koleksiyon
templates_collection = db["image_templates"]
