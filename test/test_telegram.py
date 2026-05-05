"""
Telegram webhook handler and service tests.

Covers:
- Webhook signature validation
- Message parsing (text, photo, document, voice)
- Bot command handling
- Chat type detection
- Rate limiting
- Error handling
"""

import pytest
import requests
import time

from telegram.telegram_webhook import TelegramWebhookHandler
from telegram.telegram_service import TelegramRateLimiter


# ---------------------------------------------------------------------------
# Webhook signature validation tests  (Requirements 5.1 – 5.5)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTelegramWebhookSignatureValidation:
    """Tests for TelegramWebhookHandler.validate_webhook_signature()."""

    def test_validate_webhook_signature_valid(self):
        """Matching secret token returns True."""
        handler = TelegramWebhookHandler(secret_token="my_secret")
        assert handler.validate_webhook_signature(b"body", "my_secret") is True

    def test_validate_webhook_signature_invalid(self):
        """Non-matching secret token returns False."""
        handler = TelegramWebhookHandler(secret_token="my_secret")
        assert handler.validate_webhook_signature(b"body", "wrong_secret") is False

    def test_validate_webhook_signature_missing(self):
        """Missing (None) signature header returns False."""
        handler = TelegramWebhookHandler(secret_token="my_secret")
        assert handler.validate_webhook_signature(b"body", None) is False

    def test_validate_webhook_signature_no_token_configured(self, caplog, monkeypatch):
        """When no secret token is configured, validation returns True with a warning."""
        # Patch the module-level TELEGRAM_WEBHOOK_SECRET so the handler sees None
        import telegram.telegram_webhook as tw_module
        monkeypatch.setattr(tw_module, "TELEGRAM_WEBHOOK_SECRET", None)
        handler = TelegramWebhookHandler(secret_token=None)
        import logging
        with caplog.at_level(logging.WARNING, logger="telegram_webhook"):
            result = handler.validate_webhook_signature(b"body", "any_value")
        assert result is True
        assert any(
            "secret token" in r.message.lower() or "skipping" in r.message.lower()
            for r in caplog.records
        )

    def test_validate_webhook_no_external_calls(self, mocker):
        """Signature validation does not make any external API calls."""
        mock_post = mocker.patch("requests.post")
        handler = TelegramWebhookHandler(secret_token="s")
        handler.validate_webhook_signature(b"body", "s")
        mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# Message parsing tests  (Requirements 6.1 – 6.7)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTelegramMessageParsing:
    """Tests for TelegramWebhookHandler.parse_webhook_update()."""

    def _make_handler(self):
        return TelegramWebhookHandler(secret_token="test_secret")

    def test_parse_text_message(self):
        """Text message update is identified as type 'text'."""
        handler = self._make_handler()
        update = {
            "update_id": 1,
            "message": {
                "message_id": 10,
                "from": {"id": 1, "is_bot": False, "first_name": "A"},
                "chat": {"id": 1, "type": "private"},
                "date": 0,
                "text": "Hello",
            },
        }
        result = handler.parse_webhook_update(update)
        assert result is not None
        assert result["message_type"] == "text"

    def test_parse_photo_message(self):
        """Photo message update is identified as type 'photo'."""
        handler = self._make_handler()
        update = {
            "update_id": 2,
            "message": {
                "message_id": 11,
                "from": {"id": 1, "is_bot": False, "first_name": "A"},
                "chat": {"id": 1, "type": "private"},
                "date": 0,
                "photo": [{"file_id": "f1", "file_unique_id": "u1", "width": 100, "height": 100}],
                "caption": "A photo",
            },
        }
        result = handler.parse_webhook_update(update)
        assert result is not None
        assert result["message_type"] == "photo"

    def test_parse_document_message(self):
        """Document message update is identified as type 'document'."""
        handler = self._make_handler()
        update = {
            "update_id": 3,
            "message": {
                "message_id": 12,
                "from": {"id": 1, "is_bot": False, "first_name": "A"},
                "chat": {"id": 1, "type": "private"},
                "date": 0,
                "document": {"file_id": "doc1", "file_unique_id": "u2", "file_name": "test.pdf"},
            },
        }
        result = handler.parse_webhook_update(update)
        assert result is not None
        assert result["message_type"] == "document"

    def test_parse_voice_message(self):
        """Voice message update is identified as type 'voice'."""
        handler = self._make_handler()
        update = {
            "update_id": 4,
            "message": {
                "message_id": 13,
                "from": {"id": 1, "is_bot": False, "first_name": "A"},
                "chat": {"id": 1, "type": "private"},
                "date": 0,
                "voice": {"file_id": "v1", "file_unique_id": "u3", "duration": 5},
            },
        }
        result = handler.parse_webhook_update(update)
        assert result is not None
        assert result["message_type"] == "voice"

    def test_parse_message_extract_fields(self):
        """user_id, chat_id, and username are correctly extracted."""
        handler = self._make_handler()
        update = {
            "update_id": 5,
            "message": {
                "message_id": 14,
                "from": {"id": 42, "is_bot": False, "first_name": "Bob", "username": "bobuser"},
                "chat": {"id": 99, "type": "private"},
                "date": 0,
                "text": "Hi",
            },
        }
        result = handler.parse_webhook_update(update)
        assert result["user_id"] == 42
        assert result["chat_id"] == 99
        assert result["username"] == "bobuser"

    def test_parse_message_extract_commands(self):
        """Bot commands are extracted with their arguments."""
        handler = self._make_handler()
        update = {
            "update_id": 6,
            "message": {
                "message_id": 15,
                "from": {"id": 1, "is_bot": False, "first_name": "A"},
                "chat": {"id": 1, "type": "private"},
                "date": 0,
                "text": "/start hello world",
                "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
            },
        }
        result = handler.parse_webhook_update(update)
        assert len(result["commands"]) == 1
        assert result["commands"][0]["command"] == "/start"
        assert "hello world" in result["commands"][0]["args"]


# ---------------------------------------------------------------------------
# Bot command tests  (Requirements 7.1 – 7.5)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTelegramBotCommands:
    """Tests for /start and /help command handling via the Telegram webhook endpoint."""

    def _start_update(self):
        return {
            "update_id": 100,
            "message": {
                "message_id": 20,
                "from": {"id": 1, "is_bot": False, "first_name": "A", "username": "auser"},
                "chat": {"id": 1, "type": "private"},
                "date": 0,
                "text": "/start",
                "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
            },
        }

    def _help_update(self):
        return {
            "update_id": 101,
            "message": {
                "message_id": 21,
                "from": {"id": 1, "is_bot": False, "first_name": "A", "username": "auser"},
                "chat": {"id": 1, "type": "private"},
                "date": 0,
                "text": "/help",
                "entities": [{"offset": 0, "length": 5, "type": "bot_command"}],
            },
        }

    def test_start_command(self, app_client, mocker, monkeypatch):
        """POST /telegram with /start sends a welcome message."""
        # Disable webhook secret validation for this test
        monkeypatch.setattr("app.TELEGRAM_WEBHOOK_SECRET", None)
        mock_tg_resp = mocker.Mock()
        mock_tg_resp.status_code = 200
        mock_tg_resp.json.return_value = {
            "ok": True,
            "result": {"message_id": 99, "chat": {"id": 1}, "date": 0},
        }
        mocker.patch("telegram.telegram_service.requests.post", return_value=mock_tg_resp)
        mock_get_resp = mocker.Mock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {
            "ok": True,
            "result": {"id": 1, "username": "testbot", "is_bot": True, "first_name": "Bot"},
        }
        mocker.patch("telegram.telegram_service.requests.get", return_value=mock_get_resp)
        mocker.patch("telegram.telegram_service.time.sleep")

        response = app_client.post("/telegram", json=self._start_update())
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("status") == "success"

    def test_help_command(self, app_client, mocker, monkeypatch):
        """POST /telegram with /help sends a help message."""
        monkeypatch.setattr("app.TELEGRAM_WEBHOOK_SECRET", None)
        mock_tg_resp = mocker.Mock()
        mock_tg_resp.status_code = 200
        mock_tg_resp.json.return_value = {
            "ok": True,
            "result": {"message_id": 100, "chat": {"id": 1}, "date": 0},
        }
        mocker.patch("telegram.telegram_service.requests.post", return_value=mock_tg_resp)
        mock_get_resp = mocker.Mock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {
            "ok": True,
            "result": {"id": 1, "username": "testbot", "is_bot": True, "first_name": "Bot"},
        }
        mocker.patch("telegram.telegram_service.requests.get", return_value=mock_get_resp)
        mocker.patch("telegram.telegram_service.time.sleep")

        response = app_client.post("/telegram", json=self._help_update())
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("status") == "success"

    def test_command_with_arguments(self):
        """Command arguments are correctly separated from the command name."""
        handler = TelegramWebhookHandler(secret_token=None)
        update = {
            "update_id": 102,
            "message": {
                "message_id": 22,
                "from": {"id": 1, "is_bot": False, "first_name": "A"},
                "chat": {"id": 1, "type": "private"},
                "date": 0,
                "text": "/start arg1 arg2",
                "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
            },
        }
        result = handler.parse_webhook_update(update)
        assert result["commands"][0]["command"] == "/start"
        assert "arg1" in result["commands"][0]["args"]

    def test_command_in_group(self, app_client, mocker, monkeypatch):
        """Bot command in a group chat is handled appropriately."""
        monkeypatch.setattr("app.TELEGRAM_WEBHOOK_SECRET", None)
        mock_tg_resp = mocker.Mock()
        mock_tg_resp.status_code = 200
        mock_tg_resp.json.return_value = {
            "ok": True,
            "result": {"message_id": 101, "chat": {"id": -100}, "date": 0},
        }
        mocker.patch("telegram.telegram_service.requests.post", return_value=mock_tg_resp)
        mock_get_resp = mocker.Mock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {
            "ok": True,
            "result": {"id": 1, "username": "testbot", "is_bot": True, "first_name": "Bot"},
        }
        mocker.patch("telegram.telegram_service.requests.get", return_value=mock_get_resp)
        mocker.patch("telegram.telegram_service.time.sleep")

        group_start = {
            "update_id": 103,
            "message": {
                "message_id": 23,
                "from": {"id": 2, "is_bot": False, "first_name": "B", "username": "buser"},
                "chat": {"id": -100, "type": "supergroup", "title": "Test Group"},
                "date": 0,
                "text": "/start",
                "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
            },
        }
        response = app_client.post("/telegram", json=group_start)
        # Should respond (command always triggers response)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Chat type detection tests  (Requirements 8.1 – 8.6)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTelegramChatTypeDetection:
    """Tests for is_private_chat(), is_group_chat(), and should_respond_to_update()."""

    def _parsed(self, chat_type, text="Hello", entities=None):
        """Helper: build a minimal parsed update dict."""
        return {
            "update_id": 1,
            "type": "message",
            "message_type": "text",
            "chat_type": chat_type,
            "content": text,
            "commands": [],
            "is_bot": False,
            "raw_message": {"text": text, "entities": entities or []},
        }

    def test_is_private_chat(self):
        """is_private_chat returns True for private chat type."""
        handler = TelegramWebhookHandler(secret_token=None)
        assert handler.is_private_chat(self._parsed("private")) is True

    def test_is_group_chat(self):
        """is_group_chat returns True for group chat type."""
        handler = TelegramWebhookHandler(secret_token=None)
        assert handler.is_group_chat(self._parsed("group")) is True

    def test_is_group_chat_supergroup(self):
        """is_group_chat returns True for supergroup chat type."""
        handler = TelegramWebhookHandler(secret_token=None)
        assert handler.is_group_chat(self._parsed("supergroup")) is True

    def test_should_respond_private_chat(self):
        """should_respond_to_update returns True for private chat."""
        handler = TelegramWebhookHandler(secret_token=None)
        assert handler.should_respond_to_update(self._parsed("private"), "testbot") is True

    def test_should_respond_group_no_mention(self):
        """should_respond_to_update returns False for group without bot mention."""
        handler = TelegramWebhookHandler(secret_token=None)
        assert handler.should_respond_to_update(self._parsed("group", "Hello everyone"), "testbot") is False

    def test_should_respond_group_with_mention(self):
        """should_respond_to_update returns True for group with @bot mention."""
        handler = TelegramWebhookHandler(secret_token=None)
        parsed = self._parsed(
            "supergroup",
            "@testbot help me",
            entities=[{"offset": 0, "length": 8, "type": "mention"}],
        )
        assert handler.should_respond_to_update(parsed, "testbot") is True


# ---------------------------------------------------------------------------
# Rate limiting tests  (Requirements 9.1 – 9.5)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTelegramRateLimiting:
    """Tests for TelegramRateLimiter.wait_if_needed()."""

    def test_rate_limiter_below_threshold(self):
        """25 calls within 1 second do not trigger a sleep."""
        limiter = TelegramRateLimiter(max_calls_per_second=25)
        sleep_called = []

        real_sleep = time.sleep

        def fake_sleep(d):
            sleep_called.append(d)

        import unittest.mock as mock
        with mock.patch("telegram.telegram_service.time.sleep", side_effect=fake_sleep):
            with mock.patch("telegram.telegram_service.time.time", return_value=0.5):
                for _ in range(25):
                    limiter.wait_if_needed()

        assert len(sleep_called) == 0

    def test_rate_limiter_above_threshold(self):
        """26th call within 1 second triggers a sleep."""
        limiter = TelegramRateLimiter(max_calls_per_second=25)
        sleep_called = []

        import unittest.mock as mock

        call_count = [0]

        def fake_time():
            # All calls happen at t=0.1 (within 1 second window)
            return 0.1

        def fake_sleep(d):
            sleep_called.append(d)

        with mock.patch("telegram.telegram_service.time.time", side_effect=fake_time):
            with mock.patch("telegram.telegram_service.time.sleep", side_effect=fake_sleep):
                for _ in range(26):
                    limiter.wait_if_needed()

        assert len(sleep_called) >= 1

    def test_rate_limiter_delay_calculation(self):
        """Delay is positive when rate limit is exceeded."""
        limiter = TelegramRateLimiter(max_calls_per_second=5)
        sleep_durations = []

        import unittest.mock as mock

        def fake_time():
            return 0.05  # All calls at same time

        def fake_sleep(d):
            sleep_durations.append(d)

        with mock.patch("telegram.telegram_service.time.time", side_effect=fake_time):
            with mock.patch("telegram.telegram_service.time.sleep", side_effect=fake_sleep):
                for _ in range(6):
                    limiter.wait_if_needed()

        assert all(d > 0 for d in sleep_durations)

    def test_rate_limiter_timestamp_cleanup(self):
        """Timestamps older than 1 second are removed from the tracking list."""
        limiter = TelegramRateLimiter(max_calls_per_second=25)

        import unittest.mock as mock

        # First batch at t=0
        with mock.patch("telegram.telegram_service.time.time", return_value=0.0):
            with mock.patch("telegram.telegram_service.time.sleep"):
                for _ in range(10):
                    limiter.wait_if_needed()

        assert len(limiter.calls) == 10

        # Second batch at t=2.0 — old timestamps should be cleaned up
        with mock.patch("telegram.telegram_service.time.time", return_value=2.0):
            with mock.patch("telegram.telegram_service.time.sleep"):
                limiter.wait_if_needed()

        # Only the call at t=2.0 should remain
        assert len(limiter.calls) == 1


# ---------------------------------------------------------------------------
# Error handling tests  (Requirements 10.1 – 10.6)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTelegramErrorHandling:
    """Tests for send_telegram_message() error handling in telegram_service.py."""

    def _mock_response(self, mocker, status_code, json_data):
        """Helper: build a mock requests.Response."""
        mock_resp = mocker.Mock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = json_data
        return mock_resp

    def test_telegram_error_chat_not_found(self, mocker, mock_env_vars):
        """400 'chat not found' returns an error dictionary."""
        from telegram.telegram_service import send_telegram_message

        mocker.patch(
            "telegram.telegram_service.requests.post",
            return_value=self._mock_response(
                mocker, 400, {"ok": False, "error_code": 400, "description": "Bad Request: chat not found"}
            ),
        )
        mocker.patch("telegram.telegram_service.time.sleep")

        result = send_telegram_message(99999, "Hello")
        assert "error" in result

    def test_telegram_error_bot_blocked(self, mocker, mock_env_vars):
        """403 'bot blocked' returns an error dictionary."""
        from telegram.telegram_service import send_telegram_message

        mocker.patch(
            "telegram.telegram_service.requests.post",
            return_value=self._mock_response(
                mocker, 403, {"ok": False, "error_code": 403, "description": "Forbidden: bot was blocked by the user"}
            ),
        )
        mocker.patch("telegram.telegram_service.time.sleep")

        result = send_telegram_message(12345, "Hello")
        assert "error" in result

    def test_telegram_error_rate_limit(self, mocker, mock_env_vars):
        """429 rate limit triggers retry with retry_after delay."""
        from telegram.telegram_service import send_telegram_message

        rate_limit_resp = self._mock_response(
            mocker,
            429,
            {
                "ok": False,
                "error_code": 429,
                "description": "Too Many Requests",
                "parameters": {"retry_after": 1},
            },
        )
        success_resp = self._mock_response(
            mocker,
            200,
            {"ok": True, "result": {"message_id": 1, "chat": {"id": 1}, "date": 0}},
        )
        mock_post = mocker.patch(
            "telegram.telegram_service.requests.post",
            side_effect=[rate_limit_resp, success_resp],
        )
        mock_sleep = mocker.patch("telegram.telegram_service.time.sleep")

        result = send_telegram_message(12345, "Hello", max_retries=2)
        assert result.get("success") is True
        # sleep should have been called with retry_after value
        assert mock_sleep.called

    def test_telegram_error_timeout(self, mocker, mock_env_vars):
        """Network timeout triggers retry logic."""
        from telegram.telegram_service import send_telegram_message

        success_resp = self._mock_response(
            mocker,
            200,
            {"ok": True, "result": {"message_id": 2, "chat": {"id": 1}, "date": 0}},
        )
        mock_post = mocker.patch(
            "telegram.telegram_service.requests.post",
            side_effect=[requests.exceptions.Timeout("timed out"), success_resp],
        )
        mocker.patch("telegram.telegram_service.time.sleep")

        result = send_telegram_message(12345, "Hello", max_retries=1)
        assert mock_post.call_count == 2
        assert result.get("success") is True

    def test_telegram_error_all_retries_fail(self, mocker, mock_env_vars):
        """When all retries fail an error message is returned."""
        from telegram.telegram_service import send_telegram_message

        mocker.patch(
            "telegram.telegram_service.requests.post",
            side_effect=requests.exceptions.Timeout("timed out"),
        )
        mocker.patch("telegram.telegram_service.time.sleep")

        result = send_telegram_message(12345, "Hello", max_retries=1)
        assert "error" in result


# ---------------------------------------------------------------------------
# Additional coverage tests for telegram_service.py and telegram_webhook.py
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTelegramServiceAdditional:
    """Additional tests to improve coverage of telegram_service.py."""

    def test_send_telegram_photo_success(self, mocker, mock_env_vars):
        """send_telegram_photo returns success on 200 OK."""
        from telegram.telegram_service import send_telegram_photo

        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True, "result": {"message_id": 5}}
        mocker.patch("telegram.telegram_service.requests.post", return_value=mock_resp)
        mocker.patch("telegram.telegram_service.time.sleep")

        result = send_telegram_photo(12345, "file_id_001", caption="Test photo")
        assert result.get("success") is True

    def test_send_telegram_photo_no_token(self, monkeypatch):
        """send_telegram_photo returns error when token is missing."""
        from telegram.telegram_service import send_telegram_photo
        import telegram.telegram_service as ts
        monkeypatch.setattr(ts, "TELEGRAM_BOT_TOKEN", None)

        result = send_telegram_photo(12345, "file_id_001")
        assert "error" in result

    def test_set_telegram_webhook_success(self, mocker, mock_env_vars):
        """set_telegram_webhook returns success on 200 OK."""
        from telegram.telegram_service import set_telegram_webhook

        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True, "result": True}
        mocker.patch("telegram.telegram_service.requests.post", return_value=mock_resp)

        result = set_telegram_webhook("https://example.com/webhook", "secret")
        assert result.get("success") is True

    def test_set_telegram_webhook_no_token(self, monkeypatch):
        """set_telegram_webhook returns error when token is missing."""
        from telegram.telegram_service import set_telegram_webhook
        import telegram.telegram_service as ts
        monkeypatch.setattr(ts, "TELEGRAM_BOT_TOKEN", None)

        result = set_telegram_webhook("https://example.com/webhook")
        assert "error" in result

    def test_get_telegram_bot_info_no_token(self, monkeypatch):
        """get_telegram_bot_info returns error when token is missing."""
        from telegram.telegram_service import get_telegram_bot_info
        import telegram.telegram_service as ts
        monkeypatch.setattr(ts, "TELEGRAM_BOT_TOKEN", None)

        result = get_telegram_bot_info()
        assert "error" in result

    def test_send_telegram_message_no_token(self, monkeypatch):
        """send_telegram_message returns error when token is missing."""
        from telegram.telegram_service import send_telegram_message
        import telegram.telegram_service as ts
        monkeypatch.setattr(ts, "TELEGRAM_BOT_TOKEN", None)

        result = send_telegram_message(12345, "Hello")
        assert "error" in result

    def test_send_telegram_message_empty(self, mocker, mock_env_vars):
        """send_telegram_message returns error for empty message."""
        from telegram.telegram_service import send_telegram_message

        result = send_telegram_message(12345, "")
        assert "error" in result

    def test_send_telegram_message_truncation(self, mocker, mock_env_vars):
        """Messages over 4096 chars are truncated to 4096 with ellipsis."""
        from telegram.telegram_service import send_telegram_message

        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "ok": True,
            "result": {"message_id": 1, "chat": {"id": 1}, "date": 0},
        }
        mock_post = mocker.patch("telegram.telegram_service.requests.post", return_value=mock_resp)
        mocker.patch("telegram.telegram_service.time.sleep")

        long_msg = "A" * 5000
        send_telegram_message(12345, long_msg)

        sent_text = mock_post.call_args[1]["json"]["text"]
        assert len(sent_text) == 4096
        assert sent_text.endswith("...")


@pytest.mark.unit
class TestTelegramWebhookAdditional:
    """Additional tests to improve coverage of telegram_webhook.py."""

    def test_parse_callback_query(self):
        """Callback query updates are parsed correctly."""
        handler = TelegramWebhookHandler(secret_token=None)
        update = {
            "update_id": 500,
            "callback_query": {
                "id": "cq_001",
                "from": {"id": 1, "is_bot": False, "first_name": "A", "username": "auser"},
                "message": {
                    "message_id": 10,
                    "chat": {"id": 1, "type": "private"},
                },
                "data": "button_pressed",
            },
        }
        result = handler.parse_webhook_update(update)
        assert result is not None
        assert result["type"] == "callback_query"
        assert result["data"] == "button_pressed"

    def test_parse_inline_query(self):
        """Inline query updates are parsed correctly."""
        handler = TelegramWebhookHandler(secret_token=None)
        update = {
            "update_id": 501,
            "inline_query": {
                "id": "iq_001",
                "from": {"id": 1, "is_bot": False, "first_name": "A", "username": "auser"},
                "query": "search term",
                "offset": "",
            },
        }
        result = handler.parse_webhook_update(update)
        assert result is not None
        assert result["type"] == "inline_query"
        assert result["query"] == "search term"

    def test_parse_unsupported_update_type(self):
        """Unsupported update types return a dict with type 'unsupported'."""
        handler = TelegramWebhookHandler(secret_token=None)
        update = {"update_id": 502, "poll": {"id": "poll_001"}}
        result = handler.parse_webhook_update(update)
        assert result is not None
        assert result["type"] == "unsupported"

    def test_extract_user_message_no_content(self):
        """extract_user_message returns empty string when content is empty."""
        handler = TelegramWebhookHandler(secret_token=None)
        parsed = {"content": "", "commands": []}
        assert handler.extract_user_message(parsed) == ""

    def test_extract_user_message_command_no_args(self):
        """extract_user_message returns empty string for command without args."""
        handler = TelegramWebhookHandler(secret_token=None)
        parsed = {
            "content": "/start",
            "commands": [{"command": "/start", "args": "", "offset": 0, "length": 6}],
        }
        assert handler.extract_user_message(parsed) == ""

    def test_parse_edited_message(self):
        """Edited message updates are parsed with type 'edited_message'."""
        handler = TelegramWebhookHandler(secret_token=None)
        update = {
            "update_id": 503,
            "edited_message": {
                "message_id": 20,
                "from": {"id": 1, "is_bot": False, "first_name": "A"},
                "chat": {"id": 1, "type": "private"},
                "date": 0,
                "text": "Edited text",
            },
        }
        result = handler.parse_webhook_update(update)
        assert result is not None
        assert result["type"] == "edited_message"
