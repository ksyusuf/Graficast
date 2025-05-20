from pydantic_settings import BaseSettings
from functools import lru_cache
import os
import json
from typing import Dict, Any

class Settings(BaseSettings):
    """Uygulama ayarları."""
    ENVIRONMENT: str = "development"
    MONGO_URI: str
    MONGO_DB_NAME: str
    API_KEY: str
    TOKEN_PATH: str = os.getenv("TOKEN_PATH", "/opt/render/project/src/token.pickle")
    
    # Google OAuth2 kimlik bilgileri
    GOOGLE_CREDENTIALS_JSON: str

    @property
    def google_credentials(self) -> Dict[str, Any]:
        """Google kimlik bilgilerini JSON'dan parse eder."""
        return json.loads(self.GOOGLE_CREDENTIALS_JSON)["web"]

    @property
    def token_path(self) -> str:
        """Token dosyasının yolunu döndürür."""
        if not hasattr(self, '_token_path'):
            self._token_path = 'token.pickle'
        return self._token_path

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    """Ayarları döndürür."""
    return Settings()
