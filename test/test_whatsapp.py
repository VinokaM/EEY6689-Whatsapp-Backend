"""
WhatsApp webhook and message service tests.

Covers:
- Webhook verification (GET /chat)
- Message reception and parsing (POST /chat)
- Message sending via send_whatsapp_message()
"""

import pytest
import requests


# ---------------------------------------------------------------------------
# Webhook verification tests  (Requirements 2.1 – 2.5)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestWhatsAppWebhookVerification:
    """Tests for the WhatsApp webhook verification endpoint (GET /chat)."""

    def test_verify_webhook_valid_token(self, app_client, monkeypatch):
        """Valid hub.mode + matching verify token returns the challenge string."""
        monkeypatch.setenv("VERIFY_TOKEN", "my_secret_token")
        # Re-import so the module picks up the patched env var
        import importlib, app as app_module
        importlib.reload(app_module)

        response = app_client.get(
            "/chat",
            query_string={
                "hub.mode": "subscribe",
                "hub.verify_token": "my_secret_token",
                "hub.challenge": "challenge_abc123",
            },
        )
        assert response.status_code == 200
        assert b"challenge_abc123" in response.data

    def test_verify_webhook_invalid_token(self, app_client):
        """Wrong verify token returns 403."""
        response = app_client.get(
            "/chat",
            query_string={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "challenge_abc123",
            },
        )
        assert response.status_code == 403

    def test_verify_webhook_invalid_mode(self, app_client):
        """hub.mode other than 'subscribe' returns 403."""
        response = app_client.get(
            "/chat",
            query_string={
                "hub.mode": "unsubscribe",
                "hub.verify_token": "test_verify_token",
                "hub.challenge": "challenge_abc123",
            },
        )
        assert response.status_code == 403

    def test_verify_webhook_missing_parameters(self, app_client):
        """Missing query parameters returns 403."""
        response = app_client.get("/chat")
        assert response.status_code == 403

    def test_verify_webhook_no_external_calls(self, app_client, mocker):
        """Webhook verification does not make any external API calls."""
        mock_post = mocker.patch("requests.post")
        app_client.get(
            "/chat",
            query_string={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong",
                "hub.challenge": "x",
            },
        )
        mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# Message reception tests  (Requirements 3.1 – 3.6)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestWhatsAppMessageReception:
    """Tests for WhatsApp message reception and parsing (POST /chat)."""

    def test_chat_valid_text_message(self, app_client, sample_whatsapp_webhook, mocker):
        """Valid text message webhook triggers AI and returns 200."""
        mocker.patch(
            "llama_ai.llama_service.requests.post"
        ).return_value.json.return_value = {
            "choices": [{"message": {"content": "AI reply"}}]
        }
        mocker.patch("sendMessage.requests.post").return_value.json.return_value = {
            "messages": [{"id": "msg_out_001"}]
        }
        mocker.patch(
            "sendMessage.requests.post"
        ).return_value.raise_for_status = mocker.Mock()

        response = app_client.post("/chat", json=sample_whatsapp_webhook)
        assert response.status_code == 200

    def test_chat_extract_phone_number(self, app_client, sample_whatsapp_webhook, mocker):
        """Phone number from webhook is forwarded to the send function."""
        # The app calls send_whatsapp_message which internally calls requests.post.
        # We mock send_whatsapp_message directly at the app module level.
        mock_send = mocker.patch(
            "app.send_whatsapp_message",
            return_value={"messages": [{"id": "out_001"}]},
        )
        mocker.patch(
            "llama_ai.llama_service.requests.post"
        ).return_value.json.return_value = {
            "choices": [{"message": {"content": "reply"}}]
        }

        app_client.post("/chat", json=sample_whatsapp_webhook)

        assert mock_send.called, "send_whatsapp_message was not called"
        args, _ = mock_send.call_args
        assert args[0] == "1234567890"

    def test_chat_no_messages_array(self, app_client):
        """Webhook without a messages key returns 200 with 'ignored' status."""
        payload = {
            "entry": [{"changes": [{"value": {"messaging_product": "whatsapp"}}]}]
        }
        response = app_client.post("/chat", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("status") == "ignored"

    def test_chat_empty_messages_array(self, app_client):
        """Webhook with an empty messages array returns 200 with 'ignored' status."""
        payload = {
            "entry": [{"changes": [{"value": {"messages": []}}]}]
        }
        response = app_client.post("/chat", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("status") == "ignored"

    def test_chat_malformed_webhook(self, app_client):
        """Completely malformed webhook returns 200 with 'ignored' status."""
        response = app_client.post("/chat", json={"garbage": True})
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("status") == "ignored"

    def test_chat_no_external_calls_on_ignored(self, app_client, mocker):
        """No external API calls are made when the webhook is ignored."""
        mock_post = mocker.patch("requests.post")
        app_client.post("/chat", json={"garbage": True})
        mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# Message sending tests  (Requirements 4.1 – 4.7)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestWhatsAppMessageSending:
    """Tests for send_whatsapp_message() in sendMessage.py."""

    def test_send_whatsapp_message_success(self, mocker, mock_env_vars):
        """Successful send returns the API response data."""
        from sendMessage import send_whatsapp_message

        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"messages": [{"id": "msg_out_001"}]}
        mock_resp.raise_for_status = mocker.Mock()
        mocker.patch("sendMessage.requests.post", return_value=mock_resp)

        result = send_whatsapp_message("1234567890", "Hello")
        assert result == {"messages": [{"id": "msg_out_001"}]}

    def test_send_whatsapp_message_authorization(self, mocker, mock_env_vars):
        """Authorization header contains 'Bearer' and the access token."""
        from sendMessage import send_whatsapp_message

        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"messages": [{"id": "x"}]}
        mock_resp.raise_for_status = mocker.Mock()
        mock_post = mocker.patch("sendMessage.requests.post", return_value=mock_resp)

        send_whatsapp_message("1234567890", "Hello")

        call_kwargs = mock_post.call_args[1]
        auth_header = call_kwargs["headers"]["Authorization"]
        assert auth_header.startswith("Bearer ")

    def test_send_whatsapp_message_payload(self, mocker, mock_env_vars):
        """Payload contains correct recipient and message body fields."""
        from sendMessage import send_whatsapp_message

        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"messages": [{"id": "x"}]}
        mock_resp.raise_for_status = mocker.Mock()
        mock_post = mocker.patch("sendMessage.requests.post", return_value=mock_resp)

        send_whatsapp_message("9876543210", "Test message body")

        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["to"] == "9876543210"
        assert payload["text"]["body"] == "Test message body"
        assert payload["messaging_product"] == "whatsapp"

    def test_send_whatsapp_message_response(self, mocker, mock_env_vars):
        """Return value matches the JSON from the API response."""
        from sendMessage import send_whatsapp_message

        expected = {"messages": [{"id": "msg_abc"}], "extra": "data"}
        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = expected
        mock_resp.raise_for_status = mocker.Mock()
        mocker.patch("sendMessage.requests.post", return_value=mock_resp)

        result = send_whatsapp_message("1234567890", "Hi")
        assert result == expected

    def test_send_whatsapp_message_timeout_retry(self, mocker, mock_env_vars):
        """Timeout on first attempt triggers a retry."""
        from sendMessage import send_whatsapp_message

        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"messages": [{"id": "x"}]}
        mock_resp.raise_for_status = mocker.Mock()

        mock_post = mocker.patch(
            "sendMessage.requests.post",
            side_effect=[requests.exceptions.Timeout("timed out"), mock_resp],
        )
        mocker.patch("sendMessage.time.sleep")  # speed up test

        result = send_whatsapp_message("1234567890", "Hello", max_retries=1)
        assert mock_post.call_count == 2
        assert "messages" in result

    def test_send_whatsapp_message_all_retries_fail(self, mocker, mock_env_vars):
        """When all retries fail an error dictionary is returned."""
        from sendMessage import send_whatsapp_message

        mocker.patch(
            "sendMessage.requests.post",
            side_effect=requests.exceptions.Timeout("timed out"),
        )
        mocker.patch("sendMessage.time.sleep")

        result = send_whatsapp_message("1234567890", "Hello", max_retries=1)
        assert "error" in result


# ---------------------------------------------------------------------------
# Additional coverage tests for app.py endpoints and sendMessage retry paths
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAppEndpoints:
    """Tests for additional app.py endpoints."""

    def test_home_endpoint(self, app_client):
        """GET / returns health check JSON with platform status."""
        response = app_client.get("/")
        assert response.status_code == 200
        data = response.get_json()
        assert "platforms" in data
        assert "endpoints" in data

    def test_telegram_info_endpoint_no_token(self, app_client, monkeypatch):
        """GET /telegram/info returns 400 when bot token is not configured."""
        import app as app_module
        monkeypatch.setattr(app_module, "TELEGRAM_BOT_TOKEN", None)
        response = app_client.get("/telegram/info")
        assert response.status_code == 400

    def test_telegram_info_endpoint_success(self, app_client, mocker, monkeypatch):
        """GET /telegram/info returns bot info on success."""
        import app as app_module
        monkeypatch.setattr(app_module, "TELEGRAM_BOT_TOKEN", "test_token")
        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "ok": True,
            "result": {"id": 1, "username": "testbot", "is_bot": True, "first_name": "Bot"},
        }
        mocker.patch("telegram.telegram_service.requests.get", return_value=mock_resp)

        response = app_client.get("/telegram/info")
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("status") == "success"

    def test_set_telegram_webhook_endpoint_no_token(self, app_client, monkeypatch):
        """POST /telegram/webhook returns 400 when bot token is not configured."""
        import app as app_module
        monkeypatch.setattr(app_module, "TELEGRAM_BOT_TOKEN", None)
        response = app_client.post("/telegram/webhook", json={"webhook_url": "https://example.com"})
        assert response.status_code == 400

    def test_set_telegram_webhook_endpoint_missing_url(self, app_client, monkeypatch):
        """POST /telegram/webhook returns 400 when webhook_url is missing."""
        import app as app_module
        monkeypatch.setattr(app_module, "TELEGRAM_BOT_TOKEN", "test_token")
        response = app_client.post("/telegram/webhook", json={})
        assert response.status_code == 400

    def test_set_telegram_webhook_endpoint_success(self, app_client, mocker, monkeypatch):
        """POST /telegram/webhook returns 200 on success."""
        import app as app_module
        monkeypatch.setattr(app_module, "TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setattr(app_module, "TELEGRAM_WEBHOOK_SECRET", None)
        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True, "result": True}
        mocker.patch("telegram.telegram_service.requests.post", return_value=mock_resp)

        response = app_client.post(
            "/telegram/webhook",
            json={"webhook_url": "https://example.com/telegram"},
        )
        assert response.status_code == 200


@pytest.mark.unit
class TestWhatsAppSendRetryPaths:
    """Tests for sendMessage.py retry error logging paths."""

    def test_send_whatsapp_request_exception(self, mocker, mock_env_vars):
        """RequestException on all attempts returns error dict."""
        from sendMessage import send_whatsapp_message

        mocker.patch(
            "sendMessage.requests.post",
            side_effect=requests.exceptions.RequestException("connection refused"),
        )
        mocker.patch("sendMessage.time.sleep")

        result = send_whatsapp_message("1234567890", "Hello", max_retries=1)
        assert "error" in result

    def test_send_whatsapp_unexpected_exception(self, mocker, mock_env_vars):
        """Unexpected exception on all attempts returns error dict."""
        from sendMessage import send_whatsapp_message

        mocker.patch(
            "sendMessage.requests.post",
            side_effect=ValueError("unexpected"),
        )
        mocker.patch("sendMessage.time.sleep")

        result = send_whatsapp_message("1234567890", "Hello", max_retries=1)
        assert "error" in result
