from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'sqlite:///./careerorbit.db'
    storage_dir: str = './storage'
    app_url: str = 'http://localhost:3000'
    api_url: str = 'http://localhost:8000'
    production: bool = False
    encryption_key: str = ''
    gmail_client_id: str = ''
    gmail_client_secret: str = ''
    outlook_client_id: str = ''
    outlook_client_secret: str = ''
    adzuna_app_id: str = ''
    adzuna_app_key: str = ''
    hunter_api_key: str = ''
    serpapi_api_key: str = ''
    llm_base_url: str = ''
    llm_api_key: str = ''
    llm_model: str = ''
    max_upload_mb: int = 10
    http_timeout: int = 25

settings = Settings()
Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)


def validate_runtime():
    if settings.production and (not settings.encryption_key or not settings.app_url.startswith('https://') or not settings.api_url.startswith('https://') or settings.database_url.startswith('sqlite')):
        raise RuntimeError('Production requires PostgreSQL, ENCRYPTION_KEY, HTTPS APP_URL and API_URL')
