# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Configuración de la aplicación
# ═══════════════════════════════════════════════════════════════════════════

from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración de la aplicación usando Pydantic Settings"""
    
    # ═══════════════════════════════════════════════════════════════════════
    # APLICACIÓN
    # ═══════════════════════════════════════════════════════════════════════
    APP_NAME: str = "NovaGuardian"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # ═══════════════════════════════════════════════════════════════════════
    # SERVIDOR
    # ═══════════════════════════════════════════════════════════════════════
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"
    
    # ═══════════════════════════════════════════════════════════════════════
    # BASE DE DATOS
    # ═══════════════════════════════════════════════════════════════════════
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/novaguardian"
    DATABASE_ECHO: bool = False
    
    # ═══════════════════════════════════════════════════════════════════════
    # JWT
    # ═══════════════════════════════════════════════════════════════════════
    JWT_SECRET_KEY: str = "tu_clave_secreta_muy_segura_cambiar_en_produccion"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ═══════════════════════════════════════════════════════════════════════
    # REDIS
    # ═══════════════════════════════════════════════════════════════════════
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # ═══════════════════════════════════════════════════════════════════════
    # FIREBASE
    # ═══════════════════════════════════════════════════════════════════════
    FIREBASE_CREDENTIALS_PATH: str = "./firebase-credentials.json"
    
    # ═══════════════════════════════════════════════════════════════════════
    # CORS
    # ═══════════════════════════════════════════════════════════════════════
    CORS_ORIGINS: List[str] = [
        # Producción - GitHub Pages
        "https://www.novaguardian.online",
        "https://novaguardian.online",
        "https://h0m10.github.io",
        # Desarrollo local
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8081",
        "http://127.0.0.1:5173",
        # Expo (desarrollo móvil)
        "exp://localhost:8081",
    ]
    
    # ═══════════════════════════════════════════════════════════════════════
    # EMAIL
    # ═══════════════════════════════════════════════════════════════════════
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    
    # ═══════════════════════════════════════════════════════════════════════
    # TWILIO (SMS)
    # ═══════════════════════════════════════════════════════════════════════
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    
    # ═══════════════════════════════════════════════════════════════════════
    # ALERTAS
    # ═══════════════════════════════════════════════════════════════════════
    ALERT_CHECK_INTERVAL_SECONDS: int = 30
    VITAL_SIGNS_RETENTION_DAYS: int = 90
    
    # ═══════════════════════════════════════════════════════════════════════
    # UMBRALES POR DEFECTO PARA SIGNOS VITALES
    # ═══════════════════════════════════════════════════════════════════════
    DEFAULT_HEART_RATE_MIN: int = 50
    DEFAULT_HEART_RATE_MAX: int = 120
    DEFAULT_SPO2_MIN: int = 92
    DEFAULT_TEMPERATURE_MIN: float = 35.0
    DEFAULT_TEMPERATURE_MAX: float = 38.5
    DEFAULT_SYSTOLIC_BP_MIN: int = 90
    DEFAULT_SYSTOLIC_BP_MAX: int = 140
    DEFAULT_DIASTOLIC_BP_MIN: int = 60
    DEFAULT_DIASTOLIC_BP_MAX: int = 90
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Obtener configuración (cacheada)"""
    return Settings()


# Instancia global de configuración
settings = get_settings()
