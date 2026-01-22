import requests
import json
import os
import time
import logging
from datetime import datetime
import threading
import hashlib

from dotenv import load_dotenv
load_dotenv()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("whatsapp_messages.log", encoding='utf-8')
    ]
)
logger = logging.getLogger("whatsapp_service")



def send_whatsapp_message(phone, message, max_retries=2, retry_delay=2):
    
    logger.info(f"Sending text message to {phone}")
    
    last_error = None
    
    for attempt in range(max_retries + 1):  
        try:
            logger.info(f"[ATTEMPT {attempt + 1}] Sending message to {phone}")
            
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": phone,
                "type": "text",
                "text": {
                    "body": message
                }
            }
            
            headers = {
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type": "application/json"
            }
            
            resp = requests.post(
                f"https://graph.facebook.com/v16.0/{WHATSAPP_PHONE_ID}/messages",
                headers=headers,
                json=payload,
                timeout=15  
            )
            
            resp.raise_for_status()
            response_data = resp.json()
            
            
            logger.info(f"[SUCCESS] Text message sent successfully to {phone} on attempt {attempt + 1}")
            return response_data
            
        except requests.exceptions.Timeout as e:
            last_error = f"Timeout error: {str(e)}"
            logger.warning(f"[TIMEOUT] Attempt {attempt + 1} timed out: {str(e)}")
            
        except requests.exceptions.RequestException as e:
            last_error = f"Request error: {str(e)}"
            logger.warning(f"[REQUEST ERROR] Attempt {attempt + 1} failed: {str(e)}")
            
            # Log additional error details if available
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"[API ERROR] API error details: {error_detail}")
                except ValueError:
                    logger.error(f"[API ERROR] API error text: {e.response.text}")
            
        except Exception as e:
            last_error = f"Unexpected error: {str(e)}"
            logger.error(f"[UNEXPECTED ERROR] Attempt {attempt + 1} failed: {str(e)}")
        
        # If this wasn't the last attempt, wait before retrying
        if attempt < max_retries:
            # Progressive backoff: increase delay with each retry
            wait_time = retry_delay * (attempt + 1)
            logger.info(f"[RETRY] Waiting {wait_time}s before retry attempt {attempt + 2}...")
            time.sleep(wait_time)
    
    # All attempts failed
    error_message = f"Failed to send WhatsApp message after {max_retries + 1} attempts. Last error: {last_error}"
    logger.error(error_message)
    
    
    return {"error": error_message}