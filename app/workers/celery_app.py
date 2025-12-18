# app/workers/celery_app.py
"""
Configuration Celery pour les tâches asynchrones.

Configure Celery avec Redis comme broker et backend,
et définit le planning des tâches automatiques.
"""

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init
import logging

from app.config import settings

# ==================== CONFIGURATION DU LOGGING ====================

@worker_process_init.connect
def configure_worker_logging(**kwargs):
    """
    Configure le logging lors de l'initialisation de chaque worker.
    
    Ce signal est déclenché quand un worker process démarre.
    C'est le bon endroit pour initialiser le logging de l'application.
    """
    from app.utils.logger import setup_logging
    
    # Initialiser le logging de l'application
    setup_logging()
    
    logger = logging.getLogger(__name__)
    logger.info(
        "Worker process initialized with custom logging",
        extra={
            "pid": kwargs.get("sender").pid if kwargs.get("sender") else None,
            "log_level": settings.LOG_LEVEL
        }
    )

# ==================== CELERY APP ====================

logger = logging.getLogger(__name__)

# Créer l'application Celery
celery_app = Celery(
    "genuka_kpi_engine",
    broker=settings.CELERY_BROKER_URL_COMPUTED,
    backend=settings.CELERY_RESULT_BACKEND_COMPUTED,
    include=["app.workers.tasks.report_generation"]
)

# Configuration Celery
celery_app.conf.update(
    # Timezone
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=True,
    
    # Sérialisation
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Résultats
    result_expires=3600 * 24,  # 24 heures
    result_backend_transport_options={
        "visibility_timeout": 3600,
    },
    
    # Workers
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Retry
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Logging - Format compatible avec app.utils.logger
    worker_log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    worker_task_log_format="%(asctime)s - %(name)s - %(levelname)s - [%(task_name)s(%(task_id)s)] %(message)s",
)

# Planification des tâches automatiques (Celery Beat)
celery_app.conf.beat_schedule = {
    # Rapports hebdomadaires - Tous les lundis à 8h
    "weekly-reports": {
        "task": "app.workers.tasks.report_generation.generate_scheduled_reports",
        "schedule": crontab(
            hour=8,
            minute=0,
            day_of_week=1  # Lundi
        ),
        "args": ["weekly"],
    },
    
    # Rapports mensuels - Le 1er de chaque mois à 9h
    "monthly-reports": {
        "task": "app.workers.tasks.report_generation.generate_scheduled_reports",
        "schedule": crontab(
            hour=9,
            minute=0,
            day_of_month=1
        ),
        "args": ["monthly"],
    },
    
    # Rapports trimestriels - Le 1er janv/avr/juil/oct à 10h
    "quarterly-reports": {
        "task": "app.workers.tasks.report_generation.generate_scheduled_reports",
        "schedule": crontab(
            hour=10,
            minute=0,
            day_of_month=1,
            month_of_year="1,4,7,10"
        ),
        "args": ["quarterly"],
    },
}

logger.info(
    "Celery app configured",
    extra={
        "broker": settings.REDIS_HOST,
        "timezone": settings.CELERY_TIMEZONE,
        "beat_schedule_count": len(celery_app.conf.beat_schedule)
    }
)