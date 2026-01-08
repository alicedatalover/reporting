# tests/services/test_notification_service.py
"""
Tests pour NotificationService.

Vérifie l'envoi de rapports via WhatsApp et Telegram.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.notification_service import NotificationService
from app.domain.enums import DeliveryMethod


class TestNotificationService:
    """Tests pour NotificationService"""

    # ==================== Tests initialization ====================

    def test_initialization_with_whatsapp_enabled(self):
        """Test initialisation avec WhatsApp activé."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = True
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            with patch('app.services.notification_service.WhatsAppClient') as mock_wa:
                service = NotificationService()

                assert service.whatsapp_client is not None
                assert service.telegram_client is None
                mock_wa.assert_called_once()

    def test_initialization_with_telegram_enabled(self):
        """Test initialisation avec Telegram activé."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = False
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = True
            mock_settings.TELEGRAM_BOT_TOKEN = "test_bot_token"

            with patch('app.services.notification_service.TelegramClient') as mock_tg:
                service = NotificationService()

                assert service.whatsapp_client is None
                assert service.telegram_client is not None
                mock_tg.assert_called_once()

    def test_initialization_with_both_enabled(self):
        """Test initialisation avec WhatsApp ET Telegram."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = True
            mock_settings.WHATSAPP_API_TOKEN = "test_wa_token"
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = True
            mock_settings.TELEGRAM_BOT_TOKEN = "test_tg_token"

            with patch('app.services.notification_service.WhatsAppClient'):
                with patch('app.services.notification_service.TelegramClient'):
                    service = NotificationService()

                    assert service.whatsapp_client is not None
                    assert service.telegram_client is not None

    def test_initialization_with_none_enabled(self):
        """Test initialisation sans aucun canal activé."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = False
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            service = NotificationService()

            assert service.whatsapp_client is None
            assert service.telegram_client is None

    def test_initialization_whatsapp_client_error(self):
        """Test initialisation quand WhatsApp client crash."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = True
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            with patch(
                'app.services.notification_service.WhatsAppClient',
                side_effect=Exception("API connection failed")
            ):
                service = NotificationService()

                # Ne doit pas crasher, client reste None
                assert service.whatsapp_client is None

    def test_initialization_telegram_client_error(self):
        """Test initialisation quand Telegram client crash."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = False
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = True
            mock_settings.TELEGRAM_BOT_TOKEN = "test_token"

            with patch(
                'app.services.notification_service.TelegramClient',
                side_effect=Exception("Bot token invalid")
            ):
                service = NotificationService()

                # Ne doit pas crasher, client reste None
                assert service.telegram_client is None

    # ==================== Tests send_report ====================

    @pytest.mark.asyncio
    async def test_send_report_via_whatsapp_success(self, sample_report_data):
        """Test envoi réussi via WhatsApp."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = True
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            with patch('app.services.notification_service.WhatsAppClient') as mock_wa:
                mock_client = AsyncMock()
                mock_client.send_message.return_value = True
                mock_wa.return_value = mock_client

                service = NotificationService()

                # Mock formatter
                with patch.object(service.formatter, 'format_report', return_value="Test message"):
                    result = await service.send_report(
                        report_data=sample_report_data,
                        recipient="+237658173627",
                        method=DeliveryMethod.WHATSAPP
                    )

        assert result is True
        mock_client.send_message.assert_called_once_with(
            phone_number="+237658173627",
            message="Test message"
        )

    @pytest.mark.asyncio
    async def test_send_report_via_telegram_success(self, sample_report_data):
        """Test envoi réussi via Telegram."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = False
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = True
            mock_settings.TELEGRAM_BOT_TOKEN = "test_token"

            with patch('app.services.notification_service.TelegramClient') as mock_tg:
                mock_client = AsyncMock()
                mock_client.send_message.return_value = True
                mock_tg.return_value = mock_client

                service = NotificationService()

                # Mock formatter et validator
                with patch.object(service.formatter, 'format_report', return_value="Test message"):
                    with patch(
                        'app.services.notification_service.clean_telegram_chat_id',
                        return_value="123456789"
                    ):
                        result = await service.send_report(
                            report_data=sample_report_data,
                            recipient="123456789",
                            method=DeliveryMethod.TELEGRAM
                        )

        assert result is True
        mock_client.send_message.assert_called_once_with(
            chat_id="123456789",
            message="Test message"
        )

    @pytest.mark.asyncio
    async def test_send_report_whatsapp_client_not_initialized(self, sample_report_data):
        """Test envoi WhatsApp quand client non initialisé."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = False
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            service = NotificationService()

            # Mock formatter
            with patch.object(service.formatter, 'format_report', return_value="Test message"):
                result = await service.send_report(
                    report_data=sample_report_data,
                    recipient="+237658173627",
                    method=DeliveryMethod.WHATSAPP
                )

        # Doit retourner False au lieu de crasher
        assert result is False

    @pytest.mark.asyncio
    async def test_send_report_telegram_client_not_initialized(self, sample_report_data):
        """Test envoi Telegram quand client non initialisé."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = False
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            service = NotificationService()

            # Mock formatter
            with patch.object(service.formatter, 'format_report', return_value="Test message"):
                result = await service.send_report(
                    report_data=sample_report_data,
                    recipient="123456789",
                    method=DeliveryMethod.TELEGRAM
                )

        # Doit retourner False
        assert result is False

    @pytest.mark.asyncio
    async def test_send_report_message_truncation(self, sample_report_data):
        """Test troncature des messages trop longs (>4096 caractères)."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = True
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            with patch('app.services.notification_service.WhatsAppClient') as mock_wa:
                mock_client = AsyncMock()
                mock_client.send_message.return_value = True
                mock_wa.return_value = mock_client

                service = NotificationService()

                # Générer un message trop long
                long_message = "x" * 5000

                with patch.object(service.formatter, 'format_report', return_value=long_message):
                    result = await service.send_report(
                        report_data=sample_report_data,
                        recipient="+237658173627",
                        method=DeliveryMethod.WHATSAPP
                    )

        # Vérifier que le message a été tronqué
        call_args = mock_client.send_message.call_args
        sent_message = call_args.kwargs['message']
        assert len(sent_message) <= 4096
        assert sent_message.endswith("[Tronqué]")

    @pytest.mark.asyncio
    async def test_send_report_formatting_error(self, sample_report_data):
        """Test gestion d'erreur lors du formatage."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = True
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            with patch('app.services.notification_service.WhatsAppClient'):
                service = NotificationService()

                # Formatter crash
                with patch.object(
                    service.formatter,
                    'format_report',
                    side_effect=Exception("Format error")
                ):
                    result = await service.send_report(
                        report_data=sample_report_data,
                        recipient="+237658173627",
                        method=DeliveryMethod.WHATSAPP
                    )

        # Doit retourner False au lieu de crasher
        assert result is False

    @pytest.mark.asyncio
    async def test_send_report_client_send_failure(self, sample_report_data):
        """Test quand le client échoue à envoyer."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = True
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            with patch('app.services.notification_service.WhatsAppClient') as mock_wa:
                mock_client = AsyncMock()
                mock_client.send_message.return_value = False  # Échec
                mock_wa.return_value = mock_client

                service = NotificationService()

                with patch.object(service.formatter, 'format_report', return_value="Test message"):
                    result = await service.send_report(
                        report_data=sample_report_data,
                        recipient="+237658173627",
                        method=DeliveryMethod.WHATSAPP
                    )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_report_client_raises_exception(self, sample_report_data):
        """Test quand le client lève une exception."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = True
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            with patch('app.services.notification_service.WhatsAppClient') as mock_wa:
                mock_client = AsyncMock()
                mock_client.send_message.side_effect = Exception("Network error")
                mock_wa.return_value = mock_client

                service = NotificationService()

                with patch.object(service.formatter, 'format_report', return_value="Test message"):
                    result = await service.send_report(
                        report_data=sample_report_data,
                        recipient="+237658173627",
                        method=DeliveryMethod.WHATSAPP
                    )

        # Doit catcher l'exception et retourner False
        assert result is False

    # ==================== Tests _send_via_whatsapp ====================

    @pytest.mark.asyncio
    async def test_send_via_whatsapp_success(self):
        """Test envoi direct via WhatsApp."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = True
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            with patch('app.services.notification_service.WhatsAppClient') as mock_wa:
                mock_client = AsyncMock()
                mock_client.send_message.return_value = True
                mock_wa.return_value = mock_client

                service = NotificationService()
                result = await service._send_via_whatsapp("+237658173627", "Test message")

        assert result is True

    @pytest.mark.asyncio
    async def test_send_via_whatsapp_no_client(self):
        """Test envoi WhatsApp sans client."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = False
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            service = NotificationService()
            result = await service._send_via_whatsapp("+237658173627", "Test message")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_via_whatsapp_exception(self):
        """Test gestion d'exception dans envoi WhatsApp."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = True
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            with patch('app.services.notification_service.WhatsAppClient') as mock_wa:
                mock_client = AsyncMock()
                mock_client.send_message.side_effect = Exception("API error")
                mock_wa.return_value = mock_client

                service = NotificationService()
                result = await service._send_via_whatsapp("+237658173627", "Test message")

        assert result is False

    # ==================== Tests _send_via_telegram ====================

    @pytest.mark.asyncio
    async def test_send_via_telegram_success(self):
        """Test envoi direct via Telegram."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = False
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = True
            mock_settings.TELEGRAM_BOT_TOKEN = "test_token"

            with patch('app.services.notification_service.TelegramClient') as mock_tg:
                mock_client = AsyncMock()
                mock_client.send_message.return_value = True
                mock_tg.return_value = mock_client

                service = NotificationService()

                with patch(
                    'app.services.notification_service.clean_telegram_chat_id',
                    return_value="123456789"
                ):
                    result = await service._send_via_telegram("123456789", "Test message")

        assert result is True

    @pytest.mark.asyncio
    async def test_send_via_telegram_chat_id_normalization(self):
        """Test normalisation du chat_id Telegram."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = False
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = True
            mock_settings.TELEGRAM_BOT_TOKEN = "test_token"

            with patch('app.services.notification_service.TelegramClient') as mock_tg:
                mock_client = AsyncMock()
                mock_client.send_message.return_value = True
                mock_tg.return_value = mock_client

                service = NotificationService()

                # Chat ID avec espaces/caractères spéciaux
                with patch(
                    'app.services.notification_service.clean_telegram_chat_id',
                    return_value="123456789"
                ) as mock_clean:
                    result = await service._send_via_telegram(" 123 456 789 ", "Test")

                    # Vérifier que clean_telegram_chat_id a été appelé
                    mock_clean.assert_called_once_with(" 123 456 789 ")

        assert result is True

    @pytest.mark.asyncio
    async def test_send_via_telegram_no_client(self):
        """Test envoi Telegram sans client."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = False
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            service = NotificationService()
            result = await service._send_via_telegram("123456789", "Test message")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_via_telegram_exception(self):
        """Test gestion d'exception dans envoi Telegram."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = False
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = True
            mock_settings.TELEGRAM_BOT_TOKEN = "test_token"

            with patch('app.services.notification_service.TelegramClient') as mock_tg:
                mock_client = AsyncMock()
                mock_client.send_message.side_effect = Exception("Bot blocked")
                mock_tg.return_value = mock_client

                service = NotificationService()

                with patch(
                    'app.services.notification_service.clean_telegram_chat_id',
                    return_value="123456789"
                ):
                    result = await service._send_via_telegram("123456789", "Test message")

        assert result is False

    # ==================== Tests get_available_methods ====================

    def test_get_available_methods_none(self):
        """Test aucune méthode disponible."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = False
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            service = NotificationService()
            methods = service.get_available_methods()

        assert methods == []

    def test_get_available_methods_whatsapp_only(self):
        """Test seulement WhatsApp disponible."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = True
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = False

            with patch('app.services.notification_service.WhatsAppClient'):
                service = NotificationService()
                methods = service.get_available_methods()

        assert methods == [DeliveryMethod.WHATSAPP]

    def test_get_available_methods_telegram_only(self):
        """Test seulement Telegram disponible."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = False
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = True
            mock_settings.TELEGRAM_BOT_TOKEN = "test_token"

            with patch('app.services.notification_service.TelegramClient'):
                service = NotificationService()
                methods = service.get_available_methods()

        assert methods == [DeliveryMethod.TELEGRAM]

    def test_get_available_methods_both(self):
        """Test les deux méthodes disponibles."""

        with patch('app.services.notification_service.settings') as mock_settings:
            mock_settings.ENABLE_WHATSAPP_NOTIFICATIONS = True
            mock_settings.WHATSAPP_API_TOKEN = "test_wa"
            mock_settings.ENABLE_TELEGRAM_NOTIFICATIONS = True
            mock_settings.TELEGRAM_BOT_TOKEN = "test_tg"

            with patch('app.services.notification_service.WhatsAppClient'):
                with patch('app.services.notification_service.TelegramClient'):
                    service = NotificationService()
                    methods = service.get_available_methods()

        assert DeliveryMethod.WHATSAPP in methods
        assert DeliveryMethod.TELEGRAM in methods
        assert len(methods) == 2
