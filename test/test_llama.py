"""
LLaMA AI service tests.

Covers:
- Response generation for various input types
- Service configuration (system prompt, model name, API endpoint)
"""

import pytest
import requests


# ---------------------------------------------------------------------------
# Response generation tests  (Requirements 11.1 – 11.6)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestLlamaResponseGeneration:
    """Tests for get_llama_response() in llama_ai/llama_service.py."""

    def _mock_groq(self, mocker, content="AI response text"):
        """Helper: mock Groq API to return a successful response."""
        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": content}}]
        }
        return mocker.patch("llama_ai.llama_service.requests.post", return_value=mock_resp)

    def test_llama_response_valid_message(self, mocker, mock_env_vars):
        """Valid user message returns a non-empty string."""
        from llama_ai.llama_service import get_llama_response

        self._mock_groq(mocker, "This is a helpful response.")
        result = get_llama_response("Hello, how are you?")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_llama_response_empty_string(self, mocker, mock_env_vars):
        """Empty string input is handled gracefully (no exception raised)."""
        from llama_ai.llama_service import get_llama_response

        self._mock_groq(mocker, "I need a message to respond to.")
        # Should not raise
        result = get_llama_response("")
        assert isinstance(result, str)

    def test_llama_response_long_message(self, mocker, mock_env_vars):
        """Message longer than 4000 characters is processed without error."""
        from llama_ai.llama_service import get_llama_response

        self._mock_groq(mocker, "Response to long message.")
        long_msg = "A" * 4500
        result = get_llama_response(long_msg)
        assert isinstance(result, str)

    def test_llama_response_special_characters(self, mocker, mock_env_vars):
        """Special characters (Unicode, emojis) are handled correctly."""
        from llama_ai.llama_service import get_llama_response

        self._mock_groq(mocker, "Response with special chars: 🎉")
        result = get_llama_response("Hello 🌍 こんにちは مرحبا")
        assert isinstance(result, str)

    def test_llama_response_api_error(self, mocker, mock_env_vars):
        """Groq API error raises an exception or returns an error indicator."""
        from llama_ai.llama_service import get_llama_response

        mock_resp = mocker.Mock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {
            "error": {"message": "Invalid API key", "type": "invalid_request_error"}
        }
        mocker.patch("llama_ai.llama_service.requests.post", return_value=mock_resp)

        # The current implementation will raise a KeyError on missing 'choices'.
        # We verify the function raises rather than silently returning garbage.
        with pytest.raises(Exception):
            get_llama_response("Hello")


# ---------------------------------------------------------------------------
# Configuration tests  (Requirements 12.1 – 12.5)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestLlamaServiceConfiguration:
    """Tests for LLaMA service configuration constants and system prompt."""

    def test_llama_system_prompt_hearing_impaired(self, mocker, mock_env_vars):
        """System prompt includes guidance for hearing-impaired users."""
        from llama_ai.llama_service import get_llama_response

        mock_post = mocker.patch("llama_ai.llama_service.requests.post")
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "reply"}}]
        }

        get_llama_response("test")

        call_json = mock_post.call_args[1]["json"]
        system_content = call_json["messages"][0]["content"].lower()
        assert "hearing-impaired" in system_content or "hearing impaired" in system_content

    def test_llama_system_prompt_short_sentences(self, mocker, mock_env_vars):
        """System prompt includes 'short, clear sentences' instruction."""
        from llama_ai.llama_service import get_llama_response

        mock_post = mocker.patch("llama_ai.llama_service.requests.post")
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "reply"}}]
        }

        get_llama_response("test")

        call_json = mock_post.call_args[1]["json"]
        system_content = call_json["messages"][0]["content"].lower()
        assert "short" in system_content and "clear" in system_content

    def test_llama_system_prompt_no_phone_calls(self, mocker, mock_env_vars):
        """System prompt includes 'never suggest phone calls' constraint."""
        from llama_ai.llama_service import get_llama_response

        mock_post = mocker.patch("llama_ai.llama_service.requests.post")
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "reply"}}]
        }

        get_llama_response("test")

        call_json = mock_post.call_args[1]["json"]
        system_content = call_json["messages"][0]["content"].lower()
        assert "phone" in system_content

    def test_llama_model_name(self, mocker, mock_env_vars):
        """Model name is 'llama-3.1-8b-instant'."""
        from llama_ai.llama_service import get_llama_response

        mock_post = mocker.patch("llama_ai.llama_service.requests.post")
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "reply"}}]
        }

        get_llama_response("test")

        call_json = mock_post.call_args[1]["json"]
        assert call_json["model"] == "llama-3.1-8b-instant"

    def test_llama_api_endpoint(self, mocker, mock_env_vars):
        """API endpoint is the Groq completions URL."""
        from llama_ai.llama_service import get_llama_response, GROQ_URL

        assert GROQ_URL == "https://api.groq.com/openai/v1/chat/completions"
