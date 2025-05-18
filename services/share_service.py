from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import get_settings
from models.share import DatabaseShare, ShareResponse
from db.models import ApiShare
from services.image_renderer import ImageRenderer
from services.google_photos_service import GooglePhotosService
from services.google_photos_service import GooglePhotosError


class ShareService:
    def __init__(self):
        settings = get_settings()
        self.client = AsyncIOMotorClient(settings.MONGO_URI)
        self.db = self.client.get_database(settings.MONGO_DB_NAME)
        self.collection = self.db.get_collection("shares")
        self.image_renderer = ImageRenderer()
        self.image_output_dir = "output/images"


    def _get_turkey_time(self) -> datetime:
        """Türkiye saatini döndürür (GMT+3)"""
        return datetime.now(UTC) + timedelta(hours=3)


    async def get_shares_batch(self, comment_ids: List[int]) -> List[ShareResponse]:
        """Toplu paylaşım bilgilerini getirir. Olmayan comment_id'ler için yeni kayıt oluşturur.
            bu zaten benim uniyorumda her sayfam yüklendiği zaman çalışacağı için google api servisimin
            token süresinin dolma sı ihtimali çok olmayacak.
            bu yüzden diğer metotlarda tekrar tekrar token.pickle yenilemiyorum."""
        # Mevcut paylaşımları getir
        cursor = self.collection.find({"comment_id": {"$in": comment_ids}})
        existing_shares = await cursor.to_list(length=None)
        
        # Mevcut paylaşımları ShareResponse listesine dönüştür
        shares = [ShareResponse(data=DatabaseShare(**share)) for share in existing_shares]
        
        # Olmayan comment_id'ler için yeni kayıtlar oluştur
        existing_comment_ids = {share["comment_id"] for share in existing_shares}
        for comment_id in comment_ids:
            if comment_id not in existing_comment_ids:
                new_share = DatabaseShare(
                    comment_id=comment_id,
                    image_template_type=None,
                    image_created_date=None,
                    image_updated_date=None,
                    is_uploaded_google=False,
                    uploaded_date_google=None,
                    last_uploaded_date_google=None,
                    google_photos_id=None,
                    google_product_id=None,
                    google_description=f"Paylaşım: ❌ Uniyorum Comment ID: {comment_id}",
                    is_shared=False,
                    shared_date=None,
                    last_shared_date=None,
                    error_message=None,
                    tags=[]
                )
                result = await self.collection.insert_one(new_share.model_dump())
                shares.append(ShareResponse(data=new_share))

        return shares
    

    async def create_image(self, api_share_data: ApiShare) -> DatabaseShare:
        """Görsel oluşturur ve google'a update eder vepaylaşım bilgilerini günceller."""
        try:
            # Önce comment_id'nin varlığını kontrol et
            comment_exists = await self.collection.find_one({"comment_id": api_share_data.comment_id})
            if not comment_exists:
                print("DEBUG: ValueError fırlatılıyor - comment_exists")
                raise ValueError(
                    f"Comment ID {api_share_data.comment_id} için paylaşım bulunamadı. "
                    "Lütfen önce bu yorumu veritabanına kaydedin."
                )

            # Template type'ı belirle
            # şimdilik sadece instagram-post-square destekleniyor.
            template_type = api_share_data.image_template_type
            if template_type not in ["instagram-post-square"]:
                print(f"❌ Geçersiz template type: '{template_type}'.")
                raise ValueError(f"Geçersiz template type: '{template_type}'. Mevcut sürümde yalnızca 'instagram-post-square' destekleniyor.")
            
            current_time = self._get_turkey_time()

            # Görsel oluştur
            print("🎨 Görsel oluşturuluyor...")
            image = self.image_renderer.render(api_share_data)
            print("✅ Görsel oluşturuldu")


            # Önce aynı template_type ile kayıt var mı kontrol et
            existing_share = await self.collection.find_one({
                "comment_id": api_share_data.comment_id,
                "image_template_type": template_type
            })
            # aynı resmin üretilme durumunun kontrolü sadece bu veriler ile yapılabilir.
            # eğer tam bir kontrol yapmak isteseydim
            # comment, uni, dep, ins, writer bilgilerini kaydetmiş olmam gerekirdi.
            # bu bilgileri kaydetmeyi tercih etmediğim için, gelen veriler ile foto oluşturup
            # google'a göndereceğim, gelen media_item_id ile kontrol sağlayacağım.
            # aynı media_item_id varsa -aynı- resim önceden yüklenmiş demektir. hiçbir şey yapmayacağım.
            
            # Google Photos'a yükle
            print("📤 Google Photos'a yükleniyor...")
            google_photos_service = GooglePhotosService()
            media_item = await google_photos_service.upload_image(image,
                                                                     api_share_data.comment_id,
                                                                     template_type,
                                                                     existing_share.get("google_photos_id") if existing_share else None)

            # aynı resim yüklenmişse hiçbir şey yapmayacağız.
            if media_item['id'] == existing_share.get("google_photos_id") if existing_share else None:
                print("🔄 Aynı resim yüklendiği için veritabanında da hiçbir şey yapılmayacak !!!")
                return DatabaseShare(**existing_share)

            # eğer farklı resim istediyse normal devam ediyoruz.

            # Veritabanı kaydını güncelle
            print("💾 Veritabanı güncelleniyor...")

            print(f"🔍 Aynı template kaydı kontrolü: {'Var' if existing_share else 'Yok'}")

            if existing_share:
                # Aynı template_type ile kayıt varsa güncelle
                print("📝 Mevcut template kaydı güncelleniyor...")
                share_data = DatabaseShare(**existing_share)
                
                # Sadece güncellenecek alanları değiştir
                share_data.image_updated_date = current_time
                share_data.is_shared = False  # yeni foto ürettiğimiz için paylaşılmamış olacak
                share_data.last_shared_date = None  # son paylaşım tarihi yok olacak
                share_data.last_uploaded_date_google = current_time
                share_data.google_photos_id = media_item['id']
                share_data.google_product_id = media_item['productUrl']
                # share_data.google_description = /// bu alanı güncellemeye gerek yok burada.
                share_data.error_message = None

                # Mevcut kaydı güncelle
                result = await self.collection.update_one(
                    {"_id": existing_share["_id"]},
                    {"$set": share_data.model_dump()}
                )
                print(f"✅ Mevcut template kaydı güncellendi: {result.modified_count > 0}")
            else:
                # Aynı template_type yoksa, null template kontrolü yap
                null_template_share = await self.collection.find_one({
                    "comment_id": api_share_data.comment_id,
                    "image_template_type": None
                })
                print(f"🔍 Null template kaydı kontrolü: {'Var' if null_template_share else 'Yok'}")

                if null_template_share:
                    # Null template kaydı varsa güncelle
                    print("📝 Null template kaydı güncelleniyor...")
                    share_data = DatabaseShare(**null_template_share)
                    
                    # Template type ve diğer alanları güncelle
                    share_data.image_template_type = template_type
                    share_data.image_created_date = current_time # veri yeni eklendiği için burası null kalmasın.
                    share_data.image_updated_date = current_time
                    share_data.is_uploaded_google=True
                    share_data.is_shared = False
                    share_data.last_shared_date = None
                    share_data.uploaded_date_google = current_time
                    share_data.last_uploaded_date_google = current_time
                    share_data.google_photos_id = media_item['id']
                    share_data.google_product_id = media_item['productUrl']
                    # share_data.google_description = /// bu alanı güncellemeye gerek yok burada.
                    share_data.error_message = None

                    # Null template kaydını güncelle
                    result = await self.collection.update_one(
                        {"_id": null_template_share["_id"]},
                        {"$set": share_data.model_dump()}
                    )
                    print(f"✅ Null template kaydı güncellendi: {result.modified_count > 0}")
                else:
                    # Hiç kayıt yoksa yeni kayıt oluştur
                    print("🆕 Yeni kayıt oluşturuluyor...")
                    share_data = DatabaseShare(
                        comment_id=api_share_data.comment_id,
                        image_template_type=template_type,
                        image_created_date=current_time,
                        image_updated_date=current_time,
                        is_uploaded_google=True,
                        uploaded_date_google=current_time,
                        last_uploaded_date_google=current_time,
                        google_photos_id=media_item['id'],
                        google_product_id=media_item['productUrl'],
                        google_description=None, # burası upload edilirken dolduruluyor.
                        is_shared=False,
                        shared_date=None,
                        last_shared_date=None,
                        error_message=None,
                        tags=[]
                    )

                    # Yeni kayıt ekle
                    result = await self.collection.insert_one(share_data.model_dump())
                    print(f"✅ Yeni kayıt oluşturuldu: {result.inserted_id}")

            # Güncellenmiş kaydı getir
            updated_share = await self.collection.find_one({
                "comment_id": api_share_data.comment_id,
                "image_template_type": template_type
            })
            if not updated_share:
                raise ValueError(f"Comment ID {api_share_data.comment_id} için güncellenmiş kayıt bulunamadı")

            print("✅ Veritabanı işlemi tamamlandı")
            return DatabaseShare(**updated_share)

        except ValueError as e:
            print(f"❌ Validasyon hatası: {str(e)}")
            # ValueError'u doğrudan yukarı fırlat, yakalama
            raise e
        except GooglePhotosError as e:
            print(f"❌ Google Photos hatası: {str(e)}")
            raise
        except Exception as e:
            print(f"❌ Beklenmeyen hata: {str(e)}")
            raise ValueError(f"Görsel oluşturulurken hata oluştu: {str(e)}")
        

    async def toggle_share_status(self, comment_id: int, template_type: str) -> DatabaseShare:
        """Paylaşım durumunu değiştirir ve Google Photos açıklamasını günceller."""
        print(f"🔄 Paylaşım durumu değiştiriliyor - Comment ID: {comment_id}, Template: {template_type}")
        
        # Önce comment_id ve template_type eşleşmesini kontrol et
        share = await self.collection.find_one({
            "comment_id": comment_id,
            "image_template_type": template_type
        })
        
        if not share:
            print(f"❌ Paylaşım bulunamadı - Comment ID: {comment_id}, Template: {template_type}")
            raise ValueError(
                f"Comment ID {comment_id} ve template '{template_type}' için görsel bulunamadı. "
                "Lütfen önce bu yorum için görsel oluşturun."
            )

        new_status = not share.get("is_shared", False)
        
        print(f"📊 Yeni paylaşım durumu: {'Paylaşıldı' if new_status else 'Paylaşım kaldırıldı.'}")

        # Google Photos açıklamasını güncelle
        if share.get("google_photos_id"):
            print(f"🖼️ Google Photos açıklaması güncelleniyor...")
            try:
                # Tik veya çarpı işareti ekle
                status_symbol = "✅" if new_status else "❌"
                
                # Yeni açıklama oluştur
                new_description = f"Paylaşım: {status_symbol} Uniyorum Comment ID: {comment_id}"
                     
                print(f"📝 Yeni açıklama: {new_description}")
                
                # Google Photos açıklamasını güncelle
                google_photos = GooglePhotosService()
                await google_photos.update_media_item_description(share["google_photos_id"], new_description)
                print("✅ Google Photos açıklaması başarıyla güncellendi")
                
            except Exception as e:
                error_msg = f"Google Photos açıklaması güncellenirken hata oluştu: {str(e)}"
                print(f"❌ {error_msg}")
                # Hata durumunda istemciye bilgi ver
                raise ValueError(error_msg)

        print("💾 Veritabanı güncelleniyor...")

        current_time = self._get_turkey_time()
        
        # normalde burada tip güvenliği açısından databaseShare nesnesi kullanabilirdim fakat
        # mongodb update ederken benden dict bekleniyor. ve ben databaseShare kullansam bie daha sonra
        # onu dict yapmak için bu şekilde ifade edip model_dump() yapmam gerekecek.
        # bu yüzden böyle gönderiyoruz.
        update_data = {
            "is_shared": new_status,
            "last_shared_date": current_time,
            "google_description": new_description
        }

        if new_status and not share.get("shared_date"):
            update_data["shared_date"] = current_time

        result = await self.collection.update_one(
            {"_id": share["_id"]},
            {"$set": update_data}
        )

        if result.modified_count == 0:
            print("❌ Veritabanı güncellemesi başarısız")
            raise ValueError("Paylaşım durumu güncellenemedi")

        print("✅ Veritabanı başarıyla güncellendi")
        updated_share = await self.collection.find_one({
            "comment_id": comment_id,
            "image_template_type": template_type
        })
        return DatabaseShare(**updated_share)


    async def update_tags(self, comment_id: int, template_type: str, new_tags: List[str]) -> DatabaseShare:
        """Etiketleri günceller. Yeni etiketleri mevcut etiketlere ekler, var olanları atlar.
        
        Args:
            comment_id: Yorum ID'si
            template_type: Şablon tipi
            new_tags: Eklenecek yeni etiketler
            
        Returns:
            DatabaseShare: Güncellenmiş paylaşım
            
        Raises:
            ValueError: Paylaşım bulunamazsa
        """
        # Paylaşımı bul
        share = await self.collection.find_one({
            "comment_id": comment_id,
            "image_template_type": template_type
        })
        
        if not share:
            raise ValueError(f"Paylaşım bulunamadı. (comment_id: {comment_id}, template_type: {template_type})")
        
        # Mevcut etiketleri al
        current_tags = share.get("tags", [])
        
        # Yeni etiketleri ekle (var olanları atla)
        updated_tags = list(set(current_tags + new_tags))
        
        # Etiketleri güncelle
        result = await self.collection.update_one(
            {"_id": share["_id"]},
            {"$set": {"tags": updated_tags}}
        )
        
        if result.modified_count == 0:
            raise ValueError(f"Etiketler zaten mevcut. (comment_id: {comment_id}, template_type: {template_type})")
        
        # Güncellenmiş paylaşımı döndür
        updated_share = await self.collection.find_one({"_id": share["_id"]})
        return DatabaseShare(**updated_share)
    

    async def update_error_message(self, comment_id: int, template_type: str, error_message: str) -> DatabaseShare:
        """Hata mesajını günceller.
        
        Args:
            comment_id: Yorum ID'si
            template_type: Şablon tipi
            error_message: Hata mesajı
            
        Returns:
            DatabaseShare: Güncellenmiş paylaşım
            
        Raises:
            ValueError: Paylaşım bulunamazsa
        """
        # Paylaşımı bul
        share = await self.collection.find_one({
            "comment_id": comment_id,
            "image_template_type": template_type
        })
        
        if not share:
            raise ValueError(f"Paylaşım bulunamadı. (comment_id: {comment_id}, template_type: {template_type})")
        
        # Hata mesajını güncelle
        result = await self.collection.update_one(
            {"_id": share["_id"]},
            {"$set": {"error_message": error_message}}
        )
        
        if result.modified_count == 0:
            raise ValueError(f"Yorum zaten güncellenmiş. (comment_id: {comment_id}, template_type: {template_type}) ")
        
        # Güncellenmiş paylaşımı döndür
        updated_share = await self.collection.find_one({"_id": share["_id"]})
        return DatabaseShare(**updated_share)
