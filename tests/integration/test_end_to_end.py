# tests/integration/test_end_to_end.py
"""
Tests d'intégration end-to-end.

Teste le parcours complet de génération et envoi d'un rapport.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date
from decimal import Decimal

from app.services.report_service import ReportService
from app.services.notification_service import NotificationService
from app.domain.enums import ReportFrequency, DeliveryMethod, InsightType, InsightPriority
from app.domain.models import ReportData, KPIData, KPIComparison, InsightModel


class TestEndToEndReportGeneration:
    """Tests end-to-end pour la génération complète de rapports"""

    @pytest.mark.asyncio
    async def test_full_report_generation_and_delivery_whatsapp(
        self,
        db_session,
        sample_company,
        sample_kpis
    ):
        """
        Test complet: Générer un rapport et l'envoyer via WhatsApp.

        Parcours:
        1. ReportService.generate_report() - Génère le rapport
        2. NotificationService.send_report() - Envoie via WhatsApp
        3. Vérifier que tout le pipeline fonctionne
        """

        # ========== 1. SETUP ==========

        # Mock company repository
        with patch('app.services.report_service.GeminiClient'):
            report_service = ReportService(db_session)

        # Mock notification service avec WhatsApp
        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = True
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            with patch('app.services.notification_service.WhatsAppClient') as mock_wa:
                mock_whatsapp_client = AsyncMock()
                mock_whatsapp_client.send_message.return_value = True
                mock_wa.return_value = mock_whatsapp_client

                notification_service = NotificationService()

        # ========== 2. GÉNÉRATION DU RAPPORT ==========

        with patch.object(report_service.company_repo, 'get_by_id', return_value=sample_company):
            with patch.object(report_service.kpi_calculator, 'calculate', return_value=sample_kpis):
                mock_comparison = KPIComparison(
                    revenue_change_percent=15.2,
                    sales_change_percent=8.5,
                    customer_change_percent=22.1
                )
                with patch.object(report_service.kpi_comparator, 'compare', return_value=mock_comparison):
                    # Mock insights
                    mock_insights = [
                        InsightModel(
                            type=InsightType.TREND,
                            message="📈 Revenus en hausse de +15%",
                            priority=InsightPriority.HIGH,
                            score=0.9
                        ),
                        InsightModel(
                            type=InsightType.ALERT,
                            message="⚠️ Stock bas",
                            priority=InsightPriority.MEDIUM,
                            score=0.7
                        )
                    ]
                    with patch.object(report_service, '_extract_insights', return_value=mock_insights):
                        # Mock recommendations
                        with patch.object(
                            report_service.recommendations_generator,
                            'generate',
                            return_value="Augmentez vos ventes de 20%"
                        ):
                            # Générer le rapport
                            report_data = await report_service.generate_report(
                                company_id="company_test_123",
                                frequency=ReportFrequency.MONTHLY,
                                end_date=date(2026, 1, 31)
                            )

        # Vérifications du rapport généré
        assert report_data is not None
        assert isinstance(report_data, ReportData)
        assert report_data.company_name == "Boulangerie Test"
        assert report_data.period_name == "Mois"
        assert report_data.kpis.revenue == Decimal("50000")
        assert len(report_data.insights) == 2
        assert report_data.recommendations == "Augmentez vos ventes de 20%"

        # ========== 3. ENVOI DU RAPPORT ==========

        success = await notification_service.send_report(
            report_data=report_data,
            recipient="+237658173627",
            method=DeliveryMethod.WHATSAPP
        )

        # Vérifications de l'envoi
        assert success is True
        mock_whatsapp_client.send_message.assert_called_once()

        # Vérifier que le message contient les informations clés
        call_args = mock_whatsapp_client.send_message.call_args
        sent_phone = call_args.kwargs['phone_number']
        sent_message = call_args.kwargs['message']

        assert sent_phone == "+237658173627"
        assert "Boulangerie Test" in sent_message
        assert "Mois" in sent_message
        assert "50" in sent_message  # Revenue (peut être formaté)

    @pytest.mark.asyncio
    async def test_full_report_generation_and_delivery_telegram(
        self,
        db_session,
        sample_company,
        sample_kpis
    ):
        """
        Test complet: Générer un rapport et l'envoyer via Telegram.
        """

        # ========== 1. SETUP ==========

        with patch('app.services.report_service.GeminiClient'):
            report_service = ReportService(db_session)

        # Mock notification service avec Telegram
        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = False
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = True
            mock_settings.TELEGRAM_BOT_TOKEN = "test_bot_token"

            with patch('app.services.notification_service.TelegramClient') as mock_tg:
                mock_telegram_client = AsyncMock()
                mock_telegram_client.send_message.return_value = True
                mock_tg.return_value = mock_telegram_client

                notification_service = NotificationService()

        # ========== 2. GÉNÉRATION DU RAPPORT ==========

        with patch.object(report_service.company_repo, 'get_by_id', return_value=sample_company):
            with patch.object(report_service.kpi_calculator, 'calculate', return_value=sample_kpis):
                mock_comparison = KPIComparison(
                    revenue_change_percent=10.0,
                    sales_change_percent=5.0,
                    customer_change_percent=15.0
                )
                with patch.object(report_service.kpi_comparator, 'compare', return_value=mock_comparison):
                    with patch.object(report_service, '_extract_insights', return_value=[]):
                        with patch.object(
                            report_service.recommendations_generator,
                            'generate',
                            return_value="Continuez sur cette lancée!"
                        ):
                            report_data = await report_service.generate_report(
                                company_id="company_test_123",
                                frequency=ReportFrequency.WEEKLY
                            )

        # ========== 3. ENVOI VIA TELEGRAM ==========

        with patch('app.services.notification_service.clean_telegram_chat_id', return_value="123456789"):
            success = await notification_service.send_report(
                report_data=report_data,
                recipient="123456789",
                method=DeliveryMethod.TELEGRAM
            )

        # Vérifications
        assert success is True
        mock_telegram_client.send_message.assert_called_once()

        call_args = mock_telegram_client.send_message.call_args
        assert call_args.kwargs['chat_id'] == "123456789"

    @pytest.mark.asyncio
    async def test_full_report_generation_with_error_recovery(
        self,
        db_session,
        sample_company,
        sample_kpis
    ):
        """
        Test le comportement quand un miner échoue mais le rapport continue.

        Vérifie la résilience: un miner qui crash ne bloque pas tout.
        """

        with patch('app.services.report_service.GeminiClient'):
            report_service = ReportService(db_session)

        # ========== GÉNÉRATION AVEC UN MINER QUI CRASH ==========

        with patch.object(report_service.company_repo, 'get_by_id', return_value=sample_company):
            with patch.object(report_service.kpi_calculator, 'calculate', return_value=sample_kpis):
                mock_comparison = KPIComparison(
                    revenue_change_percent=0,
                    sales_change_percent=0,
                    customer_change_percent=0
                )
                with patch.object(report_service.kpi_comparator, 'compare', return_value=mock_comparison):
                    # Premier miner crash
                    report_service.insight_miners[0].mine = AsyncMock(
                        side_effect=Exception("Miner crashed")
                    )

                    # Deuxième miner retourne un insight
                    mock_insight = InsightModel(
                        type=InsightType.OPPORTUNITY,
                        message="Opportunité détectée",
                        priority=InsightPriority.LOW,
                        score=0.5
                    )
                    report_service.insight_miners[1].mine = AsyncMock(return_value=mock_insight)

                    # Autres miners retournent None
                    for miner in report_service.insight_miners[2:]:
                        miner.mine = AsyncMock(return_value=None)

                    with patch.object(
                        report_service.recommendations_generator,
                        'generate',
                        return_value="Recommendations"
                    ):
                        report_data = await report_service.generate_report(
                            company_id="company_test_123",
                            frequency=ReportFrequency.MONTHLY
                        )

        # Le rapport doit être généré malgré l'erreur du miner
        assert report_data is not None
        # On doit avoir seulement l'insight du 2ème miner
        assert len(report_data.insights) == 1
        assert report_data.insights[0].message == "Opportunité détectée"

    @pytest.mark.asyncio
    async def test_full_report_notification_failure_handling(
        self,
        db_session,
        sample_company,
        sample_kpis
    ):
        """
        Test le comportement quand l'envoi de notification échoue.

        Le rapport est généré mais l'envoi échoue (ex: API WhatsApp down).
        """

        # ========== 1. GÉNÉRATION RÉUSSIE ==========

        with patch('app.services.report_service.GeminiClient'):
            report_service = ReportService(db_session)

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
                            return_value="Test"
                        ):
                            report_data = await report_service.generate_report(
                                company_id="company_test_123",
                                frequency=ReportFrequency.WEEKLY
                            )

        assert report_data is not None

        # ========== 2. ENVOI ÉCHOUE ==========

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = True
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            with patch('app.services.notification_service.WhatsAppClient') as mock_wa:
                # WhatsApp client retourne False (échec)
                mock_whatsapp_client = AsyncMock()
                mock_whatsapp_client.send_message.return_value = False
                mock_wa.return_value = mock_whatsapp_client

                notification_service = NotificationService()

                success = await notification_service.send_report(
                    report_data=report_data,
                    recipient="+237658173627",
                    method=DeliveryMethod.WHATSAPP
                )

        # L'envoi doit retourner False au lieu de crasher
        assert success is False

    @pytest.mark.asyncio
    async def test_full_report_with_message_truncation(
        self,
        db_session,
        sample_company
    ):
        """
        Test le comportement quand le message formaté dépasse 4096 caractères.

        Vérifie que le message est tronqué correctement.
        """

        # ========== GÉNÉRATION AVEC BEAUCOUP DE DONNÉES ==========

        with patch('app.services.report_service.GeminiClient'):
            report_service = ReportService(db_session)

        # Créer des KPIs avec beaucoup de produits (pour message long)
        large_kpis = KPIData(
            revenue=Decimal("1000000"),
            sales_count=5000,
            average_order_value=Decimal("200"),
            new_customers=500,
            returning_customers=300,
            churn_rate=5.0,
            top_products=[
                {"name": f"Product {i}", "quantity": 100, "revenue": Decimal("1000")}
                for i in range(50)  # Beaucoup de produits
            ],
            low_stock_alerts=[]
        )

        # Générer beaucoup d'insights
        many_insights = [
            InsightModel(
                type=InsightType.TREND,
                message=f"Insight {i} - " + "x" * 100,  # Messages longs
                priority=InsightPriority.MEDIUM,
                score=0.5
            )
            for i in range(20)
        ]

        # Recommandations très longues
        long_recommendations = "x" * 3000

        with patch.object(report_service.company_repo, 'get_by_id', return_value=sample_company):
            with patch.object(report_service.kpi_calculator, 'calculate', return_value=large_kpis):
                mock_comparison = KPIComparison(
                    revenue_change_percent=0,
                    sales_change_percent=0,
                    customer_change_percent=0
                )
                with patch.object(report_service.kpi_comparator, 'compare', return_value=mock_comparison):
                    with patch.object(report_service, '_extract_insights', return_value=many_insights):
                        with patch.object(
                            report_service.recommendations_generator,
                            'generate',
                            return_value=long_recommendations
                        ):
                            report_data = await report_service.generate_report(
                                company_id="company_test_123",
                                frequency=ReportFrequency.MONTHLY
                            )

        # ========== ENVOI AVEC TRONCATURE ==========

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = True
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            with patch('app.services.notification_service.WhatsAppClient') as mock_wa:
                mock_whatsapp_client = AsyncMock()
                mock_whatsapp_client.send_message.return_value = True
                mock_wa.return_value = mock_whatsapp_client

                notification_service = NotificationService()

                success = await notification_service.send_report(
                    report_data=report_data,
                    recipient="+237658173627",
                    method=DeliveryMethod.WHATSAPP
                )

        # Vérifier que le message a été tronqué
        call_args = mock_whatsapp_client.send_message.call_args
        sent_message = call_args.kwargs['message']

        assert len(sent_message) <= 4096
        # Si tronqué, devrait se terminer par "[Tronqué]"
        if len(sent_message) >= 4090:
            assert sent_message.endswith("[Tronqué]")

    @pytest.mark.asyncio
    async def test_multiple_delivery_methods_available(self, db_session):
        """
        Test que plusieurs méthodes de livraison peuvent être configurées.
        """

        # Initialiser avec WhatsApp ET Telegram
        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = True
            mock_settings.WHATSAPP_API_TOKEN = "wa_token"
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = True
            mock_settings.TELEGRAM_BOT_TOKEN = "tg_token"

            with patch('app.services.notification_service.WhatsAppClient'):
                with patch('app.services.notification_service.TelegramClient'):
                    notification_service = NotificationService()

                    available = notification_service.get_available_methods()

        # Les deux méthodes doivent être disponibles
        assert len(available) == 2
        assert DeliveryMethod.WHATSAPP in available
        assert DeliveryMethod.TELEGRAM in available

    @pytest.mark.asyncio
    async def test_report_generation_for_different_frequencies(
        self,
        db_session,
        sample_company,
        sample_kpis
    ):
        """
        Test génération de rapports pour toutes les fréquences.

        Vérifie WEEKLY, MONTHLY, QUARTERLY.
        """

        with patch('app.services.report_service.GeminiClient'):
            report_service = ReportService(db_session)

        frequencies = [
            (ReportFrequency.WEEKLY, "Semaine"),
            (ReportFrequency.MONTHLY, "Mois"),
            (ReportFrequency.QUARTERLY, "Trimestre")
        ]

        for frequency, expected_period_name in frequencies:
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
                                return_value="Test"
                            ):
                                report_data = await report_service.generate_report(
                                    company_id="company_test_123",
                                    frequency=frequency,
                                    end_date=date(2026, 1, 31)
                                )

                                assert report_data.period_name == expected_period_name
