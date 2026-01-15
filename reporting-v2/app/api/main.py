"""
Application FastAPI principale.
Point d'entrée de l'API REST.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.core.database import init_database, close_database
from app.api import routes

# Configuration du logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gère le cycle de vie de l'application (startup/shutdown).
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Initialiser la connexion DB
    init_database()
    logger.info("Database connection initialized")

    yield

    # Shutdown
    logger.info("Shutting down application")
    await close_database()


# Créer l'application FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    description="Système de génération et envoi automatique de rapports d'activité avec insights et recommandations IA",
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclure les routes
app.include_router(routes.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check simple."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "2.0.0",
        "environment": settings.ENVIRONMENT
    }


@app.get("/")
async def root():
    """Page d'accueil."""
    return {
        "message": f"Bienvenue sur {settings.APP_NAME}",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
