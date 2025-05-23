from services.google_photos_service import GooglePhotosService
import base64
import pickle
from io import BytesIO
import asyncio
from core.config import get_settings
import json
from google_auth_oauthlib.flow import InstalledAppFlow

# Settings'ten credentials'ı al
settings = get_settings()
credentials_json = settings.GOOGLE_CREDENTIALS_JSON
credentials_dict = json.loads(credentials_json)

# GooglePhotosService instance'ı oluştur (SCOPES'a erişmek için)
service = GooglePhotosService()

async def get_token():
    # OAuth2 flow'u başlat
    flow = InstalledAppFlow.from_client_config(
        credentials_dict,
        service.SCOPES,  # GooglePhotosService'in kendi scope'larını kullan
        # Redirect URI'yi sunucu ortamında genellikle kullanmasanız da,
        # run_local_server için belirtmek gerekir.
        # İlk yetkilendirmeyi manuel yaparken "urn:ietf:wg:oauth:2.0:oob" kullanabilirsiniz.
        # Ancak run_local_server ile otomatik bir tarayıcı açılıyorsa, localhost doğrudur.
        redirect_uri='http://localhost:8080/'
    )

    print("Google Kimlik Doğrulama Süreci Başlatılıyor...")
    print("Tarayıcınızda açılacak pencerede Google hesabınızı seçin ve izni onaylayın.")
    print("Bu işlem size bir refresh_token sağlayacaktır.")

    # Kimlik doğrulama - Buraya access_type='offline' ve prompt='consent' ekliyoruz!
    creds = flow.run_local_server(
        port=8080,
        access_type='offline',  # Bu, refresh_token almamızı sağlar
        prompt='consent'        # Kullanıcıdan her zaman izin onayını ister, refresh_token garantisi için faydalıdır
    )

    # Token'ı direkt bellekte pickle'la
    pickle_buffer = BytesIO()
    pickle.dump(creds, pickle_buffer)
    pickle_data = pickle_buffer.getvalue()

    # Base64'e çevir
    base64_data = base64.b64encode(pickle_data).decode('utf-8')

    print('\n--- Kimlik Doğrulama Tamamlandı ---')
    print('Elde Edilen Refresh Token:', creds.refresh_token) # Artık None gelmemeli!
    print('Base64 kodlu token (Veritabanına kaydedilecek):')
    print(base64_data)
    print('\nBu Base64 kodlu stringi veritabanınıza kaydedin ve sunucu tarafında kullanın.')

# Async fonksiyonu çalıştır
if __name__ == "__main__":
    asyncio.run(get_token())