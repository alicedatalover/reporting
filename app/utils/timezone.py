# app/utils/timezone.py
"""
Gestion centralisée des timezones.

Utilise Africa/Douala pour toutes les opérations de date/heure.
"""

from datetime import datetime, date
from zoneinfo import ZoneInfo

# Timezone par défaut pour l'application
DEFAULT_TIMEZONE = ZoneInfo("Africa/Douala")


def now_in_timezone() -> datetime:
    """
    Retourne l'heure actuelle dans le timezone de l'application.

    Returns:
        datetime avec timezone Africa/Douala
    """
    return datetime.now(DEFAULT_TIMEZONE)


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
        datetime dans le timezone Africa/Douala
    """
    if dt.tzinfo is None:
        # Si naive, assumer qu'il est en UTC
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    return dt.astimezone(DEFAULT_TIMEZONE)
