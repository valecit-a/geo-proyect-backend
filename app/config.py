"""
Configuración centralizada de la aplicación
Carga variables de entorno y configuraciones globales
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """Configuración de la aplicación"""
    
    # Base de datos
    DATABASE_URL: str
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "inmobiliario_db"
    DB_USER: str = "postgres"
    DB_PASSWORD: str
    
    # API
    API_TITLE: str = "API Inmobiliaria - Predicción de Precios"
    API_DESCRIPTION: str = "API REST para predicción de precios inmobiliarios usando ML con datos geoespaciales"
    API_VERSION: str = "1.0.0"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    RELOAD: bool = True
    
    # Seguridad
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ]
    
    # Modelo ML (opcional para desarrollo)
    MODEL_PATH: str = "/app/models/model.pkl"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


def get_settings() -> Settings:
    """Obtiene la configuración (sin cache para permitir hot-reload)"""
    return Settings()


# Instancia global
settings = get_settings()
