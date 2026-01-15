"""
Connexion et opérations de base de données simplifiées.
Utilise SQLAlchemy avec aiomysql pour MySQL async.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy import text
from typing import List, Dict, Any, Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Engine global
engine = None
AsyncSessionLocal = None


def init_database():
    """Initialise la connexion à la base de données."""
    global engine, AsyncSessionLocal

    logger.info(
        "Initializing database connection",
        extra={
            "host": settings.DB_HOST,
            "database": settings.DB_NAME
        }
    )

    # Créer l'engine avec configuration optimisée
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=AsyncAdaptedQueuePool,
        pool_size=10,
        max_overflow=5,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=30,
        echo=settings.DEBUG,
        # Désactiver SSL pour connexion MySQL locale (Docker -> Windows host)
        connect_args={"ssl": None}
    )

    # Créer le session maker
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    logger.info("Database connection initialized")


async def get_session() -> AsyncSession:
    """Obtenir une session de base de données."""
    if AsyncSessionLocal is None:
        init_database()

    async with AsyncSessionLocal() as session:
        return session


async def execute_query(
    query: str,
    params: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Exécute une requête SELECT et retourne les résultats.

    Args:
        query: Requête SQL
        params: Paramètres de la requête

    Returns:
        Liste de dictionnaires (une par ligne)
    """
    if AsyncSessionLocal is None:
        init_database()

    async with AsyncSessionLocal() as session:
        result = await session.execute(text(query), params or {})
        rows = result.fetchall()

        # Convertir en liste de dict
        if rows:
            columns = result.keys()
            return [dict(zip(columns, row)) for row in rows]
        return []


async def execute_one(
    query: str,
    params: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Exécute une requête SELECT et retourne une seule ligne.

    Args:
        query: Requête SQL
        params: Paramètres de la requête

    Returns:
        Dictionnaire ou None
    """
    results = await execute_query(query, params)
    return results[0] if results else None


async def execute_insert(
    query: str,
    params: Optional[Dict[str, Any]] = None
) -> int:
    """
    Exécute une requête INSERT/UPDATE/DELETE.

    Args:
        query: Requête SQL
        params: Paramètres de la requête

    Returns:
        Nombre de lignes affectées
    """
    if AsyncSessionLocal is None:
        init_database()

    async with AsyncSessionLocal() as session:
        result = await session.execute(text(query), params or {})
        await session.commit()
        return result.rowcount


async def test_connection() -> bool:
    """
    Teste la connexion à la base de données.

    Returns:
        True si connexion OK
    """
    try:
        result = await execute_one("SELECT 1 as test")
        return result is not None
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


# ==================== FONCTIONS MÉTIER SIMPLIFIÉES ====================

async def get_company_info(company_id: str) -> Optional[Dict[str, Any]]:
    """Récupère les informations d'une entreprise."""
    query = """
        SELECT id, name, currency_code, whatsapp_number
        FROM companies
        WHERE id = :company_id
    """
    return await execute_one(query, {"company_id": company_id})


async def get_last_activity_date(company_id: str) -> Optional[str]:
    """
    Récupère la date de la dernière vente (commande non supprimée).

    Returns:
        Date au format ISO (YYYY-MM-DD) ou None
    """
    query = """
        SELECT MAX(DATE(created_at)) as last_activity
        FROM orders
        WHERE company_id = :company_id
          AND deleted_at IS NULL
    """
    result = await execute_one(query, {"company_id": company_id})
    return result["last_activity"] if result else None


async def get_orders_for_period(
    company_id: str,
    start_date: str,
    end_date: str
) -> List[Dict[str, Any]]:
    """Récupère les commandes d'une période (pour calculs KPIs)."""
    query = """
        SELECT
            id,
            customer_id,
            amount,
            created_at
        FROM orders
        WHERE company_id = :company_id
          AND DATE(created_at) BETWEEN :start_date AND :end_date
          AND deleted_at IS NULL
        ORDER BY created_at ASC
    """
    return await execute_query(query, {
        "company_id": company_id,
        "start_date": start_date,
        "end_date": end_date
    })


async def get_order_products_for_period(
    company_id: str,
    start_date: str,
    end_date: str
) -> List[Dict[str, Any]]:
    """Récupère les produits vendus dans une période (pour top produits)."""
    query = """
        SELECT
            p.id as product_id,
            p.title as product_name,
            COUNT(op.id) as sales_count,
            SUM(op.quantity) as total_quantity
        FROM order_product op
        JOIN orders o ON op.order_id = o.id
        JOIN products p ON op.product_id = p.id
        WHERE o.company_id = :company_id
          AND DATE(o.created_at) BETWEEN :start_date AND :end_date
          AND o.deleted_at IS NULL
        GROUP BY p.id, p.title
        ORDER BY sales_count DESC
        LIMIT 5
    """
    return await execute_query(query, {
        "company_id": company_id,
        "start_date": start_date,
        "end_date": end_date
    })


async def get_low_stock_products(company_id: str) -> List[Dict[str, Any]]:
    """Récupère les produits en alerte stock."""
    query = """
        SELECT
            s.id,
            s.title as product_name,
            sw.quantity as current_quantity,
            s.quantity_alert as alert_threshold
        FROM stocks s
        JOIN stock_warehouse sw ON s.id = sw.stock_id
        WHERE s.company_id = :company_id
          AND sw.quantity < s.quantity_alert
        ORDER BY (sw.quantity / s.quantity_alert) ASC
        LIMIT 10
    """
    return await execute_query(query, {"company_id": company_id})


async def get_inactive_customers(
    company_id: str,
    inactive_days: int
) -> List[Dict[str, Any]]:
    """Récupère les clients inactifs depuis X jours."""
    query = """
        SELECT
            c.id,
            c.first_name,
            c.last_name,
            c.phone,
            c.last_activity,
            DATEDIFF(NOW(), c.last_activity) as days_inactive
        FROM customers c
        WHERE c.company_id = :company_id
          AND c.last_activity IS NOT NULL
          AND DATEDIFF(NOW(), c.last_activity) > :inactive_days
          AND c.deleted_at IS NULL
        ORDER BY days_inactive DESC
        LIMIT 20
    """
    return await execute_query(query, {
        "company_id": company_id,
        "inactive_days": inactive_days
    })


async def close_database():
    """Ferme proprement les connexions à la base de données."""
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database connections closed")
