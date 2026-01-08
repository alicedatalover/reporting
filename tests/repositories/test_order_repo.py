# tests/repositories/test_order_repo.py
"""
Tests pour OrderRepository.

Vérifie les requêtes SQL, les optimisations, et la gestion des erreurs.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.infrastructure.repositories.order_repo import OrderRepository


class TestOrderRepository:
    """Tests pour OrderRepository"""

    @pytest.fixture
    def order_repo(self, db_session):
        """Fixture pour créer un OrderRepository avec une session de test."""
        return OrderRepository(db_session)

    # ==================== Tests get_by_id ====================

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, order_repo):
        """Test récupération d'une commande existante."""
        # Mock de _fetch_one
        expected_order = {
            "id": "order_123",
            "company_id": "company_456",
            "customer_id": "customer_789",
            "amount": Decimal("5000"),
            "status": "completed"
        }

        with patch.object(order_repo, '_fetch_one', return_value=expected_order):
            result = await order_repo.get_by_id("order_123")

        assert result is not None
        assert result["id"] == "order_123"
        assert result["amount"] == Decimal("5000")

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, order_repo):
        """Test récupération d'une commande inexistante."""
        with patch.object(order_repo, '_fetch_one', return_value=None):
            result = await order_repo.get_by_id("nonexistent")

        assert result is None

    # ==================== Tests exists ====================

    @pytest.mark.asyncio
    async def test_exists_true(self, order_repo):
        """Test vérification existence d'une commande."""
        with patch.object(order_repo, '_execute_scalar', return_value=1):
            result = await order_repo.exists("order_123")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, order_repo):
        """Test vérification non-existence."""
        with patch.object(order_repo, '_execute_scalar', return_value=0):
            result = await order_repo.exists("nonexistent")

        assert result is False

    # ==================== Tests fetch_orders_for_period ====================

    @pytest.mark.asyncio
    async def test_fetch_orders_for_period(self, order_repo):
        """Test récupération des commandes pour une période."""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)

        mock_orders = [
            {"id": "order_1", "amount": Decimal("1000")},
            {"id": "order_2", "amount": Decimal("2000")}
        ]

        with patch.object(order_repo, '_execute_query', return_value=mock_orders):
            result = await order_repo.fetch_orders_for_period(
                "company_123",
                start_date,
                end_date,
                limit=10
            )

        assert len(result) == 2
        assert result[0]["id"] == "order_1"

    @pytest.mark.asyncio
    async def test_fetch_orders_with_pagination(self, order_repo):
        """Test pagination des commandes."""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)

        with patch.object(order_repo, '_execute_query', return_value=[]) as mock_query:
            await order_repo.fetch_orders_for_period(
                "company_123",
                start_date,
                end_date,
                limit=50,
                offset=100
            )

            # Vérifier que limit et offset sont passés
            call_args = mock_query.call_args
            assert call_args[0][1]["limit"] == 50
            assert call_args[0][1]["offset"] == 100

    @pytest.mark.asyncio
    async def test_fetch_orders_no_limit(self, order_repo):
        """Test récupération sans limite."""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)

        with patch.object(order_repo, '_execute_query', return_value=[]) as mock_query:
            await order_repo.fetch_orders_for_period(
                "company_123",
                start_date,
                end_date,
                limit=None
            )

            # Vérifier que limit n'est pas dans les params
            call_args = mock_query.call_args
            assert "limit" not in call_args[0][1]

    # ==================== Tests calculate_revenue_for_period ====================

    @pytest.mark.asyncio
    async def test_calculate_revenue_success(self, order_repo):
        """Test calcul du revenue avec succès."""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)

        with patch.object(order_repo, '_execute_scalar', return_value=50000):
            result = await order_repo.calculate_revenue_for_period(
                "company_123",
                start_date,
                end_date
            )

        assert result == Decimal("50000")
        assert isinstance(result, Decimal)

    @pytest.mark.asyncio
    async def test_calculate_revenue_zero(self, order_repo):
        """Test calcul revenue quand aucune vente."""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)

        with patch.object(order_repo, '_execute_scalar', return_value=0):
            result = await order_repo.calculate_revenue_for_period(
                "company_123",
                start_date,
                end_date
            )

        assert result == Decimal("0")

    @pytest.mark.asyncio
    async def test_calculate_revenue_none_result(self, order_repo):
        """Test calcul revenue avec résultat None."""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)

        with patch.object(order_repo, '_execute_scalar', return_value=None):
            result = await order_repo.calculate_revenue_for_period(
                "company_123",
                start_date,
                end_date
            )

        assert result == Decimal("0")

    @pytest.mark.asyncio
    async def test_calculate_revenue_invalid_conversion(self, order_repo):
        """Test gestion d'erreur lors conversion Decimal."""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)

        # Retourner une valeur invalide qui causera une erreur
        with patch.object(order_repo, '_execute_scalar', return_value="invalid_number"):
            result = await order_repo.calculate_revenue_for_period(
                "company_123",
                start_date,
                end_date
            )

        # Doit retourner 0 au lieu de crasher
        assert result == Decimal("0")

    # ==================== Tests count_sales_for_period ====================

    @pytest.mark.asyncio
    async def test_count_sales_success(self, order_repo):
        """Test comptage des ventes."""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)

        with patch.object(order_repo, '_execute_scalar', return_value=234):
            result = await order_repo.count_sales_for_period(
                "company_123",
                start_date,
                end_date
            )

        assert result == 234
        assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_count_sales_zero(self, order_repo):
        """Test comptage avec zéro ventes."""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)

        with patch.object(order_repo, '_execute_scalar', return_value=0):
            result = await order_repo.count_sales_for_period(
                "company_123",
                start_date,
                end_date
            )

        assert result == 0

    @pytest.mark.asyncio
    async def test_count_sales_none_result(self, order_repo):
        """Test comptage avec résultat None."""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)

        with patch.object(order_repo, '_execute_scalar', return_value=None):
            result = await order_repo.count_sales_for_period(
                "company_123",
                start_date,
                end_date
            )

        assert result == 0

    # ==================== Tests get_top_selling_products ====================

    @pytest.mark.asyncio
    async def test_get_top_selling_products(self, order_repo):
        """Test récupération des produits les plus vendus."""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)

        mock_products = [
            {
                "product_variant_id": "prod_1",
                "product_name": "Pain",
                "total_quantity": 150,
                "total_revenue": Decimal("7500")
            },
            {
                "product_variant_id": "prod_2",
                "product_name": "Croissant",
                "total_quantity": 89,
                "total_revenue": Decimal("4450")
            }
        ]

        with patch.object(order_repo, '_execute_query', return_value=mock_products):
            result = await order_repo.get_top_selling_products(
                "company_123",
                start_date,
                end_date,
                limit=10
            )

        assert len(result) == 2
        assert result[0]["product_name"] == "Pain"
        assert result[0]["total_quantity"] == 150

    # ==================== Tests calculate_sales_kpis ====================

    @pytest.mark.asyncio
    async def test_calculate_sales_kpis_success(self, order_repo):
        """Test calcul des KPIs de vente (optimisé en une requête)."""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)

        mock_result = {
            "total_revenue": 50000,
            "total_sales": 234
        }

        with patch.object(order_repo, '_fetch_one', return_value=mock_result):
            result = await order_repo.calculate_sales_kpis(
                "company_123",
                start_date,
                end_date
            )

        assert result["total_revenue"] == Decimal("50000")
        assert result["total_sales"] == 234
        assert isinstance(result["total_revenue"], Decimal)
        assert isinstance(result["total_sales"], int)

    @pytest.mark.asyncio
    async def test_calculate_sales_kpis_zero(self, order_repo):
        """Test KPIs avec aucune vente."""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)

        mock_result = {
            "total_revenue": 0,
            "total_sales": 0
        }

        with patch.object(order_repo, '_fetch_one', return_value=mock_result):
            result = await order_repo.calculate_sales_kpis(
                "company_123",
                start_date,
                end_date
            )

        assert result["total_revenue"] == Decimal("0")
        assert result["total_sales"] == 0

    @pytest.mark.asyncio
    async def test_calculate_sales_kpis_none_result(self, order_repo):
        """Test KPIs avec résultat None."""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)

        with patch.object(order_repo, '_fetch_one', return_value=None):
            result = await order_repo.calculate_sales_kpis(
                "company_123",
                start_date,
                end_date
            )

        assert result["total_revenue"] == Decimal("0")
        assert result["total_sales"] == 0

    @pytest.mark.asyncio
    async def test_calculate_sales_kpis_invalid_revenue(self, order_repo):
        """Test gestion d'erreur conversion revenue dans KPIs."""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)

        mock_result = {
            "total_revenue": "invalid_decimal",
            "total_sales": 234
        }

        with patch.object(order_repo, '_fetch_one', return_value=mock_result):
            result = await order_repo.calculate_sales_kpis(
                "company_123",
                start_date,
                end_date
            )

        # Revenue doit fallback à 0
        assert result["total_revenue"] == Decimal("0")
        # Sales count reste valide
        assert result["total_sales"] == 234

    @pytest.mark.asyncio
    async def test_calculate_sales_kpis_invalid_sales_count(self, order_repo):
        """Test gestion d'erreur conversion sales count dans KPIs."""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)

        mock_result = {
            "total_revenue": 50000,
            "total_sales": "not_a_number"
        }

        with patch.object(order_repo, '_fetch_one', return_value=mock_result):
            result = await order_repo.calculate_sales_kpis(
                "company_123",
                start_date,
                end_date
            )

        # Revenue reste valide
        assert result["total_revenue"] == Decimal("50000")
        # Sales count doit fallback à 0
        assert result["total_sales"] == 0

    # ==================== Tests SQL Optimization ====================

    @pytest.mark.asyncio
    async def test_date_range_uses_exclusive_end(self, order_repo):
        """
        Test que les requêtes utilisent end_date + 1 jour (exclusif).

        Ceci permet d'utiliser les index sur created_at au lieu de DATE().
        """
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)
        expected_end_exclusive = date(2026, 1, 8)

        with patch.object(order_repo, '_execute_scalar', return_value=0) as mock_scalar:
            await order_repo.count_sales_for_period(
                "company_123",
                start_date,
                end_date
            )

            # Vérifier que end_date_exclusive est passé
            call_args = mock_scalar.call_args
            assert call_args[0][1]["end_date_exclusive"] == expected_end_exclusive

    @pytest.mark.asyncio
    async def test_excludes_cancelled_orders(self, order_repo):
        """Test que les commandes annulées sont exclues."""
        # Ce test vérifie indirectement via le comportement
        # En production, les cancelled doivent être exclus des KPIs
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)

        with patch.object(order_repo, '_execute_query') as mock_query:
            await order_repo.fetch_orders_for_period(
                "company_123",
                start_date,
                end_date
            )

            # Vérifier que la requête contient la clause status != 'cancelled'
            query_sql = mock_query.call_args[0][0]
            assert "status != 'cancelled'" in query_sql or "status <> 'cancelled'" in query_sql

    @pytest.mark.asyncio
    async def test_excludes_soft_deleted_orders(self, order_repo):
        """Test que les commandes soft-deleted sont exclues."""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 7)

        with patch.object(order_repo, '_execute_query') as mock_query:
            await order_repo.fetch_orders_for_period(
                "company_123",
                start_date,
                end_date
            )

            # Vérifier que deleted_at IS NULL est dans la requête
            query_sql = mock_query.call_args[0][0]
            assert "deleted_at IS NULL" in query_sql
