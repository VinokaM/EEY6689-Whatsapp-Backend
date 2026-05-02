"""
Shared test fixtures and configuration for the comprehensive test suite.

This module provides reusable fixtures for testing the multi-platform chatbot
backend including WhatsApp, Telegram, and LLaMA AI service components.
"""

import json
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def load_fixture(fixture_name: str) -> dict:
    """Load test fixture data from a JSON file in test/fixtures/.

    Args:
        fixture_name: Name of the fixture file (without .json extension).

    Returns:
        Parsed JSON data as a dictionary.
    """
    fixture_path = Path(__file__).parent / "fixtures" / f"{fixture_name}.json"
    with open(fixture_path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app_client():
    """Flask test client for endpoint testing.

    Creates a single Flask test client for the entire test session to avoid
    repeated application initialisation overhead.

    Yields:
        Flask test client configured with TESTING=True.
    """
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=False)
def mock_env_vars(monkeypatch):
    """Mock environment variables required by the application.

    Sets safe test values for all external-service credentials so that no
    real API calls are made and no secrets are needed in the test environment.

    Args:
        monkeypatch: pytest monkeypatch fixture.
    """
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test_whatsapp_token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "test_phone_id")
    monkeypatch.setenv("VERIFY_TOKEN", "test_verify_token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_telegram_token")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "test_webhook_secret")
    monkeypatch.setenv("GROQ_API_KEY", "test_groq_key")


# ---------------------------------------------------------------------------
# Module-scoped API mock fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_whatsapp_api(mocker):
    """Mock WhatsApp API (requests.post) for WhatsApp service tests.

    Returns a mock that simulates a successful WhatsApp message send response.

    Args:
        mocker: pytest-mock mocker fixture.

    Returns:
        MagicMock patching requests.post with a 200 OK WhatsApp response.
    """
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"messages": [{"id": "msg_123"}]}
    mock_response.raise_for_status = mocker.Mock()
    return mocker.patch("requests.post", return_value=mock_response)


@pytest.fixture
def mock_telegram_api(mocker):
    """Mock Telegram API (requests.post) for Telegram service tests.

    Returns a mock that simulates a successful Telegram sendMessage response.

    Args:
        mocker: pytest-mock mocker fixture.

    Returns:
        MagicMock patching requests.post with a 200 OK Telegram response.
    """
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "ok": True,
        "result": {
            "message_id": 42,
            "chat": {"id": 987654321},
            "date": 1234567890,
            "text": "Test message",
        },
    }
    mock_response.raise_for_status = mocker.Mock()
    return mocker.patch("requests.post", return_value=mock_response)


@pytest.fixture
def mock_groq_api(mocker):
    """Mock Groq API (requests.post) for LLaMA service tests.

    Returns a mock that simulates a successful Groq chat completion response.

    Args:
        mocker: pytest-mock mocker fixture.

    Returns:
        MagicMock patching requests.post with a 200 OK Groq response.
    """
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": "llama-3.1-8b-instant",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "AI response text"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }
    mock_response.raise_for_status = mocker.Mock()
    return mocker.patch("requests.post", return_value=mock_response)


# ---------------------------------------------------------------------------
# Function-scoped sample data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_whatsapp_webhook():
    """Valid WhatsApp webhook payload for a text message.

    Returns:
        dict: A minimal but complete WhatsApp webhook payload.
    """
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry_id_001",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "1234567890",
                                "phone_number_id": "phone_id_001",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Test User"},
                                    "wa_id": "1234567890",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "1234567890",
                                    "id": "msg_001",
                                    "timestamp": "1234567890",
                                    "text": {"body": "Hello bot"},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


@pytest.fixture
def sample_telegram_message():
    """Valid Telegram message update payload.

    Returns:
        dict: A minimal but complete Telegram webhook update for a text message.
    """
    return {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "from": {
                "id": 987654321,
                "is_bot": False,
                "first_name": "John",
                "last_name": "Doe",
                "username": "johndoe",
                "language_code": "en",
            },
            "chat": {
                "id": 987654321,
                "first_name": "John",
                "last_name": "Doe",
                "username": "johndoe",
                "type": "private",
            },
            "date": 1234567890,
            "text": "Hello bot",
        },
    }


@pytest.fixture
def sample_ai_response():
    """Mock AI response data from the Groq API.

    Returns:
        dict: A complete Groq chat completion response payload.
    """
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "llama-3.1-8b-instant",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a helpful AI response.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 15,
            "completion_tokens": 25,
            "total_tokens": 40,
        },
    }


@pytest.fixture
def mock_time(mocker):
    """Mock time.time() and time.sleep() for rate-limiting tests.

    Provides a mutable current-time list so tests can advance simulated time
    without waiting for real wall-clock time.

    Args:
        mocker: pytest-mock mocker fixture.

    Returns:
        list: Single-element list [current_time] that tests can mutate.
    """
    current_time = [0.0]

    def time_side_effect():
        return current_time[0]

    def sleep_side_effect(duration):
        current_time[0] += duration

    mocker.patch("time.time", side_effect=time_side_effect)
    mocker.patch("time.sleep", side_effect=sleep_side_effect)

    return current_time
