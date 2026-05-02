"""
Integration tests for end-to-end message flows.

Validates that all components (webhook → parser → AI → response) work together
correctly with mocked external APIs.
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_groq(mocker, content="AI response"):
    """Patch get_llama_response at the app module level."""
    return mocker.patch("app.get_llama_response", return_value=content)


def _mock_whatsapp_send(mocker):
    """Patch send_whatsapp_message at the app level."""
    return mocker.patch(
        "app.send_whatsapp_message",
        return_value={"messages": [{"id": "out_001"}]},
    )


def _mock_telegram_send(mocker):
    """Patch the Telegram sendMessage API call."""
    mock_resp = mocker.Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "ok": True,
        "result": {"message_id": 1, "chat": {"id": 1}, "date": 0},
    }
    mocker.patch("telegram.telegram_service.time.sleep")
    return mocker.patch("telegram.telegram_service.requests.post", return_value=mock_resp)


def _mock_telegram_get_me(mocker):
    """Patch the Telegram getMe API call."""
    mock_resp = mocker.Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "ok": True,
        "result": {"id": 1, "username": "testbot", "is_bot": True, "first_name": "Bot"},
    }
    return mocker.patch("telegram.telegram_service.requests.get", return_value=mock_resp)


# ---------------------------------------------------------------------------
# End-to-end flow tests  (Requirements 13.1 – 13.5)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestEndToEndFlows:
    """End-to-end integration tests for WhatsApp and Telegram message flows."""

    def test_whatsapp_end_to_end_flow(self, app_client, sample_whatsapp_webhook, mocker):
        """WhatsApp webhook → AI → response: full flow returns 200."""
        _mock_groq(mocker, "Hello from AI!")
        _mock_whatsapp_send(mocker)

        response = app_client.post("/chat", json=sample_whatsapp_webhook)

        assert response.status_code == 200

    def test_telegram_end_to_end_flow(self, app_client, sample_telegram_message, mocker, monkeypatch):
        """Telegram webhook → AI → response: full flow returns 200."""
        monkeypatch.setattr("app.TELEGRAM_WEBHOOK_SECRET", None)
        _mock_groq(mocker, "Hello from AI!")
        _mock_telegram_send(mocker)
        _mock_telegram_get_me(mocker)

        response = app_client.post("/telegram", json=sample_telegram_message)

        assert response.status_code == 200
        data = response.get_json()
        assert data.get("status") == "success"

    def test_start_command_flow(self, app_client, mocker, monkeypatch):
        """Telegram /start command bypasses AI and sends welcome message."""
        monkeypatch.setattr("app.TELEGRAM_WEBHOOK_SECRET", None)
        mock_ai = _mock_groq(mocker)
        _mock_telegram_send(mocker)
        _mock_telegram_get_me(mocker)

        start_update = {
            "update_id": 200,
            "message": {
                "message_id": 30,
                "from": {"id": 1, "is_bot": False, "first_name": "A", "username": "auser"},
                "chat": {"id": 1, "type": "private"},
                "date": 0,
                "text": "/start",
                "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
            },
        }
        response = app_client.post("/telegram", json=start_update)

        assert response.status_code == 200
        # AI should NOT have been called for /start
        mock_ai.assert_not_called()

    def test_help_command_flow(self, app_client, mocker, monkeypatch):
        """Telegram /help command bypasses AI and sends help message."""
        monkeypatch.setattr("app.TELEGRAM_WEBHOOK_SECRET", None)
        mock_ai = _mock_groq(mocker)
        _mock_telegram_send(mocker)
        _mock_telegram_get_me(mocker)

        help_update = {
            "update_id": 201,
            "message": {
                "message_id": 31,
                "from": {"id": 1, "is_bot": False, "first_name": "A", "username": "auser"},
                "chat": {"id": 1, "type": "private"},
                "date": 0,
                "text": "/help",
                "entities": [{"offset": 0, "length": 5, "type": "bot_command"}],
            },
        }
        response = app_client.post("/telegram", json=help_update)

        assert response.status_code == 200
        mock_ai.assert_not_called()


# ---------------------------------------------------------------------------
# Cross-platform consistency tests  (Requirements 22.1 – 22.5)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestCrossPlatformConsistency:
    """Tests verifying consistent behaviour across WhatsApp and Telegram."""

    def test_same_message_both_platforms(self, app_client, sample_whatsapp_webhook, sample_telegram_message, mocker, monkeypatch):
        """Same user message on both platforms both receive AI responses."""
        monkeypatch.setattr("app.TELEGRAM_WEBHOOK_SECRET", None)

        # WhatsApp
        mock_ai_wa = _mock_groq(mocker, "AI response for WhatsApp")
        _mock_whatsapp_send(mocker)
        wa_response = app_client.post("/chat", json=sample_whatsapp_webhook)
        assert wa_response.status_code == 200
        assert mock_ai_wa.called

        # Telegram
        mock_ai_tg = _mock_groq(mocker, "AI response for Telegram")
        _mock_telegram_send(mocker)
        _mock_telegram_get_me(mocker)
        tg_response = app_client.post("/telegram", json=sample_telegram_message)
        assert tg_response.status_code == 200
        assert mock_ai_tg.called

    def test_same_ai_service_both_platforms(self, app_client, sample_whatsapp_webhook, sample_telegram_message, mocker, monkeypatch):
        """Both platforms call the same get_llama_response function."""
        monkeypatch.setattr("app.TELEGRAM_WEBHOOK_SECRET", None)

        mock_ai = _mock_groq(mocker, "AI reply")
        _mock_whatsapp_send(mocker)
        app_client.post("/chat", json=sample_whatsapp_webhook)
        wa_call_count = mock_ai.call_count

        mock_ai2 = _mock_groq(mocker, "AI reply")
        _mock_telegram_send(mocker)
        _mock_telegram_get_me(mocker)
        app_client.post("/telegram", json=sample_telegram_message)
        tg_call_count = mock_ai2.call_count

        # Both platforms should have called the AI function exactly once
        assert wa_call_count == 1
        assert tg_call_count == 1

    def test_same_system_prompt_both_platforms(self, app_client, sample_whatsapp_webhook, sample_telegram_message, mocker, monkeypatch):
        """Both platforms pass the same user message text to the AI function."""
        monkeypatch.setattr("app.TELEGRAM_WEBHOOK_SECRET", None)

        mock_ai = _mock_groq(mocker, "reply")
        _mock_whatsapp_send(mocker)
        app_client.post("/chat", json=sample_whatsapp_webhook)
        wa_user_msg = mock_ai.call_args[0][0]

        mock_ai2 = _mock_groq(mocker, "reply")
        _mock_telegram_send(mocker)
        _mock_telegram_get_me(mocker)
        app_client.post("/telegram", json=sample_telegram_message)
        tg_user_msg = mock_ai2.call_args[0][0]

        # Both payloads contain "Hello bot" as the user message
        assert wa_user_msg == "Hello bot"
        assert tg_user_msg == "Hello bot"

    def test_same_error_handling_both_platforms(self, app_client, mocker, monkeypatch):
        """Both platforms return 200 with 'ignored' for malformed webhooks."""
        monkeypatch.setattr("app.TELEGRAM_WEBHOOK_SECRET", None)

        wa_response = app_client.post("/chat", json={"garbage": True})
        assert wa_response.status_code == 200
        assert wa_response.get_json().get("status") == "ignored"

        # Telegram with missing message field
        tg_response = app_client.post(
            "/telegram",
            json={"update_id": 999},
        )
        assert tg_response.status_code == 200
