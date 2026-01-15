"""
Configuration centralisée pour Genuka KPI Engine V2.
Charge les variables d'environnement depuis .env ou .env.docker.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
from datetime import date


class Settings(BaseSettings):
    """Configuration de l'application."""

    # ==================== APPLICATION ====================
    APP_NAME: str = Field(default="Genuka KPI Engine V2")
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    SECRET_KEY: str = Field(default="dev-secret-key")

    # ==================== DATABASE ====================
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=3306)
    DB_NAME: str = Field(default="genuka")
    DB_USER: str = Field(default="root")
    DB_PASSWORD: str = Field(default="")
    DB_CHARSET: str = Field(default="utf8mb4")

    # ==================== REDIS ====================
    REDIS_HOST: str = Field(default="redis")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)

    # ==================== GEMINI AI ====================
    GOOGLE_API_KEY: str = Field(default="")
    GEMINI_MODEL: str = Field(default="gemini-2.0-flash-exp")
    GEMINI_MAX_TOKENS: int = Field(default=300)
    GEMINI_TEMPERATURE: float = Field(default=0.7)

    # ==================== WHATSAPP ====================
    WHATSAPP_API_TOKEN: str = Field(default="")
    WHATSAPP_PHONE_NUMBER_ID: str = Field(default="")
    WHATSAPP_BUSINESS_ID: str = Field(default="")
    WHATSAPP_API_VERSION: str = Field(default="v21.0")

    # ==================== TELEGRAM ====================
    TELEGRAM_BOT_TOKEN: str = Field(default="")

    # ==================== CELERY ====================
    CELERY_BROKER_URL: str = Field(default="")
    CELERY_RESULT_BACKEND: str = Field(default="")
    CELERY_TIMEZONE: str = Field(default="Africa/Douala")

    # ==================== BUSINESS LOGIC ====================
    INACTIVE_DAYS_THRESHOLD: int = Field(
        default=30,
        description="Ne pas envoyer de rapport si pas de ventes depuis X jours"
    )
    MAX_INSIGHTS_PER_REPORT: int = Field(
        default=3,
        description="Nombre maximum d'insights par rapport"
    )
    CHURN_INACTIVE_DAYS: int = Field(
        default=45,
        description="Jours d'inactivité pour détecter churn client"
    )

    # ==================== LOGGING ====================
    LOG_LEVEL: str = Field(default="INFO")

    # ==================== CORS ====================
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000"
    )

    # ==================== TESTING ====================
    MOCK_CURRENT_DATE: Optional[str] = Field(
        default=None,
        description="Date simulée pour tests (format: YYYY-MM-DD)"
    )

    model_config = SettingsConfigDict(
        env_file=".env.docker",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # ==================== COMPUTED PROPERTIES ====================

    @property
    def DATABASE_URL(self) -> str:
        """URL de connexion MySQL async (aiomysql)."""
        password_part = f":{self.DB_PASSWORD}" if self.DB_PASSWORD else ""
        return (
            f"mysql+aiomysql://{self.DB_USER}{password_part}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset={self.DB_CHARSET}"
        )

    @property
    def REDIS_URL(self) -> str:
        """URL de connexion Redis."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def CELERY_BROKER_URL_COMPUTED(self) -> str:
        """URL broker Celery (utilise REDIS_URL si non défini)."""
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @property
    def CELERY_RESULT_BACKEND_COMPUTED(self) -> str:
        """URL backend Celery (utilise REDIS_URL si non défini)."""
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL

    @property
    def WHATSAPP_BASE_URL(self) -> str:
        """URL de base Meta Graph API."""
        return f"https://graph.facebook.com/{self.WHATSAPP_API_VERSION}"

    @property
    def CORS_ORIGINS_LIST(self) -> list[str]:
        """Parse les origines CORS depuis la string."""
        if not self.CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def get_current_date(self) -> date:
        """
        Retourne la date actuelle ou la date mockée pour tests.

        Returns:
            Date actuelle ou date simulée si MOCK_CURRENT_DATE est défini
        """
        if self.MOCK_CURRENT_DATE:
            from datetime import datetime
            return datetime.strptime(self.MOCK_CURRENT_DATE, "%Y-%m-%d").date()

        from datetime import datetime
        return datetime.now().date()


# Instance globale
settings = Settings()
