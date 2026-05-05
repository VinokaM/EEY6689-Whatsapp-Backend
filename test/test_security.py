"""
Security tests for the multi-platform chatbot backend.

Validates that:
- Sensitive credentials are never logged in plain text
- Webhook verification prevents unauthorized access
- Signature validation prevents request forgery
"""

import logging
import pytest


# ---------------------------------------------------------------------------
# Sensitive data protection tests  (Requirements 14.1 – 14.5)
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestSensitiveDataProtection:
    """Tests that tokens and API keys are not exposed in log output."""

    def test_no_whatsapp_token_logging(self, mocker, mock_env_vars, caplog):
        """WhatsApp access token is not logged in plain text."""
        from sendMessage import send_whatsapp_message

        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"messages": [{"id": "x"}]}
        mock_resp.raise_for_status = mocker.Mock()
        mocker.patch("sendMessage.requests.post", return_value=mock_resp)

        with caplog.at_level(logging.DEBUG, logger="whatsapp_service"):
            send_whatsapp_message("1234567890", "Test message")

        token = "test_whatsapp_token"
        for record in caplog.records:
            assert token not in record.message, (
                f"WhatsApp token found in log: {record.message}"
            )

    def test_no_telegram_token_logging(self, mocker, mock_env_vars, caplog):
        """Telegram bot token is not logged in plain text."""
        from telegram.telegram_service import send_telegram_message

        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "ok": True,
            "result": {"message_id": 1, "chat": {"id": 1}, "date": 0},
        }
        mocker.patch("telegram.telegram_service.requests.post", return_value=mock_resp)
        mocker.patch("telegram.telegram_service.time.sleep")

        with caplog.at_level(logging.DEBUG, logger="telegram_service"):
            send_telegram_message(12345, "Test message")

        token = "test_telegram_token"
        for record in caplog.records:
            assert token not in record.message, (
                f"Telegram token found in log: {record.message}"
            )

    def test_no_groq_key_logging(self, mocker, mock_env_vars, caplog):
        """Groq API key is not logged in plain text."""
        from llama_ai.llama_service import get_llama_response

        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "reply"}}]
        }
        mocker.patch("llama_ai.llama_service.requests.post", return_value=mock_resp)

        with caplog.at_level(logging.DEBUG):
            get_llama_response("Hello")

        api_key = "test_groq_key"
        for record in caplog.records:
            assert api_key not in record.message, (
                f"Groq API key found in log: {record.message}"
            )

    def test_webhook_verification_enforcement(self, app_client):
        """WhatsApp webhook verification rejects requests with wrong token."""
        response = app_client.get(
            "/chat",
            query_string={
                "hub.mode": "subscribe",
                "hub.verify_token": "attacker_token",
                "hub.challenge": "steal_this",
            },
        )
        assert response.status_code == 403
        # Challenge string must not be in the response body
        assert b"steal_this" not in response.data

    def test_signature_validation_enforcement(self, app_client):
        """Telegram webhook rejects requests with invalid signature."""
        import importlib
        import app as app_module
        # Ensure the app has a webhook secret configured
        original = app_module.TELEGRAM_WEBHOOK_SECRET
        app_module.TELEGRAM_WEBHOOK_SECRET = "real_secret"

        try:
            response = app_client.post(
                "/telegram",
                json={"update_id": 1},
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong_secret"},
            )
            assert response.status_code == 403
        finally:
            app_module.TELEGRAM_WEBHOOK_SECRET = original
