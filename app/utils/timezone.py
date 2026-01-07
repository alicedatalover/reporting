# app/utils/timezone.py
"""
Gestion centralisée des timezones.

Utilise la timezone configurée dans settings (CELERY_TIMEZONE).
"""

from datetime import datetime, date
from zoneinfo import ZoneInfo


def _get_app_timezone() -> ZoneInfo:
    """
    Récupère la timezone depuis settings.

    Returns:
        ZoneInfo configurée
    """
    from app.config import settings
    return ZoneInfo(settings.CELERY_TIMEZONE)


def now_in_timezone() -> datetime:
    """
    Retourne l'heure actuelle dans le timezone de l'application.

    Returns:
        datetime avec timezone configurée
    """
    return datetime.now(_get_app_timezone())


def today_in_timezone() -> date:
    """
    Retourne la date d'aujourd'hui dans le timezone de l'application.

    Returns:
        date d'aujourd'hui
    """
    return now_in_timezone().date()


def to_app_timezone(dt: datetime) -> datetime:
    """
    Convertit un datetime vers le timezone de l'application.

    Args:
        dt: datetime à convertir (peut être naive ou aware)

    Returns:
        datetime dans le timezone de l'application
    """
    if dt.tzinfo is None:
        # Si naive, assumer qu'il est en UTC
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    return dt.astimezone(_get_app_timezone())
