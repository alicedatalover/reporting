"""
Calculs des KPIs (Key Performance Indicators).
Cœur métier de l'application - Priorité #1.
"""

from datetime import date, timedelta
from typing import Tuple, Optional
import logging

from app.models import KPIData, KPIComparison, ReportFrequency
from app.core.database import (
    get_orders_for_period,
    get_order_products_for_period
)
from app.config import settings

logger = logging.getLogger(__name__)


def calculate_period_dates(
    frequency: ReportFrequency,
    end_date: Optional[date] = None
) -> Tuple[date, date]:
    """
    Calcule les dates de début et fin de période.

    Args:
        frequency: Fréquence du rapport (weekly/monthly)
        end_date: Date de fin (si None, utilise date actuelle/mockée)

    Returns:
        Tuple (start_date, end_date)

    Example:
        >>> calculate_period_dates(ReportFrequency.WEEKLY, date(2026, 1, 19))
        (date(2026, 1, 13), date(2026, 1, 19))
    """
    if end_date is None:
        end_date = settings.get_current_date()

    if frequency == ReportFrequency.WEEKLY:
        # Semaine = 7 jours (du lundi au dimanche)
        start_date = end_date - timedelta(days=6)
    else:  # MONTHLY
        # Début du mois de end_date
        start_date = end_date.replace(day=1)

    return start_date, end_date


def format_period_range(
    start_date: date,
    end_date: date,
    frequency: ReportFrequency
) -> str:
    """
    Formate la période pour affichage.

    Args:
        start_date: Date de début
        end_date: Date de fin
        frequency: Fréquence du rapport

    Returns:
        String formaté

    Example:
        >>> format_period_range(date(2026, 1, 13), date(2026, 1, 19), ReportFrequency.WEEKLY)
        "semaine du 13 au 19 janvier"
    """
    months_fr = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    ]

    if frequency == ReportFrequency.WEEKLY:
        if start_date.month == end_date.month:
            return f"semaine du {start_date.day} au {end_date.day} {months_fr[end_date.month - 1]}"
        else:
            return f"semaine du {start_date.day} {months_fr[start_date.month - 1]} au {end_date.day} {months_fr[end_date.month - 1]}"
    else:  # MONTHLY
        return f"mois de {months_fr[end_date.month - 1]} {end_date.year}"


async def calculate_kpis(
    company_id: str,
    start_date: date,
    end_date: date
) -> KPIData:
    """
    Calcule tous les KPIs pour une période donnée.

    Args:
        company_id: ID de l'entreprise
        start_date: Date de début
        end_date: Date de fin

    Returns:
        KPIData avec tous les KPIs calculés

    Example:
        >>> kpis = await calculate_kpis("01hjt9qsj7b039ww1nyrn9kg5t", date(2026, 1, 13), date(2026, 1, 19))
        >>> print(kpis.revenue)
        2450000.0
    """
    logger.info(
        f"Calculating KPIs for company {company_id}",
        extra={
            "company_id": company_id,
            "start_date": str(start_date),
            "end_date": str(end_date)
        }
    )

    # Récupérer les commandes de la période
    orders = await get_orders_for_period(
        company_id,
        str(start_date),
        str(end_date)
    )

    # Calculer les KPIs de base
    revenue = sum(order["amount"] for order in orders)
    orders_count = len(orders)
    avg_basket = revenue / orders_count if orders_count > 0 else 0
    unique_customers = len(set(
        order["customer_id"] for order in orders if order["customer_id"]
    ))

    # Récupérer les produits vendus
    products = await get_order_products_for_period(
        company_id,
        str(start_date),
        str(end_date)
    )

    # Top 3 produits
    top_products = [
        {
            "name": p["product_name"],
            "sales_count": p["sales_count"]
        }
        for p in products[:3]
    ]

    logger.info(
        f"KPIs calculated",
        extra={
            "company_id": company_id,
            "revenue": revenue,
            "orders_count": orders_count
        }
    )

    return KPIData(
        revenue=revenue,
        orders_count=orders_count,
        avg_basket=avg_basket,
        unique_customers=unique_customers,
        top_products=top_products
    )


async def compare_kpis(
    company_id: str,
    current_start: date,
    current_end: date,
    frequency: ReportFrequency
) -> KPIComparison:
    """
    Compare les KPIs avec la période précédente.

    Args:
        company_id: ID de l'entreprise
        current_start: Date de début période actuelle
        current_end: Date de fin période actuelle
        frequency: Fréquence du rapport

    Returns:
        KPIComparison avec évolutions en %

    Example:
        >>> comparison = await compare_kpis("01hjt9qsj7b039ww1nyrn9kg5t", ...)
        >>> print(comparison.revenue_evolution)
        18.5  # +18.5%
    """
    # Calculer les KPIs de la période actuelle
    current_kpis = await calculate_kpis(company_id, current_start, current_end)

    # Calculer les dates de la période précédente
    period_length = (current_end - current_start).days + 1
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=period_length - 1)

    # Calculer les KPIs de la période précédente
    previous_kpis = await calculate_kpis(company_id, previous_start, previous_end)

    # Calculer les évolutions en %
    def calculate_evolution(current: float, previous: float) -> float:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)

    return KPIComparison(
        revenue_evolution=calculate_evolution(
            current_kpis.revenue,
            previous_kpis.revenue
        ),
        orders_evolution=calculate_evolution(
            current_kpis.orders_count,
            previous_kpis.orders_count
        ),
        avg_basket_evolution=calculate_evolution(
            current_kpis.avg_basket,
            previous_kpis.avg_basket
        )
    )


async def get_last_year_comparison(
    company_id: str,
    start_date: date,
    end_date: date
) -> Optional[KPIData]:
    """
    Récupère les KPIs de la même période l'année dernière (pour recommandations Gemini).

    Args:
        company_id: ID de l'entreprise
        start_date: Date de début période actuelle
        end_date: Date de fin période actuelle

    Returns:
        KPIData de l'année dernière ou None si pas de données

    Example:
        >>> last_year = await get_last_year_comparison("01hjt9qsj7b039ww1nyrn9kg5t", ...)
        >>> if last_year:
        ...     print(f"CA année dernière : {last_year.revenue}")
    """
    try:
        # Même période il y a 365 jours
        last_year_start = start_date - timedelta(days=365)
        last_year_end = end_date - timedelta(days=365)

        kpis = await calculate_kpis(company_id, last_year_start, last_year_end)

        # Retourner None si pas de données
        if kpis.orders_count == 0:
            return None

        return kpis

    except Exception as e:
        logger.warning(
            f"Could not fetch last year comparison: {e}",
            extra={"company_id": company_id}
        )
        return None
