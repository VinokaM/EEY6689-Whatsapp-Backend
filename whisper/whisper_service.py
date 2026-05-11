import os
import requests
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")

def download_voice_message(media_id):
    """Step 1 - Get media URL from Meta"""
    url = f"https://graph.facebook.com/v18.0/{media_id}"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    
    response = requests.get(url, headers=headers)
    media_url = response.json().get("url")
    
    """Step 2 - Download the actual audio file"""
    audio_response = requests.get(media_url, headers=headers)
    
    audio_path = f"voice_{media_id}.ogg"
    with open(audio_path, "wb") as f:
        f.write(audio_response.content)
    
    return audio_path

def transcribe_voicew(media_id):
    """Download and transcribe voice message using Groq Whisper v3"""
    try:
        # Download voice file
        audio_path = download_voice_message(media_id)
        
        # Transcribe using Groq Whisper v3
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-large-v3",  # Groq Whisper v3
                file=audio_file,
                language="en"
            )
        
        # Delete audio file after transcription
        os.remove(audio_path)
        
        print(f"Transcribed text: {transcription.text}")
        return transcription.text

    except Exception as e:
        print(f"Transcription error: {e}")
        return None