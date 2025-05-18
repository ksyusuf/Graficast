from pydantic_settings import BaseSettings
from functools import lru_cache
import os
import base64
import tempfile
import json
from typing import Dict, Any, Optional

class Settings(BaseSettings):
    """Uygulama ayarları."""
    ENVIRONMENT: str = "development"
    MONGO_URI: str
    MONGO_DB_NAME: str
    API_KEY: str
    TOKEN_PATH: str = os.getenv("TOKEN_PATH", "/opt/render/project/src/token.pickle")
    
    # Google OAuth2 kimlik bilgileri
    GOOGLE_CREDENTIALS_JSON: str
    TOKEN_BASE64: Optional[str] = None  # Opsiyonel yaptık

    @property
    def google_credentials(self) -> Dict[str, Any]:
        """Google kimlik bilgilerini JSON'dan parse eder."""
        return json.loads(self.GOOGLE_CREDENTIALS_JSON)["web"]

    @property
    def token_path(self) -> str:
        """Token dosyasının yolunu döndürür."""
        if not hasattr(self, '_token_path'):
            # token.pickle yoksa base64'ten decode et
            if self.TOKEN_BASE64:
                # Base64'ten decode et
                token_data = base64.b64decode(self.TOKEN_BASE64)
                
                # Geçici dosya oluştur
                temp_dir = tempfile.gettempdir()
                self._token_path = os.path.join(temp_dir, 'token.pickle')
                
                # Token'ı geçici dosyaya yaz
                with open(self._token_path, 'wb') as f:
                    f.write(token_data)
            else:
                # Lokal geliştirme ortamında token.pickle dosyasını kullan
                self._token_path = 'token.pickle'
        
        return self._token_path

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    """Ayarları döndürür."""
    return Settings()
