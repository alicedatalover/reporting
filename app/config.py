# app/config.py
"""
Configuration centralisée de l'application Genuka KPI Engine.

Utilise Pydantic Settings pour la validation et le chargement depuis .env
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Literal
import os


class Settings(BaseSettings):
    """Configuration de l'application avec validation"""
    
    # ==================== APPLICATION ====================
    APP_NAME: str = Field(default="Genuka KPI Engine", description="Nom de l'application")
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Environnement d'exécution"
    )
    DEBUG: bool = Field(default=False, description="Mode debug")
    SECRET_KEY: str = Field(default="change-me-in-production", description="Clé secrète")
    
    # ==================== DATABASE ====================
    DB_HOST: str = Field(default="localhost", description="Host MySQL")
    DB_PORT: int = Field(default=3306, description="Port MySQL")
    DB_NAME: str = Field(default="genuka", description="Nom de la base")
    DB_USER: str = Field(default="root", description="Utilisateur MySQL")
    DB_PASSWORD: str = Field(default="", description="Mot de passe MySQL")
    DB_CHARSET: str = Field(default="utf8mb4", description="Charset MySQL")
    
    # ==================== REDIS ====================
    REDIS_HOST: str = Field(default="localhost", description="Host Redis")
    REDIS_PORT: int = Field(default=6379, description="Port Redis")
    REDIS_DB: int = Field(default=0, description="Numéro de DB Redis")
    REDIS_PASSWORD: str = Field(default="", description="Mot de passe Redis")
    
    # ==================== GEMINI AI ====================
    GOOGLE_API_KEY: str = Field(default="", description="Clé API Google Gemini")
    GEMINI_MODEL: str = Field(
        default="gemini-2.0-flash-exp",
        description="Modèle Gemini à utiliser"
    )
    GEMINI_MAX_TOKENS: int = Field(default=300, description="Tokens max pour recommandations")
    GEMINI_TEMPERATURE: float = Field(default=0.7, description="Température génération (0-1)")
    
    # ==================== WHATSAPP ====================
    WHATSAPP_API_TOKEN: str = Field(default="", description="Token Meta Business API")
    WHATSAPP_PHONE_NUMBER_ID: str = Field(default="", description="ID du numéro WhatsApp")
    WHATSAPP_BUSINESS_ID: str = Field(default="", description="ID Business Account")
    WHATSAPP_API_VERSION: str = Field(default="v21.0", description="Version API Graph")
    
    # ==================== TELEGRAM ====================
    TELEGRAM_BOT_TOKEN: str = Field(default="", description="Token du bot Telegram")
    
    # ==================== CELERY ====================
    CELERY_BROKER_URL: str = Field(default="", description="URL broker Celery (Redis)")
    CELERY_RESULT_BACKEND: str = Field(default="", description="Backend résultats Celery")
    CELERY_TIMEZONE: str = Field(default="Africa/Douala", description="Timezone Celery")
    
    # ==================== FEATURES ====================
    ENABLE_LLM_RECOMMENDATIONS: bool = Field(
        default=True,
        description="Activer les recommandations Gemini"
    )
    ENABLE_WHATSAPP_NOTIFICATIONS: bool = Field(
        default=True,
        description="Activer les notifications WhatsApp"
    )
    ENABLE_TELEGRAM_NOTIFICATIONS: bool = Field(
        default=True,
        description="Activer les notifications Telegram"
    )
    MAX_INSIGHTS_PER_REPORT: int = Field(
        default=3,
        description="Nombre max d'insights par rapport"
    )
    
    # ==================== LOGGING ====================
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Niveau de log"
    )
    LOG_FORMAT: Literal["json", "text"] = Field(
        default="json",
        description="Format des logs"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # ==================== COMPUTED PROPERTIES ====================
    
    @property
    def DATABASE_URL(self) -> str:
        """URL de connexion MySQL async"""
        password_part = f":{self.DB_PASSWORD}" if self.DB_PASSWORD else ""
        return (
            f"mysql+aiomysql://{self.DB_USER}{password_part}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset={self.DB_CHARSET}"
        )
    
    @property
    def REDIS_URL(self) -> str:
        """URL de connexion Redis"""
        password_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    @property
    def WHATSAPP_BASE_URL(self) -> str:
        """URL de base Meta Graph API"""
        return f"https://graph.facebook.com/{self.WHATSAPP_API_VERSION}"
    
    @property
    def CELERY_BROKER_URL_COMPUTED(self) -> str:
        """URL broker Celery (utilise REDIS_URL si non défini)"""
        return self.CELERY_BROKER_URL or self.REDIS_URL
    
    @property
    def CELERY_RESULT_BACKEND_COMPUTED(self) -> str:
        """URL backend Celery (utilise REDIS_URL si non défini)"""
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL
    
    # ==================== VALIDATORS ====================
    
    @field_validator("GEMINI_TEMPERATURE")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Valide que la température est entre 0 et 1"""
        if not 0 <= v <= 1:
            raise ValueError("Temperature must be between 0 and 1")
        return v
    
    @field_validator("MAX_INSIGHTS_PER_REPORT")
    @classmethod
    def validate_max_insights(cls, v: int) -> int:
        """Valide le nombre d'insights"""
        if not 1 <= v <= 10:
            raise ValueError("MAX_INSIGHTS_PER_REPORT must be between 1 and 10")
        return v
    
    def is_production(self) -> bool:
        """Vérifie si on est en production"""
        return self.ENVIRONMENT == "production"
    
    def is_development(self) -> bool:
        """Vérifie si on est en développement"""
        return self.ENVIRONMENT == "development"


# Singleton settings
settings = Settings()