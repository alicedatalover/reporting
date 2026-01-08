# tests/conftest.py
"""
Fixtures globales pour tous les tests.

Fournit des fixtures réutilisables pour database, mocks, et données de test.
"""

import pytest
import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.domain.enums import ReportFrequency, DeliveryMethod, ReportStatus
from app.domain.models import ReportData, KPIs, Insight, KPIComparison


# ==================== PYTEST CONFIGURATION ====================

@pytest.fixture(scope="session")
def event_loop():
    """
    Fixture pour le event loop asyncio.

    Scope session pour réutiliser le même loop dans tous les tests.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== DATABASE FIXTURES ====================

@pytest.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    Crée un engine de test SQLite en mémoire.

    Note: En production, utiliser une vraie DB de test PostgreSQL.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=NullPool,
        echo=False
    )

    # Créer les tables (en vrai projet, utiliser Alembic migrations)
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Fournit une session de base de données pour chaque test.

    La session est rollback à la fin du test pour isolation.
    """
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        # Commencer une transaction
        async with session.begin():
            yield session
            # Rollback automatique à la fin du test
            await session.rollback()


# ==================== MOCK FIXTURES ====================

@pytest.fixture
def mock_redis():
    """Mock Redis client pour les tests."""
    redis_mock = MagicMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.incr.return_value = 1
    redis_mock.expire.return_value = True
    redis_mock.setex.return_value = True
    redis_mock.ping.return_value = True
    return redis_mock


@pytest.fixture
def mock_whatsapp_client():
    """Mock WhatsApp client pour les tests."""
    mock = AsyncMock()
    mock.send_message.return_value = True
    return mock


@pytest.fixture
def mock_telegram_client():
    """Mock Telegram client pour les tests."""
    mock = AsyncMock()
    mock.send_message.return_value = True
    return mock


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini AI client pour les tests."""
    mock = AsyncMock()
    mock.generate_recommendations.return_value = "Augmentez vos ventes de 20% en..."
    return mock


# ==================== DATA FIXTURES ====================

@pytest.fixture
def sample_company() -> Dict[str, Any]:
    """Données d'exemple pour une entreprise."""
    return {
        "id": "company_test_123",
        "name": "Boulangerie Test",
        "contact_phone": "+237658173627",
        "contact_email": "test@example.com",
        "created_at": datetime.now(),
        "deleted_at": None
    }


@pytest.fixture
def sample_orders() -> list[Dict[str, Any]]:
    """Données d'exemple pour des commandes."""
    today = date.today()
    return [
        {
            "id": f"order_{i}",
            "company_id": "company_test_123",
            "customer_id": f"customer_{i % 3}",
            "amount": Decimal("5000") + Decimal(i * 100),
            "status": "completed",
            "created_at": today - timedelta(days=i),
            "deleted_at": None
        }
        for i in range(10)
    ]


@pytest.fixture
def sample_kpis() -> KPIs:
    """KPIs d'exemple pour un rapport."""
    return KPIs(
        revenue=Decimal("50000"),
        sales_count=234,
        average_order_value=Decimal("213.68"),
        new_customers=45,
        returning_customers=28,
        churn_rate=12.5,
        top_products=[
            {"name": "Pain", "quantity": 150, "revenue": Decimal("7500")},
            {"name": "Croissant", "quantity": 89, "revenue": Decimal("4450")}
        ],
        low_stock_alerts=[
            {"name": "Farine", "quantity": 5, "threshold": 10}
        ]
    )


@pytest.fixture
def sample_insights() -> list[Insight]:
    """Insights d'exemple pour un rapport."""
    return [
        Insight(
            type="trend",
            message="📈 Revenus en hausse de +15%",
            priority="high"
        ),
        Insight(
            type="alert",
            message="⚠️ Stock de Farine critique (5 restants)",
            priority="medium"
        ),
        Insight(
            type="opportunity",
            message="💡 45 nouveaux clients ce mois",
            priority="low"
        )
    ]


@pytest.fixture
def sample_report_data(sample_kpis: KPIs, sample_insights: list[Insight]) -> ReportData:
    """ReportData complet d'exemple."""
    return ReportData(
        company_name="Boulangerie Test",
        period_name="Semaine 3",
        period_range="15/01 - 21/01/2026",
        kpis=sample_kpis,
        kpis_comparison=KPIComparison(
            revenue_change_percent=15.2,
            sales_change_percent=8.5,
            customer_change_percent=22.1
        ),
        insights=sample_insights,
        recommendations="Augmentez la production de Pain de 20% pour répondre à la demande croissante."
    )


@pytest.fixture
def mock_celery_task():
    """Mock Celery task pour les tests."""
    mock = MagicMock()
    mock.id = "task_test_123"
    mock.status = "PENDING"
    mock.ready.return_value = False
    mock.successful.return_value = False
    mock.failed.return_value = False
    return mock


# ==================== HELPER FIXTURES ====================

@pytest.fixture
def freeze_time():
    """
    Fixture pour figer le temps dans les tests.

    Usage:
        def test_something(freeze_time):
            with freeze_time("2026-01-15 10:00:00"):
                # Le temps est figé à cette date
                ...
    """
    from unittest.mock import patch
    from datetime import datetime

    class FreezeTime:
        def __call__(self, frozen_time: str):
            frozen_dt = datetime.fromisoformat(frozen_time)
            return patch('app.utils.timezone.today_in_timezone', return_value=frozen_dt.date())

    return FreezeTime()


@pytest.fixture
def assert_logs():
    """
    Fixture pour vérifier les logs dans les tests.

    Usage:
        def test_logging(assert_logs):
            with assert_logs('app.services.report_service', level='INFO') as logs:
                # Code qui log
                ...
            assert "Report generated" in logs.output
    """
    import logging
    from contextlib import contextmanager

    @contextmanager
    def _assert_logs(logger_name: str, level: str = 'INFO'):
        logger = logging.getLogger(logger_name)
        with patch.object(logger, level.lower()) as mock_log:
            yield mock_log

    return _assert_logs


# ==================== CLEANUP ====================

@pytest.fixture(autouse=True)
async def cleanup():
    """
    Fixture automatique pour nettoyer après chaque test.

    Exécutée automatiquement après chaque test.
    """
    yield
    # Cleanup code ici si nécessaire
    # Par exemple: fermer connexions, supprimer fichiers temporaires
