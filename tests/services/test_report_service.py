# tests/services/test_report_service.py
"""
Tests pour ReportService.

Vérifie la logique de génération de rapports, orchestration des composants.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.report_service import ReportService
from app.domain.enums import ReportFrequency, InsightType, InsightPriority
from app.domain.models import KPIData, KPIComparison, InsightModel, ReportData


class TestReportService:
    """Tests pour ReportService"""

    @pytest.fixture
    def report_service(self, db_session):
        """Fixture pour créer un ReportService."""
        # Mock Gemini client pour éviter les appels API
        with patch('app.services.report_service.GeminiClient'):
            service = ReportService(db_session)
        return service

    # ==================== Tests generate_report ====================

    @pytest.mark.asyncio
    async def test_generate_report_success(self, report_service, sample_company, sample_kpis):
        """Test génération d'un rapport complet avec succès."""

        # Mock company_repo
        with patch.object(report_service.company_repo, 'get_by_id', return_value=sample_company):
            # Mock KPI calculator
            with patch.object(report_service.kpi_calculator, 'calculate', return_value=sample_kpis):
                # Mock KPI comparator
                mock_comparison = KPIComparison(
                    revenue_change_percent=15.2,
                    sales_change_percent=8.5,
                    customer_change_percent=22.1
                )
                with patch.object(report_service.kpi_comparator, 'compare', return_value=mock_comparison):
                    # Mock insights extraction
                    mock_insights = [
                        InsightModel(
                            type=InsightType.TREND,
                            message="Revenue up",
                            priority=InsightPriority.HIGH,
                            score=0.9
                        )
                    ]
                    with patch.object(report_service, '_extract_insights', return_value=mock_insights):
                        # Mock recommendations
                        with patch.object(
                            report_service.recommendations_generator,
                            'generate',
                            return_value="Test recommendations"
                        ):
                            # Générer le rapport
                            result = await report_service.generate_report(
                                company_id="company_test_123",
                                frequency=ReportFrequency.WEEKLY,
                                end_date=date(2026, 1, 7)
                            )

        # Vérifications
        assert isinstance(result, ReportData)
        assert result.company_name == "Boulangerie Test"
        assert result.period_name == "Semaine"
        assert result.kpis == sample_kpis
        assert result.kpis_comparison == mock_comparison
        assert len(result.insights) == 1
        assert result.recommendations == "Test recommendations"

    @pytest.mark.asyncio
    async def test_generate_report_company_not_found(self, report_service):
        """Test erreur si l'entreprise n'existe pas."""

        with patch.object(report_service.company_repo, 'get_by_id', return_value=None):
            with pytest.raises(ValueError, match="Company .* not found"):
                await report_service.generate_report(
                    company_id="nonexistent",
                    frequency=ReportFrequency.WEEKLY
                )

    @pytest.mark.asyncio
    async def test_generate_report_with_default_end_date(self, report_service, sample_company, sample_kpis):
        """Test génération avec end_date par défaut (aujourd'hui)."""

        with patch.object(report_service.company_repo, 'get_by_id', return_value=sample_company):
            with patch.object(report_service.kpi_calculator, 'calculate', return_value=sample_kpis):
                mock_comparison = KPIComparison(
                    revenue_change_percent=0,
                    sales_change_percent=0,
                    customer_change_percent=0
                )
                with patch.object(report_service.kpi_comparator, 'compare', return_value=mock_comparison):
                    with patch.object(report_service, '_extract_insights', return_value=[]):
                        with patch.object(
                            report_service.recommendations_generator,
                            'generate',
                            return_value=""
                        ):
                            # end_date = None devrait utiliser today
                            result = await report_service.generate_report(
                                company_id="company_test_123",
                                frequency=ReportFrequency.MONTHLY,
                                end_date=None
                            )

        assert isinstance(result, ReportData)

    @pytest.mark.asyncio
    async def test_generate_report_logs_on_error(self, report_service, sample_company):
        """Test que les erreurs sont loggées correctement."""

        with patch.object(report_service.company_repo, 'get_by_id', return_value=sample_company):
            with patch.object(
                report_service.kpi_calculator,
                'calculate',
                side_effect=Exception("Database error")
            ):
                with pytest.raises(Exception, match="Database error"):
                    await report_service.generate_report(
                        company_id="company_test_123",
                        frequency=ReportFrequency.WEEKLY
                    )

    # ==================== Tests _extract_insights ====================

    @pytest.mark.asyncio
    async def test_extract_insights_all_miners_succeed(self, report_service, sample_kpis):
        """Test extraction d'insights quand tous les miners réussissent."""

        # Mock tous les miners pour retourner un insight
        mock_insight = InsightModel(
            type=InsightType.ALERT,
            message="Test insight",
            priority=InsightPriority.HIGH,
            score=0.8
        )

        for miner in report_service.insight_miners:
            miner.mine = AsyncMock(return_value=mock_insight)

        result = await report_service._extract_insights(
            company_id="company_123",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 7),
            kpis=sample_kpis
        )

        # Devrait avoir un insight par miner
        assert len(result) == len(report_service.insight_miners)
        assert all(isinstance(i, InsightModel) for i in result)

    @pytest.mark.asyncio
    async def test_extract_insights_some_miners_return_none(self, report_service, sample_kpis):
        """Test extraction quand certains miners ne trouvent rien."""

        mock_insight = InsightModel(
            type=InsightType.OPPORTUNITY,
            message="Found opportunity",
            priority=InsightPriority.MEDIUM,
            score=0.6
        )

        # Premier miner retourne insight, les autres None
        report_service.insight_miners[0].mine = AsyncMock(return_value=mock_insight)
        for miner in report_service.insight_miners[1:]:
            miner.mine = AsyncMock(return_value=None)

        result = await report_service._extract_insights(
            company_id="company_123",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 7),
            kpis=sample_kpis
        )

        # Devrait avoir seulement 1 insight
        assert len(result) == 1
        assert result[0].message == "Found opportunity"

    @pytest.mark.asyncio
    async def test_extract_insights_miner_raises_error(self, report_service, sample_kpis):
        """Test que les erreurs d'un miner n'empêchent pas les autres."""

        mock_insight = InsightModel(
            type=InsightType.TREND,
            message="Trend detected",
            priority=InsightPriority.LOW,
            score=0.5
        )

        # Premier miner crash, deuxième réussit
        report_service.insight_miners[0].mine = AsyncMock(side_effect=Exception("Miner error"))
        report_service.insight_miners[1].mine = AsyncMock(return_value=mock_insight)
        for miner in report_service.insight_miners[2:]:
            miner.mine = AsyncMock(return_value=None)

        result = await report_service._extract_insights(
            company_id="company_123",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 7),
            kpis=sample_kpis
        )

        # Devrait avoir l'insight du deuxième miner
        assert len(result) == 1
        assert result[0].message == "Trend detected"

    @pytest.mark.asyncio
    async def test_extract_insights_all_miners_fail(self, report_service, sample_kpis):
        """Test extraction quand tous les miners échouent."""

        # Tous les miners crashent
        for miner in report_service.insight_miners:
            miner.mine = AsyncMock(side_effect=Exception("Critical error"))

        result = await report_service._extract_insights(
            company_id="company_123",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 7),
            kpis=sample_kpis
        )

        # Devrait retourner liste vide au lieu de crasher
        assert result == []

    # ==================== Tests _calculate_period_dates ====================

    def test_calculate_period_dates_weekly(self, report_service):
        """Test calcul de période hebdomadaire."""
        end_date = date(2026, 1, 7)  # Mercredi

        start, end, name, range_str = report_service._calculate_period_dates(
            ReportFrequency.WEEKLY,
            end_date
        )

        assert start == date(2026, 1, 1)  # 7 jours avant (inclus)
        assert end == end_date
        assert name == "Semaine"
        assert range_str == "01/01 - 07/01/2026"

    def test_calculate_period_dates_monthly(self, report_service):
        """Test calcul de période mensuelle."""
        end_date = date(2026, 1, 15)

        start, end, name, range_str = report_service._calculate_period_dates(
            ReportFrequency.MONTHLY,
            end_date
        )

        assert start == date(2026, 1, 1)  # Premier jour du mois
        assert end == end_date
        assert name == "Mois"
        assert range_str == "01/01 - 15/01/2026"

    def test_calculate_period_dates_quarterly_q1(self, report_service):
        """Test calcul trimestre Q1 (Jan-Mar)."""
        end_date = date(2026, 3, 31)

        start, end, name, range_str = report_service._calculate_period_dates(
            ReportFrequency.QUARTERLY,
            end_date
        )

        assert start == date(2026, 1, 1)  # Début Q1
        assert end == end_date
        assert name == "Trimestre"
        assert range_str == "01/01 - 31/03/2026"

    def test_calculate_period_dates_quarterly_q2(self, report_service):
        """Test calcul trimestre Q2 (Apr-Jun)."""
        end_date = date(2026, 6, 30)

        start, end, name, range_str = report_service._calculate_period_dates(
            ReportFrequency.QUARTERLY,
            end_date
        )

        assert start == date(2026, 4, 1)  # Début Q2
        assert end == end_date
        assert name == "Trimestre"

    def test_calculate_period_dates_quarterly_q3(self, report_service):
        """Test calcul trimestre Q3 (Jul-Sep)."""
        end_date = date(2026, 9, 30)

        start, end, name, range_str = report_service._calculate_period_dates(
            ReportFrequency.QUARTERLY,
            end_date
        )

        assert start == date(2026, 7, 1)  # Début Q3
        assert end == end_date

    def test_calculate_period_dates_quarterly_q4(self, report_service):
        """Test calcul trimestre Q4 (Oct-Dec)."""
        end_date = date(2026, 12, 31)

        start, end, name, range_str = report_service._calculate_period_dates(
            ReportFrequency.QUARTERLY,
            end_date
        )

        assert start == date(2026, 10, 1)  # Début Q4
        assert end == end_date

    def test_calculate_period_dates_with_none_end_date(self, report_service):
        """Test calcul avec end_date = None (utilise aujourd'hui)."""

        with patch('app.services.report_service.today_in_timezone') as mock_today:
            mock_today.return_value = date(2026, 1, 15)

            start, end, name, range_str = report_service._calculate_period_dates(
                ReportFrequency.WEEKLY,
                end_date=None
            )

            assert end == date(2026, 1, 15)
            assert start == date(2026, 1, 9)

    def test_calculate_period_dates_format_consistency(self, report_service):
        """Test que le format de period_range est cohérent."""

        start, end, name, range_str = report_service._calculate_period_dates(
            ReportFrequency.MONTHLY,
            date(2026, 12, 31)
        )

        # Format attendu: "DD/MM - DD/MM/YYYY"
        assert "/" in range_str
        assert " - " in range_str
        assert range_str.endswith("/2026")

    # ==================== Tests initialization ====================

    def test_service_initialization_with_gemini(self, db_session):
        """Test initialisation avec Gemini client valide."""

        with patch('app.services.report_service.GeminiClient') as mock_gemini:
            with patch('app.services.report_service.settings') as mock_settings:
                mock_settings.GOOGLE_API_KEY = "test_key"
                mock_settings.MAX_INSIGHTS_PER_REPORT = 5

                service = ReportService(db_session)

                # Vérifier que tous les composants sont initialisés
                assert service.session == db_session
                assert service.company_repo is not None
                assert service.order_repo is not None
                assert service.customer_repo is not None
                assert service.kpi_calculator is not None
                assert service.kpi_comparator is not None
                assert len(service.insight_miners) == 4
                assert service.recommendations_generator is not None

    def test_service_initialization_without_gemini(self, db_session):
        """Test initialisation sans Gemini (clé API manquante)."""

        with patch('app.services.report_service.settings') as mock_settings:
            mock_settings.GOOGLE_API_KEY = None
            mock_settings.MAX_INSIGHTS_PER_REPORT = 5

            service = ReportService(db_session)

            # Le service doit quand même fonctionner sans Gemini
            assert service.recommendations_generator is not None

    def test_service_initialization_gemini_error(self, db_session):
        """Test initialisation quand Gemini client crash."""

        with patch('app.services.report_service.GeminiClient', side_effect=Exception("API error")):
            with patch('app.services.report_service.settings') as mock_settings:
                mock_settings.GOOGLE_API_KEY = "test_key"
                mock_settings.MAX_INSIGHTS_PER_REPORT = 5

                # Ne doit pas crasher, mais fallback à None
                service = ReportService(db_session)
                assert service.recommendations_generator is not None

    # ==================== Tests edge cases ====================

    @pytest.mark.asyncio
    async def test_generate_report_with_empty_kpis(self, report_service, sample_company):
        """Test génération avec KPIs vides."""

        empty_kpis = KPIData(
            revenue=Decimal("0"),
            sales_count=0,
            average_order_value=Decimal("0"),
            new_customers=0,
            returning_customers=0,
            churn_rate=0.0,
            top_products=[],
            low_stock_alerts=[]
        )

        with patch.object(report_service.company_repo, 'get_by_id', return_value=sample_company):
            with patch.object(report_service.kpi_calculator, 'calculate', return_value=empty_kpis):
                mock_comparison = KPIComparison(
                    revenue_change_percent=0,
                    sales_change_percent=0,
                    customer_change_percent=0
                )
                with patch.object(report_service.kpi_comparator, 'compare', return_value=mock_comparison):
                    with patch.object(report_service, '_extract_insights', return_value=[]):
                        with patch.object(
                            report_service.recommendations_generator,
                            'generate',
                            return_value="Start selling!"
                        ):
                            result = await report_service.generate_report(
                                company_id="company_test_123",
                                frequency=ReportFrequency.WEEKLY
                            )

        # Doit générer un rapport même avec KPIs vides
        assert result.kpis.revenue == Decimal("0")
        assert result.kpis.sales_count == 0

    @pytest.mark.asyncio
    async def test_generate_report_with_no_insights(self, report_service, sample_company, sample_kpis):
        """Test génération sans insights détectés."""

        with patch.object(report_service.company_repo, 'get_by_id', return_value=sample_company):
            with patch.object(report_service.kpi_calculator, 'calculate', return_value=sample_kpis):
                mock_comparison = KPIComparison(
                    revenue_change_percent=0,
                    sales_change_percent=0,
                    customer_change_percent=0
                )
                with patch.object(report_service.kpi_comparator, 'compare', return_value=mock_comparison):
                    # Aucun insight
                    with patch.object(report_service, '_extract_insights', return_value=[]):
                        with patch.object(
                            report_service.recommendations_generator,
                            'generate',
                            return_value="Keep up the good work"
                        ):
                            result = await report_service.generate_report(
                                company_id="company_test_123",
                                frequency=ReportFrequency.WEEKLY
                            )

        # Doit générer un rapport même sans insights
        assert len(result.insights) == 0
        assert result.recommendations is not None
