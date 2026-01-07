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
        default="gemini-2.5-flash",
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

    # ==================== CORS ====================
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000",
        description="Origines CORS autorisées (séparées par des virgules)"
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

    @property
    def CORS_ORIGINS_LIST(self) -> list[str]:
        """
        Parse les origines CORS depuis la string séparée par des virgules.

        Returns:
            Liste des origines autorisées
        """
        if not self.CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # ==================== VALIDATORS ====================

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """
        Valide que SECRET_KEY est définie et sécurisée.

        CRITIQUE en production !
        """
        environment = info.data.get("ENVIRONMENT", "development")

        # Production : SECRET_KEY obligatoire et forte
        if environment == "production":
            if not v or v == "change-me-in-production":
                raise ValueError(
                    "❌ SECRET_KEY OBLIGATOIRE en production ! "
                    "Générez une clé forte : python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )
            if len(v) < 32:
                raise ValueError(
                    "❌ SECRET_KEY trop courte en production ! "
                    f"Minimum 32 caractères, actuellement {len(v)}"
                )

        # Développement : Warning si default
        elif v == "change-me-in-production":
            import logging
            logging.warning("⚠️  SECRET_KEY utilise la valeur par défaut (OK en dev, INTERDIT en prod)")

        return v

    @field_validator("GOOGLE_API_KEY")
    @classmethod
    def validate_google_api_key(cls, v: str, info) -> str:
        """Valide GOOGLE_API_KEY si LLM activé"""
        enable_llm = info.data.get("ENABLE_LLM_RECOMMENDATIONS", True)

        if enable_llm and not v:
            import logging
            logging.warning(
                "⚠️  ENABLE_LLM_RECOMMENDATIONS=True mais GOOGLE_API_KEY vide ! "
                "Les recommandations utiliseront le fallback."
            )

        return v

    @field_validator("WHATSAPP_API_TOKEN")
    @classmethod
    def validate_whatsapp_token(cls, v: str, info) -> str:
        """Valide WHATSAPP_API_TOKEN si WhatsApp activé"""
        enable_wa = info.data.get("ENABLE_WHATSAPP_NOTIFICATIONS", True)

        if enable_wa and not v:
            import logging
            logging.warning(
                "⚠️  ENABLE_WHATSAPP_NOTIFICATIONS=True mais WHATSAPP_API_TOKEN vide ! "
                "Les notifications WhatsApp échoueront."
            )

        return v

    @field_validator("TELEGRAM_BOT_TOKEN")
    @classmethod
    def validate_telegram_token(cls, v: str, info) -> str:
        """Valide TELEGRAM_BOT_TOKEN si Telegram activé"""
        enable_tg = info.data.get("ENABLE_TELEGRAM_NOTIFICATIONS", True)

        if enable_tg and not v:
            import logging
            logging.warning(
                "⚠️  ENABLE_TELEGRAM_NOTIFICATIONS=True mais TELEGRAM_BOT_TOKEN vide ! "
                "Les notifications Telegram échoueront."
            )

        return v

    @field_validator("DB_PASSWORD")
    @classmethod
    def validate_db_password(cls, v: str, info) -> str:
        """Valide DB_PASSWORD en production"""
        environment = info.data.get("ENVIRONMENT", "development")

        if environment == "production" and not v:
            import logging
            logging.warning(
                "⚠️  DB_PASSWORD vide en production ! "
                "Base de données non sécurisée, FORTEMENT DÉCONSEILLÉ !"
            )

        return v

    @field_validator("GEMINI_TEMPERATURE")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Valide que la température est entre 0 et 1"""
        if not 0 <= v <= 1:
            raise ValueError("GEMINI_TEMPERATURE doit être entre 0 et 1")
        return v

    @field_validator("MAX_INSIGHTS_PER_REPORT")
    @classmethod
    def validate_max_insights(cls, v: int) -> int:
        """Valide le nombre d'insights"""
        if not 1 <= v <= 10:
            raise ValueError("MAX_INSIGHTS_PER_REPORT doit être entre 1 et 10")
        return v

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: str, info) -> str:
        """Valide les origines CORS en production"""
        environment = info.data.get("ENVIRONMENT", "development")

        if environment == "production":
            if "localhost" in v or "127.0.0.1" in v:
                raise ValueError(
                    "❌ CORS_ORIGINS contient localhost/127.0.0.1 en production ! "
                    "Utilisez uniquement les domaines de production (ex: https://app.genuka.com)"
                )

        return v

    def is_production(self) -> bool:
        """Vérifie si on est en production"""
        return self.ENVIRONMENT == "production"

    def is_development(self) -> bool:
        """Vérifie si on est en développement"""
        return self.ENVIRONMENT == "development"

    def validate_runtime_config(self) -> list[str]:
        """
        Valide la configuration au runtime et retourne les warnings.

        À appeler au démarrage de l'application.

        Returns:
            Liste de warnings (vide si tout OK)
        """
        warnings = []

        # Check Redis en production
        if self.is_production():
            if not self.REDIS_PASSWORD:
                warnings.append("⚠️  REDIS_PASSWORD vide en production (sécurité faible)")

            if self.DEBUG:
                warnings.append("⚠️  DEBUG=True en production (INTERDIT !)")

        return warnings


# Singleton settings
settings = Settings()