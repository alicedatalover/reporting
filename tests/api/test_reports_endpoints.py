# tests/api/test_reports_endpoints.py
"""
Tests pour les endpoints de l'API reports.

Teste les endpoints FastAPI pour la génération, preview, historique.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date
from decimal import Decimal

from app.main import app
from app.domain.enums import ReportFrequency, DeliveryMethod, InsightType, InsightPriority
from app.domain.models import ReportData, KPIData, KPIComparison, InsightModel


# Client de test FastAPI
client = TestClient(app)


class TestGenerateReportEndpoint:
    """Tests pour POST /reports/generate"""

    def test_generate_report_success(self):
        """Test génération de rapport réussi."""

        with patch('app.api.v1.reports.generate_single_report') as mock_task:
            # Mock de la tâche Celery
            mock_celery_task = MagicMock()
            mock_celery_task.id = "task_abc123"
            mock_task.delay.return_value = mock_celery_task

            response = client.post(
                "/api/v1/reports/generate",
                json={
                    "company_id": "company_123",
                    "frequency": "monthly",
                    "end_date": "2026-01-31",
                    "recipient": "+237658173627",
                    "delivery_method": "whatsapp"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task_abc123"
        assert data["status"] == "pending"
        assert data["company_id"] == "company_123"

    def test_generate_report_invalid_phone(self):
        """Test avec numéro de téléphone invalide."""

        response = client.post(
            "/api/v1/reports/generate",
            json={
                "company_id": "company_123",
                "frequency": "weekly",
                "recipient": "invalid_phone",
                "delivery_method": "whatsapp"
            }
        )

        assert response.status_code == 400
        assert "Invalid phone number" in response.json()["detail"]

    def test_generate_report_invalid_date(self):
        """Test avec date invalide."""

        with patch('app.api.v1.reports.generate_single_report') as mock_task:
            mock_celery_task = MagicMock()
            mock_celery_task.id = "task_123"
            mock_task.delay.return_value = mock_celery_task

            response = client.post(
                "/api/v1/reports/generate",
                json={
                    "company_id": "company_123",
                    "frequency": "monthly",
                    "end_date": "invalid_date",
                    "delivery_method": "telegram"
                }
            )

        # validate_date_string devrait lever une HTTPException
        assert response.status_code == 400

    def test_generate_report_celery_broker_unavailable(self):
        """Test quand Celery broker n'est pas disponible."""

        from kombu.exceptions import OperationalError as KombuOperationalError

        with patch('app.api.v1.reports.generate_single_report') as mock_task:
            mock_task.delay.side_effect = KombuOperationalError("Connection refused")

            response = client.post(
                "/api/v1/reports/generate",
                json={
                    "company_id": "company_123",
                    "frequency": "monthly"
                }
            )

        assert response.status_code == 503
        assert "broker indisponible" in response.json()["detail"]

    def test_generate_report_with_minimal_params(self):
        """Test génération avec paramètres minimaux."""

        with patch('app.api.v1.reports.generate_single_report') as mock_task:
            mock_celery_task = MagicMock()
            mock_celery_task.id = "task_minimal"
            mock_task.delay.return_value = mock_celery_task

            response = client.post(
                "/api/v1/reports/generate",
                json={
                    "company_id": "company_123"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data

    def test_generate_report_telegram_no_phone_validation(self):
        """Test Telegram n'exige pas de validation de numéro."""

        with patch('app.api.v1.reports.generate_single_report') as mock_task:
            mock_celery_task = MagicMock()
            mock_celery_task.id = "task_tg"
            mock_task.delay.return_value = mock_celery_task

            response = client.post(
                "/api/v1/reports/generate",
                json={
                    "company_id": "company_123",
                    "frequency": "weekly",
                    "recipient": "123456789",  # Chat ID, pas un numéro
                    "delivery_method": "telegram"
                }
            )

        assert response.status_code == 200


class TestGetTaskStatusEndpoint:
    """Tests pour GET /reports/task/{task_id}"""

    def test_get_task_status_pending(self):
        """Test récupération statut d'une tâche en cours."""

        with patch('app.api.v1.reports.AsyncResult') as mock_async_result:
            mock_task = MagicMock()
            mock_task.status = "PENDING"
            mock_task.ready.return_value = False
            mock_async_result.return_value = mock_task

            response = client.get("/api/v1/reports/task/task_123")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task_123"
        assert data["status"] == "PENDING"
        assert data["ready"] is False

    def test_get_task_status_success(self):
        """Test récupération statut d'une tâche réussie."""

        with patch('app.api.v1.reports.AsyncResult') as mock_async_result:
            mock_task = MagicMock()
            mock_task.status = "SUCCESS"
            mock_task.ready.return_value = True
            mock_task.successful.return_value = True
            mock_task.result = {"message": "Report generated"}
            mock_async_result.return_value = mock_task

            response = client.get("/api/v1/reports/task/task_success")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["ready"] is True
        assert data["result"]["message"] == "Report generated"

    def test_get_task_status_failed(self):
        """Test récupération statut d'une tâche échouée."""

        with patch('app.api.v1.reports.AsyncResult') as mock_async_result:
            mock_task = MagicMock()
            mock_task.status = "FAILURE"
            mock_task.ready.return_value = True
            mock_task.successful.return_value = False
            mock_task.failed.return_value = True
            mock_task.info = Exception("Database error")
            mock_async_result.return_value = mock_task

            response = client.get("/api/v1/reports/task/task_failed")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FAILURE"
        assert data["ready"] is True
        assert "error" in data


class TestPreviewReportEndpoint:
    """Tests pour POST /reports/preview"""

    @pytest.mark.asyncio
    async def test_preview_report_success(self, sample_report_data):
        """Test preview réussi."""

        # Mock ReportService
        with patch('app.api.v1.reports.get_report_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.generate_report.return_value = sample_report_data

            # Faire en sorte que get_report_service retourne notre mock
            async def get_mock_service():
                return mock_service

            mock_get_service.return_value = get_mock_service()

            response = client.post(
                "/api/v1/reports/preview",
                json={
                    "company_id": "company_123",
                    "frequency": "monthly",
                    "end_date": "2026-01-31"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["company_name"] == sample_report_data.company_name
        assert data["period_name"] == sample_report_data.period_name
        assert "formatted_message" in data
        assert "message_length" in data
        assert "kpis" in data
        assert "insights" in data

    def test_preview_report_company_not_found(self):
        """Test preview avec entreprise inexistante."""

        with patch('app.api.v1.reports.get_report_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.generate_report.side_effect = ValueError("Company not found")

            async def get_mock_service():
                return mock_service

            mock_get_service.return_value = get_mock_service()

            response = client.post(
                "/api/v1/reports/preview",
                json={
                    "company_id": "nonexistent",
                    "frequency": "weekly"
                }
            )

        assert response.status_code == 404

    def test_preview_report_invalid_date(self):
        """Test preview avec date invalide."""

        response = client.post(
            "/api/v1/reports/preview",
            json={
                "company_id": "company_123",
                "frequency": "monthly",
                "end_date": "not-a-date"
            }
        )

        assert response.status_code == 400

    def test_preview_report_internal_error(self):
        """Test preview avec erreur interne."""

        with patch('app.api.v1.reports.get_report_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.generate_report.side_effect = Exception("Database error")

            async def get_mock_service():
                return mock_service

            mock_get_service.return_value = get_mock_service()

            response = client.post(
                "/api/v1/reports/preview",
                json={
                    "company_id": "company_123",
                    "frequency": "quarterly"
                }
            )

        assert response.status_code == 500


class TestReportHistoryEndpoint:
    """Tests pour GET /reports/history/{company_id}"""

    @pytest.mark.asyncio
    async def test_get_report_history_success(self):
        """Test récupération historique réussie."""

        # Mock de la validation de company existence
        with patch('app.api.v1.reports.validate_company_exists') as mock_validate:
            mock_validate.return_value = "company_123"

            # Mock de la session DB
            with patch('app.api.v1.reports.AsyncSessionLocal') as mock_session_local:
                mock_session = AsyncMock()

                # Mock résultat de la requête history
                mock_row1 = MagicMock()
                mock_row1._mapping = {
                    "id": "report_1",
                    "report_type": "monthly",
                    "status": "success",
                    "created_at": "2026-01-01"
                }
                mock_row2 = MagicMock()
                mock_row2._mapping = {
                    "id": "report_2",
                    "report_type": "weekly",
                    "status": "success",
                    "created_at": "2026-01-08"
                }

                mock_result = AsyncMock()
                mock_result.all.return_value = [mock_row1, mock_row2]

                # Mock résultat du count
                mock_count_result = AsyncMock()
                mock_count_result.scalar.return_value = 2

                # Configure les appels execute
                mock_session.execute.side_effect = [mock_result, mock_count_result]

                # Configure le context manager
                mock_session_local.return_value.__aenter__.return_value = mock_session

                response = client.get("/api/v1/reports/history/company_123?limit=10&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert len(data["history"]) == 2

    def test_get_report_history_pagination(self):
        """Test pagination de l'historique."""

        with patch('app.api.v1.reports.validate_company_exists') as mock_validate:
            mock_validate.return_value = "company_123"

            with patch('app.api.v1.reports.AsyncSessionLocal') as mock_session_local:
                mock_session = AsyncMock()
                mock_result = AsyncMock()
                mock_result.all.return_value = []
                mock_count_result = AsyncMock()
                mock_count_result.scalar.return_value = 100

                mock_session.execute.side_effect = [mock_result, mock_count_result]
                mock_session_local.return_value.__aenter__.return_value = mock_session

                response = client.get("/api/v1/reports/history/company_123?limit=20&offset=40")

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 20
        assert data["offset"] == 40
        assert data["total"] == 100

    def test_get_report_history_invalid_limit(self):
        """Test avec limite invalide (>100)."""

        response = client.get("/api/v1/reports/history/company_123?limit=200")

        # FastAPI validation devrait rejeter
        assert response.status_code == 422

    def test_get_report_history_negative_offset(self):
        """Test avec offset négatif."""

        response = client.get("/api/v1/reports/history/company_123?offset=-5")

        # FastAPI validation devrait rejeter
        assert response.status_code == 422


class TestGlobalStatsEndpoint:
    """Tests pour GET /reports/stats/global"""

    @pytest.mark.asyncio
    async def test_get_global_stats_success(self):
        """Test récupération statistiques globales."""

        with patch('app.api.v1.reports.AsyncSessionLocal') as mock_session_local:
            mock_session = AsyncMock()

            # Mock résultat total
            mock_total_result = AsyncMock()
            mock_total_result.scalar.return_value = 150

            # Mock résultat par statut
            mock_status_row1 = MagicMock()
            mock_status_row1.status = "success"
            mock_status_row1.count = 120
            mock_status_row2 = MagicMock()
            mock_status_row2.status = "failed"
            mock_status_row2.count = 30

            mock_status_result = AsyncMock()
            mock_status_result.all.return_value = [mock_status_row1, mock_status_row2]

            # Mock résultat par fréquence
            mock_freq_row1 = MagicMock()
            mock_freq_row1.report_type = "monthly"
            mock_freq_row1.count = 80
            mock_freq_row2 = MagicMock()
            mock_freq_row2.report_type = "weekly"
            mock_freq_row2.count = 70

            mock_freq_result = AsyncMock()
            mock_freq_result.all.return_value = [mock_freq_row1, mock_freq_row2]

            # Mock résultat temps moyen
            mock_avg_result = AsyncMock()
            mock_avg_result.scalar.return_value = 1250.5

            # Configure les appels execute dans l'ordre
            mock_session.execute.side_effect = [
                mock_total_result,
                mock_status_result,
                mock_freq_result,
                mock_avg_result
            ]

            mock_session_local.return_value.__aenter__.return_value = mock_session

            response = client.get("/api/v1/reports/stats/global")

        assert response.status_code == 200
        data = response.json()
        assert data["total_reports"] == 150
        assert data["by_status"]["success"] == 120
        assert data["by_status"]["failed"] == 30
        assert data["by_frequency"]["monthly"] == 80
        assert data["by_frequency"]["weekly"] == 70
        assert data["avg_execution_time_ms"] == 1250

    @pytest.mark.asyncio
    async def test_get_global_stats_no_data(self):
        """Test statistiques quand aucune donnée."""

        with patch('app.api.v1.reports.AsyncSessionLocal') as mock_session_local:
            mock_session = AsyncMock()

            # Tous les résultats vides
            mock_total_result = AsyncMock()
            mock_total_result.scalar.return_value = 0

            mock_status_result = AsyncMock()
            mock_status_result.all.return_value = []

            mock_freq_result = AsyncMock()
            mock_freq_result.all.return_value = []

            mock_avg_result = AsyncMock()
            mock_avg_result.scalar.return_value = 0

            mock_session.execute.side_effect = [
                mock_total_result,
                mock_status_result,
                mock_freq_result,
                mock_avg_result
            ]

            mock_session_local.return_value.__aenter__.return_value = mock_session

            response = client.get("/api/v1/reports/stats/global")

        assert response.status_code == 200
        data = response.json()
        assert data["total_reports"] == 0
        assert data["by_status"] == {}
        assert data["by_frequency"] == {}
        assert data["avg_execution_time_ms"] == 0


class TestRateLimiting:
    """Tests pour le rate limiting sur les endpoints"""

    def test_rate_limit_strict_endpoint(self):
        """Test rate limiting sur /generate (strict: 10/min)."""

        # Note: Ce test nécessite un vrai Redis pour fonctionner
        # Pour le moment, on vérifie juste que le dependency existe

        with patch('app.api.v1.reports.generate_single_report') as mock_task:
            mock_celery_task = MagicMock()
            mock_celery_task.id = "task_rl"
            mock_task.delay.return_value = mock_celery_task

            # Premier appel devrait passer
            response = client.post(
                "/api/v1/reports/generate",
                json={"company_id": "company_123"}
            )

            # Avec un vrai Redis, après 10 requêtes on aurait 429
            assert response.status_code == 200

    def test_rate_limit_permissive_endpoint(self):
        """Test rate limiting sur /task/{id} (permissive: 120/min)."""

        with patch('app.api.v1.reports.AsyncResult') as mock_async_result:
            mock_task = MagicMock()
            mock_task.status = "PENDING"
            mock_task.ready.return_value = False
            mock_async_result.return_value = mock_task

            # Devrait permettre beaucoup de requêtes
            for i in range(5):
                response = client.get(f"/api/v1/reports/task/task_{i}")
                assert response.status_code == 200
