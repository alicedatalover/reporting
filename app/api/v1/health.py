# app/api/v1/health.py
"""
Endpoints de health check.

Vérifie l'état de santé de l'application et ses dépendances.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import logging
import redis.asyncio as redis

from app.infrastructure.database.connection import (
    get_db_session,
    check_database_connection
)
from app.infrastructure.external.gemini_client import GeminiClient
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
async def health_check() -> Dict[str, str]:
    """
    Health check basique.
    
    Returns:
        Status de l'API
    """
    return {
        "status": "healthy",
        "service": "Genuka KPI Engine",
        "version": "1.0.0"
    }


@router.get("/detailed")
async def detailed_health_check(
    session: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Health check détaillé avec vérification des dépendances.
    
    Returns:
        Status détaillé de tous les composants
    """
    
    health_status = {
        "status": "healthy",
        "checks": {}
    }
    
    # Vérifier la base de données
    try:
        db_ok = await check_database_connection()
        health_status["checks"]["database"] = {
            "status": "healthy" if db_ok else "unhealthy",
            "host": settings.DB_HOST,
            "database": settings.DB_NAME
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Vérifier Gemini
    if settings.GOOGLE_API_KEY:
        try:
            gemini_client = GeminiClient(settings)
            gemini_ok = await gemini_client.test_connection()
            health_status["checks"]["gemini"] = {
                "status": "healthy" if gemini_ok else "unhealthy",
                "model": settings.GEMINI_MODEL
            }
        except Exception as e:
            health_status["checks"]["gemini"] = {
                "status": "unhealthy",
                "error": str(e)
            }
    else:
        health_status["checks"]["gemini"] = {
            "status": "disabled",
            "reason": "No API key configured"
    }
    
    # Vérifier Redis (Celery)
    if settings.REDIS_HOST:
        try:
            client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )
            ok = await client.ping()
            health_status["checks"]["celery"] = {
                "status": "healthy" if ok else "unhealthy",
                "broker": settings.REDIS_URL
            }
        except Exception as e:
            health_status["checks"]["celery"] = {
                "status": "unhealthy",
                "broker": settings.REDIS_URL,
                "error": str(e)
            }
            health_status["status"] = "unhealthy"
        finally:
            try:
                await client.close()
            except Exception:
                pass
    else:
        health_status["checks"]["celery"] = {
            "status": "not_configured",
            "broker": None
        }
    
    # Vérifier WhatsApp
    health_status["checks"]["whatsapp"] = {
        "status": "configured" if settings.WHATSAPP_API_TOKEN else "not_configured",
        "enabled": settings.ENABLE_WHATSAPP_NOTIFICATIONS
    }
    
    # Vérifier Telegram
    health_status["checks"]["telegram"] = {
        "status": "configured" if settings.TELEGRAM_BOT_TOKEN else "not_configured",
        "enabled": settings.ENABLE_TELEGRAM_NOTIFICATIONS
    }
    
    return health_status
