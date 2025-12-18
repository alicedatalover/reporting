# app/workers/__init__.py
"""
Workers Celery pour les tâches asynchrones.
"""

from app.workers.celery_app import celery_app

__all__ = ["celery_app"]