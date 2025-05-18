import os
import io
import pickle
import requests
import json
from typing import Optional
from PIL import Image
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from core.config import get_settings

""" NOTLAR
1. Token Yönetimi:
   - token.pickle dosyası GitHub'a gönderilmiyor (güvenlik nedeniyle)
   - Dağıtım ortamında (örn. Render.com) token.pickle içeriği base64 formatında TOKEN_BASE64 environment variable'ı olarak saklanıyor
   - Settings sınıfı bu base64 değeri decode edip geçici bir token.pickle dosyası oluşturuyor
   - Bu sayede dağıtım ortamında Google yetkilendirme penceresi açılmadan token kullanılabiliyor

2. Kimlik Bilgileri Yönetimi:
   - credentials.json dosyası yerine GOOGLE_CREDENTIALS_JSON environment variable'ı kullanılıyor
   - Bu değer Settings sınıfı tarafından parse edilip kullanılıyor
   - Geçici credentials.json dosyası oluşturulup işlem sonunda siliniyor

3. Dağıtım Notları:
   - Render.com'da TOKEN_BASE64 ve GOOGLE_CREDENTIALS_JSON environment variable'ları ayarlanmalı
   - TOKEN_BASE64: token.pickle dosyasının base64 formatındaki hali
   - GOOGLE_CREDENTIALS_JSON: credentials.json içeriği

4. Geliştirme Notları:
   - Lokal geliştirme ortamında token.pickle ve credentials.json dosyaları kullanılabilir
   - Settings sınıfı her iki durumu da destekliyor
   - Token yenileme işlemi otomatik yapılıyor
"""


class GooglePhotosError(Exception):
    """Google Photos işlemleri sırasında oluşan hatalar için özel hata sınıfı."""
    def __init__(self, message: str, error_code: int = 500, problematic_value: str = None):
        self.message = message
        self.error_code = error_code  # HTTP durum kodu (404, 500 vb.)
        self.problematic_value = problematic_value
        super().__init__(self.message)


class GooglePhotosService:
    SCOPES = [
        'https://www.googleapis.com/auth/photoslibrary',
        'https://www.googleapis.com/auth/photoslibrary.appendonly',
        'https://www.googleapis.com/auth/photoslibrary.sharing',
        'https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata', # albümleri listelemek için
        'https://www.googleapis.com/auth/photoslibrary.edit.appcreateddata' # fotoğraf açıklama güncelleme için
    ]
    ALBUM_NAME = "Uniyorum"

    def __init__(self, token_path='token.pickle'):
        self.settings = get_settings()
        self.token_path = token_path
        self.credentials = self._get_credentials()
        self.service = None
        self.album_id = None
        print("✅ GooglePhotosService başlatıldı")

    def _get_credentials(self) -> Credentials:
        try:
            print("🔐 Kimlik bilgileri alınıyor...")
            credentials = None

            # Settings'ten token path'i al
            token_path = self.settings.token_path

            if os.path.exists(token_path):
                with open(token_path, 'rb') as token:
                    credentials = pickle.load(token)
                    print("📦 Mevcut token yüklendi")

            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    print("♻️ Token süresi dolmuş, yenileniyor...")
                    credentials.refresh(Request())
                else:
                    print("🆕 Yeni kimlik bilgileri oluşturuluyor...")
                    # Settings'ten credentials bilgilerini al
                    credentials_data = self.settings.google_credentials
                    
                    # Geçici bir credentials.json dosyası oluştur
                    temp_credentials_path = 'temp_credentials.json'
                    with open(temp_credentials_path, 'w') as f:
                        json.dump({"web": credentials_data}, f)
                    
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            temp_credentials_path, 
                            self.SCOPES,
                            redirect_uri='http://localhost:8080/'
                        )
                        credentials = flow.run_local_server(port=8080)
                    finally:
                        # Geçici dosyayı temizle
                        if os.path.exists(temp_credentials_path):
                            os.remove(temp_credentials_path)

                # Token'ı kaydet
                with open(token_path, 'wb') as token:
                    pickle.dump(credentials, token)
                    print("✅ Yeni token kaydedildi")

            return credentials
        except Exception as e:
            raise GooglePhotosError(f"Kimlik doğrulama hatası: {e}", 400)


    def _get_service(self):
        if not self.service:
            print("🛠️ Google Photos servisi oluşturuluyor...")
            try:
                # Token süresi kontrolü
                if self.credentials.expired:
                    print("❌ Token süresi dolmuş.")
                    raise GooglePhotosError("Token süresi dolmuş, lütfen yeniden giriş yapın", 400)

                # Servisi oluştur
                self.service = build('photoslibrary', 'v1', 
                    credentials=self.credentials,
                    static_discovery=False,
                    cache_discovery=False
                )
                print("✅ Google Photos servisi oluşturuldu")
            except GooglePhotosError:
                # Token hatası için özel hata fırlat
                raise
            except Exception as e:
                print(f"❌ Servis oluşturma hatası: {str(e)}")
                raise GooglePhotosError(f"Servis oluşturulamadı: {e}", 500)
        return self.service


    async def _get_or_create_album(self) -> str:
        if self.album_id:
            return self.album_id

        try:
            service = self._get_service()
            print("🔍 Albümler kontrol ediliyor...")
            
            # Önce albümleri listele
            albums_result = service.albums().list(pageSize=50).execute()
            albums = albums_result.get('albums', [])
            print(f"📚 Toplam {len(albums)} albüm bulundu")

            # Mevcut albümü ara
            for album in albums:
                if album['title'] == self.ALBUM_NAME:
                    self.album_id = album['id']
                    print(f"📁 Mevcut albüm bulundu: {self.ALBUM_NAME}")
                    
                    # Albüm izinlerini kontrol et
                    try:
                        album_details = service.albums().get(albumId=self.album_id).execute()
                        if not album_details.get('isWriteable', False):
                            print("⚠️ Albüm yazılabilir değil, yeni albüm oluşturuluyor...")
                            # Yeni albüm oluştur
                            created_album = service.albums().create(
                                body={
                                    'album': {
                                        'title': f"{self.ALBUM_NAME}_new"
                                    }
                                }
                            ).execute()
                            self.album_id = created_album['id']
                            print(f"✅ Yeni albüm oluşturuldu: {self.ALBUM_NAME}_new")
                            return self.album_id
                        return self.album_id
                    except Exception as e:
                        print(f"⚠️ Albüm izinleri kontrol edilemedi: {str(e)}")
                        # Yeni albüm oluştur
                        created_album = service.albums().create(
                            body={
                                'album': {
                                    'title': f"{self.ALBUM_NAME}_new"
                                }
                            }
                        ).execute()
                        self.album_id = created_album['id']
                        print(f"✅ Yeni albüm oluşturuldu: {self.ALBUM_NAME}_new")
                        return self.album_id

            # Albüm bulunamadıysa yeni oluştur
            print(f"🆕 Yeni albüm oluşturuluyor: {self.ALBUM_NAME}")
            created_album = service.albums().create(
                body={
                    'album': {
                        'title': self.ALBUM_NAME
                    }
                }
            ).execute()
            
            self.album_id = created_album['id']
            print(f"✅ Albüm oluşturuldu: {self.ALBUM_NAME}")
            return self.album_id

        except Exception as e:
            print(f"❌ Albüm işlemi hatası: {str(e)}")
            raise GooglePhotosError(f"Albüm işlemi hatası: {e}", 500)


    async def upload_image(self, image: Image.Image, comment_id: int, template_type: str, DB_google_photos_id: str) -> str:
        try:
            print(f"📤 Yükleme başladı: comment_id={comment_id}")

            # aynı bilgiler ile resim üretilirse gelen media_item_id ile veritabanımdaki değer eşleşir.
            # bu durumda hiçbir şey yapılmayacak.
            if image.mode == 'RGBA':
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])
                image = background

            
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            img_byte_arr.seek(0)

            # Upload token alma
            print("🔑 Upload token alınıyor...")
            file_name = f"ComId_{comment_id}_{template_type}.jpg"
            try:
                upload_headers = {
                    "Authorization": f"Bearer {self.credentials.token}",
                    "Content-type": "application/octet-stream",
                    "X-Goog-Upload-File-Name": file_name,
                    "X-Goog-Upload-Protocol": "raw"
                }
                upload_response = requests.post(
                    "https://photoslibrary.googleapis.com/v1/uploads",
                    headers=upload_headers,
                    data=img_byte_arr.getvalue()
                )

            except UnicodeEncodeError as e:
                error_msg = f"Google Photos API Hatası: {str(e)}. Lütfen dosya adında Türkçe karakter kullanmayın. (Hatalı değer: {file_name})"
                print(f"❌ {error_msg}")
                raise GooglePhotosError(
                    error_msg,
                    400,
                    problematic_value=file_name
                )

            if upload_response.status_code != 200:
                error_msg = f"Google Photos API Hatası: {upload_response.text}. Lütfen tekrar deneyin."
                print(f"❌ {error_msg}")
                raise GooglePhotosError(error_msg, 500)  # Internal Server Error

            upload_token = upload_response.text
            print(f"📥 Upload token alındı")

            # Media item oluştur
            print("📦 Media item oluşturuluyor...")
            create_headers = {
                "Authorization": f"Bearer {self.credentials.token}",
                "Content-type": "application/json"
            }

            create_body = {
                "newMediaItems": [
                    {
                        # bir upload mevcutsa paylaşımı otomatik yapılmadı demektir.
                        "description": f"Paylaşım: ❌ Uniyorum Comment ID: {comment_id}",
                        "simpleMediaItem": {
                            "uploadToken": upload_token
                        }
                    }
                ]
            }

            create_response = requests.post(
                "https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate",
                headers=create_headers,
                json=create_body
            )

            if create_response.status_code != 200:
                raise GooglePhotosError(f"Media item oluşturulamadı: {create_response.text}", 500)

            response_json = create_response.json()
            print("📦 Media oluşturma yanıtı alındı")

            if 'newMediaItemResults' not in response_json:
                raise GooglePhotosError("Media item oluşturulamadı", 500)

            media_item = response_json['newMediaItemResults'][0].get('mediaItem')
            if not media_item:
                raise GooglePhotosError("Media item bilgisi alınamadı", 500)

            print(f"✅ Media yükleme başarılı: {media_item['id']}")

            # eğer DB_google_photos_id None değilse ve media_item_id ile aynı ise aynı resmi isitiyor demektir.
            if (DB_google_photos_id is not None) and (DB_google_photos_id == media_item['id']):
                print(f"🔄 Mevcut fotoğraf bulundu, hiçbir şey yapılmayacak !!!\n{DB_google_photos_id}")
                return media_item


            # eğer kullanıcı yeni bir resim üretmişse o resmi ilgili albüme de yükleyelim.
            print("🆕 Kullanıcı yeni bir resim üretmiş.")

            # Albüme ekle
            print("📁 Albüm kontrol ediliyor...")
            album_id = await self._get_or_create_album()
            
            print(f"📁 Media albüme ekleniyor: {album_id}")
            add_response = requests.post(
                f"https://photoslibrary.googleapis.com/v1/albums/{album_id}:batchAddMediaItems",
                headers=create_headers,
                json={"mediaItemIds": [media_item['id']]}
            )

            if add_response.status_code != 200:
                raise GooglePhotosError(f"Albüme eklenemedi: {add_response.text}", add_response.status_code)

            print(f"✅ Media albüme eklendi")

            # Eğer eski fotoğraf varsa sil
            ### google photos api fotoğraf silmeyi desteklemiyor.
            # biz de silmek yerine ilgili albümden kaldırıp açıklamasını İptal olarak değiştirelim.
            # ama bizim veritabanımızda silmek yerine yeni bilgiler ile ilgili fotoyu tutacağız
            # yani güncellenmiş halini tutacağız.
            if DB_google_photos_id is not None:
                print(f"🗑️ Eski fotoğraf albümden kaldırılıyor: {DB_google_photos_id}")
                try:
                    # Önce albüm ID'sini al
                    album_id = await self._get_or_create_album()
                    
                    delete_response = requests.post(
                        f"https://photoslibrary.googleapis.com/v1/albums/{album_id}:batchRemoveMediaItems",
                        headers={
                            "Authorization": f"Bearer {self.credentials.token}",
                            "Content-type": "application/json"
                        },
                        json={"mediaItemIds": [DB_google_photos_id]}
                    )
                    
                    if delete_response.status_code != 200:
                        raise GooglePhotosError(f"Fotoğraf albümden silinemedi: {delete_response.text}", delete_response.status_code)
                        
                    print("✅ Eski fotoğraf başarıyla albümden kaldırıldı")

                    # Fotoğrafın açıklamasını "İptal" olarak güncelle
                    try:
                        # daha sonra bu açıklama değişimini replace ile yapabiliriz
                        # ama veritabanından veriyi çekmemiz ya da parametre olarak nesneyi almamız gerekecek.
                        print("✅ Silinen medya öğesi açıklamaları düzenleniyor...")
                        await self.update_media_item_description(
                            DB_google_photos_id,
                            f"İptal: ❌ Uniyorum Comment ID: {comment_id} - Bu resmi silebilirsin."
                        )
                        print("✅ Silinen medya açıklaması 'İptal' olarak güncellendi")
                    except Exception as e:
                        print(f"⚠️ Silinen medya açıklaması güncellenirken hata oluştu: {str(e)}")
                        # Açıklama güncellenmese bile devam et

                except Exception as e:
                    print(f"⚠️ Silinen medya albümden kaldırılırken hata oluştu: {str(e)}")
                    # Eski fotoğraf silinmese bile devam et.
                    # ama bunu birşekilde bilmemiz lazım ?

            return media_item

        except GooglePhotosError:
            raise
        except Exception as e:
            print(f"❌ Beklenmeyen hata: {str(e)}")
            raise GooglePhotosError(f"Yükleme hatası: {e}", 500)


    async def get_media_item(self, media_item_id: str) -> dict:
        """Google Photos'tan belirli bir medya öğesinin bilgilerini getirir."""
        try:
            print(f"🔍 Medya öğesi getiriliyor: {media_item_id}")
            service = self._get_service()

            response = service.mediaItems().get(mediaItemId=media_item_id).execute()
            print(f"✅ Medya öğesi başarıyla getirildi.")

            return response
        
        except Exception as e:
            print(f"❌ Medya öğesi getirilemedi: {str(e)}")
            raise GooglePhotosError(f"Medya öğesi getirilemedi: {str(e)}")


    async def update_media_item_description(self, media_item_id: str, description: str) -> dict:
        """Google Photos'taki bir medya öğesinin açıklamasını günceller."""
        try:
            print(f"📝 Medya öğesi açıklaması güncelleniyor...")
            service = self._get_service()
            
            # Güncellemeyi kaydet
            response = service.mediaItems().patch(
                id=media_item_id,
                updateMask="description",  # Bu satırı ekleyin
                body={"description": description}
            ).execute()

            print("✅ Medya öğesi açıklaması başarıyla güncellendi")
            return response
        
        except Exception as e:
            print(f"❌ Medya öğesi açıklaması güncellenemedi: {str(e)}")
            raise GooglePhotosError(f"Medya öğesi açıklaması güncellenemedi: {str(e)}")
