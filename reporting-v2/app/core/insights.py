"""
Extraction d'insights (data mining).
Détecte des patterns et anomalies dans les données.
Priorité #1 - C'est ici que vous ajouterez vos algorithmes de data mining.
"""

from datetime import date
from typing import List
import logging

from app.models import Insight, InsightType
from app.core.database import (
    get_low_stock_products,
    get_inactive_customers,
    get_order_products_for_period,
    get_orders_for_period
)
from app.config import settings

logger = logging.getLogger(__name__)


async def extract_all_insights(
    company_id: str,
    start_date: date,
    end_date: date
) -> List[Insight]:
    """
    Extrait tous les insights pour une période.

    Args:
        company_id: ID de l'entreprise
        start_date: Date de début
        end_date: Date de fin

    Returns:
        Liste d'insights triés par priorité (severity)

    Example:
        >>> insights = await extract_all_insights("01hjt9qsj7b039ww1nyrn9kg5t", ...)
        >>> for insight in insights[:3]:  # Top 3
        ...     print(insight.message)
    """
    insights = []

    # 1. Stock Alerts (critique)
    stock_insights = await detect_stock_alerts(company_id)
    insights.extend(stock_insights)

    # 2. Churn Risk (important)
    churn_insights = await detect_churn_risk(company_id)
    insights.extend(churn_insights)

    # 3. Seasonality (informatif)
    seasonality_insights = await detect_seasonality(
        company_id, start_date, end_date
    )
    insights.extend(seasonality_insights)

    # 4. Profit Margin (stratégique)
    # TODO: À implémenter si vous voulez analyser les marges
    # profit_insights = await detect_profit_margins(company_id, start_date, end_date)
    # insights.extend(profit_insights)

    # Trier par priorité (severity) décroissante
    insights.sort(key=lambda x: x.severity, reverse=True)

    logger.info(
        f"Extracted {len(insights)} insights",
        extra={
            "company_id": company_id,
            "insights_count": len(insights)
        }
    )

    # Limiter au nombre max configuré
    return insights[:settings.MAX_INSIGHTS_PER_REPORT]


async def detect_stock_alerts(company_id: str) -> List[Insight]:
    """
    Détecte les produits en alerte stock.

    Returns:
        Liste d'insights de type STOCK_ALERT
    """
    low_stock = await get_low_stock_products(company_id)

    if not low_stock:
        return []

    # Compter les produits en rupture
    count = len(low_stock)

    # Formater les noms des produits (max 3)
    product_names = [p["product_name"] for p in low_stock[:3]]
    products_str = ", ".join(product_names)

    # Créer l'insight
    if count == 1:
        message = f"{products_str} risque la rupture de stock"
    elif count <= 3:
        message = f"{count} produits risquent la rupture de stock : {products_str}"
    else:
        message = f"{count} produits risquent la rupture de stock : {products_str}, et {count - 3} autres"

    return [Insight(
        type=InsightType.STOCK_ALERT,
        message=message,
        severity=5,  # Critique
        data={
            "products_count": count,
            "products": low_stock
        }
    )]


async def detect_churn_risk(company_id: str) -> List[Insight]:
    """
    Détecte les clients à risque de churn (inactifs depuis X jours).

    Returns:
        Liste d'insights de type CHURN_RISK
    """
    inactive = await get_inactive_customers(
        company_id,
        settings.CHURN_INACTIVE_DAYS
    )

    if not inactive:
        return []

    count = len(inactive)

    # Créer l'insight
    if count == 1:
        message = f"1 client fidèle n'a pas commandé depuis {settings.CHURN_INACTIVE_DAYS} jours"
    else:
        message = f"{count} clients fidèles n'ont pas commandé depuis {settings.CHURN_INACTIVE_DAYS} jours"

    return [Insight(
        type=InsightType.CHURN_RISK,
        message=message,
        severity=4,  # Important
        data={
            "customers_count": count,
            "customers": inactive[:10]  # Limiter la data
        }
    )]


async def detect_seasonality(
    company_id: str,
    start_date: date,
    end_date: date
) -> List[Insight]:
    """
    Détecte des patterns de saisonnalité (jours forts, produits tendances).

    Returns:
        Liste d'insights de type SEASONALITY
    """
    insights = []

    # Récupérer les commandes de la période
    orders = await get_orders_for_period(
        company_id,
        str(start_date),
        str(end_date)
    )

    if not orders:
        return []

    # Analyser les jours de la semaine
    from collections import Counter
    from datetime import datetime

    days_counter = Counter()
    for order in orders:
        weekday = order["created_at"].weekday()  # 0=lundi, 6=dimanche
        days_counter[weekday] += 1

    # Total des commandes (pour calculs de pourcentage)
    total_orders = len(orders)

    # Trouver les jours les plus actifs
    if days_counter and total_orders > 0:
        most_common = days_counter.most_common(2)

        # Si 50%+ des ventes sur 2 jours
        top_2_sales = sum(count for _, count in most_common)
        if top_2_sales / total_orders >= 0.5:
            days_names_fr = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
            top_days = [days_names_fr[day] for day, _ in most_common]
            percentage = int((top_2_sales / total_orders) * 100)

            insights.append(Insight(
                type=InsightType.SEASONALITY,
                message=f"{percentage}% de vos ventes sont concentrées {'-'.join(top_days)}",
                severity=3,  # Informatif
                data={
                    "top_days": top_days,
                    "percentage": percentage,
                    "distribution": dict(days_counter)
                }
            ))

        # Analyser les baisses en milieu de semaine (mardi-mercredi)
        tuesday_wednesday = days_counter.get(1, 0) + days_counter.get(2, 0)
        if tuesday_wednesday < (total_orders * 0.15):  # Moins de 15% des ventes
            insights.append(Insight(
                type=InsightType.SEASONALITY,
                message="Vos ventes chutent particulièrement en milieu de semaine (mardi-mercredi)",
                severity=3,
                data={"midweek_percentage": int((tuesday_wednesday / total_orders) * 100)}
            ))

    return insights


# ==================== HELPERS ====================

def select_top_insights(
    insights: List[Insight],
    max_count: int = 3
) -> List[Insight]:
    """
    Sélectionne les insights les plus pertinents.

    Args:
        insights: Liste complète d'insights
        max_count: Nombre maximum à retourner

    Returns:
        Top insights triés par severity
    """
    # Trier par priorité
    sorted_insights = sorted(insights, key=lambda x: x.severity, reverse=True)

    # Prioriser les types critiques (stock > churn > seasonality)
    priority_order = {
        InsightType.STOCK_ALERT: 4,
        InsightType.CHURN_RISK: 3,
        InsightType.PROFIT_MARGIN: 2,
        InsightType.SEASONALITY: 1
    }

    sorted_insights.sort(
        key=lambda x: (x.severity, priority_order.get(x.type, 0)),
        reverse=True
    )

    return sorted_insights[:max_count]
