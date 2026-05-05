from dotenv import load_dotenv
import os
import io
import logging
from groq import Groq
import requests

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

logger = logging.getLogger(__name__)

# Groq client (reused for both chat and transcription)
_groq_client = Groq(api_key=GROQ_API_KEY)


def transcribe_voice(audio_bytes: bytes, filename: str = "voice.ogg") -> str:
    """
    Transcribe audio bytes using Groq Whisper API.

    Args:
        audio_bytes: Raw audio file content (OGG/OPUS from Telegram)
        filename: Filename hint so Groq knows the format (default: voice.ogg)

    Returns:
        Transcribed text string, or empty string on failure
    """
    try:
        logger.info(f"Transcribing audio file: {filename} ({len(audio_bytes)} bytes)")

        transcription = _groq_client.audio.transcriptions.create(
            file=(filename, io.BytesIO(audio_bytes)),
            model="whisper-large-v3-turbo",  # Fast, multilingual, cheap ($0.04/hr)
            response_format="text",
        )

        # When response_format="text", the result is a plain string
        transcript = transcription if isinstance(transcription, str) else transcription.text
        logger.info(f"Transcription successful: {transcript[:80]}...")
        return transcript.strip()

    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        return ""


def get_llama_response(user_message):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a friendly assistant for hearing-impaired users. Reply in short, clear sentences. Use simple words. Use bullet points for steps. Never suggest phone calls — only text/chat solutions. Be warm and patient"},
            {"role": "user", "content": user_message}
        ]
    }

    response = requests.post(GROQ_URL, headers=headers, json=data)
    response_json = response.json()

    return response_json["choices"][0]["message"]["content"]