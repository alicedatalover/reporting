# app/workers/tasks/__init__.py
"""
Tâches Celery disponibles.
"""

from app.workers.tasks.report_generation import (
    generate_scheduled_reports,
    generate_single_report,
)

__all__ = [
    "generate_scheduled_reports",
    "generate_single_report",
]