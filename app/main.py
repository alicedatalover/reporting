# app/main.py
"""
Point d'entrée de l'application FastAPI.

Configure l'application avec tous les routers et middleware.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.utils.logger import setup_logging
from app.infrastructure.database.connection import close_database_connection
from app.api.v1 import health, companies, configs, reports

# Configurer le logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestion du cycle de vie de l'application.
    
    Exécuté au démarrage et à l'arrêt de l'application.
    """
     # Startup
    logger.info(
        "Starting Genuka KPI Engine",
        extra={
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG
        }
    )
    
    # Initialiser la base de données
    from app.infrastructure.database.connection import init_database
    init_database()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Genuka KPI Engine")
    await close_database_connection()



# Créer l'application FastAPI
app = FastAPI(
    title="Genuka KPI Engine API",
    description="API pour la génération automatique de rapports d'activité",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)


# ==================== MIDDLEWARE ====================

# CORS - Origines configurées via CORS_ORIGINS dans .env
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ==================== ROUTERS ====================

# Health checks
app.include_router(health.router, prefix="/api/v1")

# Companies
app.include_router(companies.router, prefix="/api/v1")

# Report configs
app.include_router(configs.router, prefix="/api/v1")

# Reports
app.include_router(reports.router, prefix="/api/v1")


# ==================== ROOT ====================

@app.get("/")
async def root():
    """
    Endpoint racine.
    
    Returns:
        Message de bienvenue
    """
    return {
        "message": "Genuka KPI Engine API",
        "version": "1.0.0",
        "docs": "/docs" if settings.DEBUG else "disabled in production",
        "health": "/api/v1/health"
    }


# ==================== ERROR HANDLERS ====================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handler global pour les exceptions non gérées."""
    logger.error(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc)
        },
        exc_info=True
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )