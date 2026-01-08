# app/utils/date_utils.py
"""
Utilitaires pour la gestion des dates.

Fournit des fonctions pour calculer les périodes de rapports.
"""

from datetime import date, timedelta
from typing import Tuple
import logging

from app.domain.enums import ReportFrequency

logger = logging.getLogger(__name__)


def calculate_period_dates(
    frequency: ReportFrequency,
    end_date: date
) -> Tuple[date, date]:
    """
    Calcule les dates de début et fin pour une période de rapport.

    Implémente la logique de calcul de période pour chaque fréquence:
    - WEEKLY: 7 jours (du lundi au dimanche)
    - MONTHLY: Du 1er au dernier jour du mois
    - QUARTERLY: 3 mois complets (trimestre)

    Args:
        frequency: Fréquence du rapport (WEEKLY, MONTHLY, QUARTERLY)
        end_date: Date de fin de la période

    Returns:
        Tuple (start_date, end_date) avec les dates calculées

    Raises:
        ValueError: Si la fréquence est invalide

    Example:
        >>> from datetime import date
        >>> end = date(2025, 7, 31)
        >>> start, end = calculate_period_dates(ReportFrequency.MONTHLY, end)
        >>> print(start, end)
        2025-07-01 2025-07-31
    """
    if not isinstance(frequency, ReportFrequency):
        raise ValueError(f"Invalid frequency type: {type(frequency)}")

    if frequency == ReportFrequency.WEEKLY:
        # 7 derniers jours (inclus)
        start_date = end_date - timedelta(days=6)

    elif frequency == ReportFrequency.MONTHLY:
        # Du 1er jour du mois à end_date
        start_date = end_date.replace(day=1)

    elif frequency == ReportFrequency.QUARTERLY:
        # Début du trimestre (mois 1, 4, 7, 10)
        quarter_month = ((end_date.month - 1) // 3) * 3 + 1
        try:
            start_date = end_date.replace(month=quarter_month, day=1)
        except ValueError as e:
            logger.error(
                f"Failed to calculate quarterly start date: {e}",
                extra={"end_date": end_date, "quarter_month": quarter_month}
            )
            # Fallback: utiliser 3 mois en arrière
            start_date = end_date - timedelta(days=90)

    else:
        raise ValueError(f"Unsupported frequency: {frequency}")

    logger.debug(
        f"Calculated period for {frequency.value}: {start_date} to {end_date}"
    )

    return start_date, end_date
