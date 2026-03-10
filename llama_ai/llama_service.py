from dotenv import load_dotenv
import os
from groq import Groq
import requests

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

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