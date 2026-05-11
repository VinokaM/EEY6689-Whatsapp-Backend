"""
Performance tests for the multi-platform chatbot backend.

Validates that message processing meets response time requirements
when all external APIs are mocked (no network latency).
"""

import time
import logging
import pytest

logger = logging.getLogger("performance_tests")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_whatsapp_webhook():
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "e1",
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "1234567890",
                                    "id": "msg_perf",
                                    "timestamp": "0",
                                    "text": {"body": "Performance test"},
                                    "type": "text",
                                }
                            ]
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


# ---------------------------------------------------------------------------
# Response time tests  (Requirements 15.1 – 15.5)
# ---------------------------------------------------------------------------

@pytest.mark.performance
class TestResponseTime:
    """Performance tests measuring internal processing time with mocked APIs."""

    def test_message_processing_under_2_seconds(self, app_client, mocker):
        """Single WhatsApp message is processed in under 2 seconds."""
        mocker.patch("app.get_llama_response", return_value="Fast AI reply")
        mocker.patch(
            "app.send_whatsapp_message",
            return_value={"messages": [{"id": "out"}]},
        )

        start = time.time()
        response = app_client.post("/chat", json=_sample_whatsapp_webhook())
        elapsed = time.time() - start

        assert response.status_code == 200
        logger.info(f"Single message processing time: {elapsed:.3f}s")
        assert elapsed < 2.0, f"Processing took {elapsed:.3f}s, expected < 2s"

    def test_concurrent_messages_under_5_seconds(self, app_client, mocker):
        """10 sequential WhatsApp messages all complete within 5 seconds total."""
        mocker.patch("app.get_llama_response", return_value="Fast AI reply")
        mocker.patch(
            "app.send_whatsapp_message",
            return_value={"messages": [{"id": "out"}]},
        )

        # Flask test client is not thread-safe; use sequential requests to
        # validate the 5-second total throughput requirement.
        start = time.time()
        statuses = []
        for _ in range(10):
            resp = app_client.post("/chat", json=_sample_whatsapp_webhook())
            statuses.append(resp.status_code)
        elapsed = time.time() - start

        logger.info(f"10 sequential messages processing time: {elapsed:.3f}s")
        assert all(s == 200 for s in statuses), f"Non-200 responses: {statuses}"
        assert elapsed < 5.0, f"Sequential processing took {elapsed:.3f}s, expected < 5s"

    def test_rate_limiting_delays(self, mocker):
        """Rate limiter introduces delay when threshold is exceeded."""
        from telegram.telegram_service import TelegramRateLimiter
        import unittest.mock as mock

        limiter = TelegramRateLimiter(max_calls_per_second=5)
        sleep_calls = []

        def fake_time():
            return 0.1  # All calls at same instant

        def fake_sleep(d):
            sleep_calls.append(d)

        with mock.patch("telegram.telegram_service.time.time", side_effect=fake_time):
            with mock.patch("telegram.telegram_service.time.sleep", side_effect=fake_sleep):
                for _ in range(6):
                    limiter.wait_if_needed()

        assert len(sleep_calls) >= 1, "Rate limiter should have introduced at least one delay"
        logger.info(f"Rate limiter sleep calls: {sleep_calls}")

    def test_performance_metrics_logging(self, app_client, mocker):
        """Performance test logs timing information."""
        mocker.patch("app.get_llama_response", return_value="reply")
        mocker.patch(
            "app.send_whatsapp_message",
            return_value={"messages": [{"id": "out"}]},
        )

        start = time.time()
        response = app_client.post("/chat", json=_sample_whatsapp_webhook())
        elapsed = time.time() - start
        logger.info(f"Test response time: {elapsed:.3f}s")

        assert response.status_code == 200
        assert elapsed < 2.0, f"Response took {elapsed:.3f}s"
