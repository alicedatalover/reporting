# tests/test_config.py
"""
Tests pour la configuration de l'application.
"""

import pytest
from app.config import Settings


def test_settings_loading():
    """Teste que les settings se chargent correctement depuis .env"""
    settings = Settings()

    # Vérifier que les valeurs sont chargées depuis .env
    assert settings.APP_NAME == "Genuka KPI Engine"
    assert settings.ENVIRONMENT == "development"
    assert settings.DEBUG is True
    assert settings.SECRET_KEY == "dev-secret-key-change-in-production-12345678"


def test_database_url():
    """Teste que l'URL de base de données est correctement construite"""
    settings = Settings()

    # Vérifier la construction de l'URL
    db_url = settings.DATABASE_URL
    assert "mysql+aiomysql://" in db_url
    assert "localhost:3306" in db_url
    assert "genuka" in db_url


def test_redis_url():
    """Teste que l'URL Redis est correctement construite"""
    settings = Settings()

    # Vérifier la construction de l'URL Redis
    redis_url = settings.REDIS_URL
    assert "redis://" in redis_url
    assert "localhost:6379" in redis_url


def test_environment_helpers():
    """Teste les méthodes helper pour l'environnement"""
    settings = Settings()

    # En mode development
    assert settings.is_development() is True
    assert settings.is_production() is False


def test_temperature_validation():
    """Teste la validation de la température Gemini"""
    # Température valide
    settings = Settings(GEMINI_TEMPERATURE=0.5)
    assert settings.GEMINI_TEMPERATURE == 0.5

    # Température invalide
    with pytest.raises(ValueError, match="Temperature must be between 0 and 1"):
        Settings(GEMINI_TEMPERATURE=1.5)


def test_max_insights_validation():
    """Teste la validation du nombre max d'insights"""
    # Valeur valide
    settings = Settings(MAX_INSIGHTS_PER_REPORT=5)
    assert settings.MAX_INSIGHTS_PER_REPORT == 5

    # Valeur invalide (trop grande)
    with pytest.raises(ValueError, match="MAX_INSIGHTS_PER_REPORT must be between 1 and 10"):
        Settings(MAX_INSIGHTS_PER_REPORT=20)

    # Valeur invalide (trop petite)
    with pytest.raises(ValueError, match="MAX_INSIGHTS_PER_REPORT must be between 1 and 10"):
        Settings(MAX_INSIGHTS_PER_REPORT=0)


def test_celery_broker_url_computed():
    """Teste que le broker Celery utilise Redis par défaut"""
    settings = Settings()

    # Si CELERY_BROKER_URL est défini dans .env, il devrait l'utiliser
    # Sinon, il devrait utiliser REDIS_URL
    broker_url = settings.CELERY_BROKER_URL_COMPUTED
    assert "redis://" in broker_url
    assert "localhost:6379" in broker_url
