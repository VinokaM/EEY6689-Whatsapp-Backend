"""
Telegram Bot Service

Handles sending messages through Telegram Bot API with robust error handling,
retry logic, and comprehensive logging.

Based on Telegram Bot API v7.0+ specifications:
- Rate limiting: 30 messages per second per bot
- Message length: Up to 4096 characters for text messages
- Supports markdown and HTML formatting
"""

import requests
import json
import os
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Union
import hashlib
import hmac

from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Configure logging for Telegram operations
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("telegram_messages.log", encoding='utf-8')
    ]
)
logger = logging.getLogger("telegram_service")


class TelegramAPIError(Exception):
    """Custom exception for Telegram API errors"""
    def __init__(self, message: str, error_code: Optional[int] = None, description: Optional[str] = None):
        self.error_code = error_code
        self.description = description
        super().__init__(message)


class TelegramRateLimiter:
    """
    Rate limiter for Telegram API calls
    Telegram allows 30 messages per second per bot
    """
    def __init__(self, max_calls_per_second: int = 25):  # Conservative limit
        self.max_calls_per_second = max_calls_per_second
        self.calls = []
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        # Remove calls older than 1 second
        self.calls = [call_time for call_time in self.calls if now - call_time < 1.0]
        
        if len(self.calls) >= self.max_calls_per_second:
            sleep_time = 1.0 - (now - self.calls[0])
            if sleep_time > 0:
                logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
        
        self.calls.append(now)


# Global rate limiter instance
rate_limiter = TelegramRateLimiter()


def send_telegram_message(
    chat_id: Union[int, str], 
    message: str, 
    parse_mode: Optional[str] = None,
    disable_web_page_preview: bool = True,
    disable_notification: bool = False,
    reply_to_message_id: Optional[int] = None,
    max_retries: int = 3,
    retry_delay: int = 2
) -> Dict[str, Any]:
    """
    Send a text message via Telegram Bot API with comprehensive error handling.
    
    Args:
        chat_id: Unique identifier for the target chat or username (@username)
        message: Text of the message to be sent (1-4096 characters)
        parse_mode: Send Markdown or HTML, if you want Telegram apps to show bold, italic, etc.
        disable_web_page_preview: Disables link previews for links in this message
        disable_notification: Sends the message silently
        reply_to_message_id: If the message is a reply, ID of the original message
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        Dict containing the API response or error information
        
    Raises:
        TelegramAPIError: When all retry attempts fail
    """
    
    if not TELEGRAM_BOT_TOKEN:
        error_msg = "TELEGRAM_BOT_TOKEN not found in environment variables"
        logger.error(error_msg)
        return {"error": error_msg}
    
    if not message or len(message.strip()) == 0:
        error_msg = "Message cannot be empty"
        logger.error(error_msg)
        return {"error": error_msg}
    
    # Telegram message length limit
    if len(message) > 4096:
        logger.warning(f"Message length ({len(message)}) exceeds Telegram limit (4096). Truncating...")
        message = message[:4093] + "..."
    
    logger.info(f"Sending Telegram message to chat_id: {chat_id}")
    
    # Prepare payload
    payload = {
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": disable_web_page_preview,
        "disable_notification": disable_notification
    }
    
    # Optional parameters
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "TelegramBot/1.0"
    }
    
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"[ATTEMPT {attempt + 1}] Sending message to chat_id: {chat_id}")
            
            # Apply rate limiting
            rate_limiter.wait_if_needed()
            
            # Make API request
            response = requests.post(
                f"{TELEGRAM_API_BASE_URL}/sendMessage",
                headers=headers,
                json=payload,
                timeout=30  # Telegram recommends 30 second timeout
            )
            
            response_data = response.json()
            
            # Check if request was successful
            if response.status_code == 200 and response_data.get("ok"):
                logger.info(f"[SUCCESS] Message sent successfully to chat_id: {chat_id} on attempt {attempt + 1}")
                return {
                    "success": True,
                    "message_id": response_data["result"]["message_id"],
                    "chat_id": response_data["result"]["chat"]["id"],
                    "date": response_data["result"]["date"],
                    "response": response_data
                }
            
            # Handle Telegram API errors
            error_code = response_data.get("error_code")
            description = response_data.get("description", "Unknown error")
            
            # Handle specific error codes
            if error_code == 429:  # Too Many Requests
                retry_after = response_data.get("parameters", {}).get("retry_after", retry_delay)
                logger.warning(f"[RATE LIMIT] Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                continue
            
            elif error_code == 400:  # Bad Request
                if "chat not found" in description.lower():
                    error_msg = f"Chat not found: {chat_id}"
                    logger.error(error_msg)
                    return {"error": error_msg, "error_code": error_code}
                elif "message is too long" in description.lower():
                    error_msg = f"Message too long: {len(message)} characters"
                    logger.error(error_msg)
                    return {"error": error_msg, "error_code": error_code}
            
            elif error_code == 403:  # Forbidden
                error_msg = f"Bot was blocked by user or chat: {chat_id}"
                logger.error(error_msg)
                return {"error": error_msg, "error_code": error_code}
            
            last_error = f"Telegram API error {error_code}: {description}"
            logger.warning(f"[API ERROR] Attempt {attempt + 1} failed: {last_error}")
            
        except requests.exceptions.Timeout as e:
            last_error = f"Request timeout: {str(e)}"
            logger.warning(f"[TIMEOUT] Attempt {attempt + 1} timed out: {str(e)}")
            
        except requests.exceptions.ConnectionError as e:
            last_error = f"Connection error: {str(e)}"
            logger.warning(f"[CONNECTION ERROR] Attempt {attempt + 1} failed: {str(e)}")
            
        except requests.exceptions.RequestException as e:
            last_error = f"Request error: {str(e)}"
            logger.warning(f"[REQUEST ERROR] Attempt {attempt + 1} failed: {str(e)}")
            
        except Exception as e:
            last_error = f"Unexpected error: {str(e)}"
            logger.error(f"[UNEXPECTED ERROR] Attempt {attempt + 1} failed: {str(e)}")
        
        # Wait before retry (except for the last attempt)
        if attempt < max_retries:
            wait_time = retry_delay * (attempt + 1)  # Exponential backoff
            logger.info(f"[RETRY] Waiting {wait_time}s before retry attempt {attempt + 2}...")
            time.sleep(wait_time)
    
    # All attempts failed
    error_message = f"Failed to send Telegram message after {max_retries + 1} attempts. Last error: {last_error}"
    logger.error(error_message)
    
    return {"error": error_message}


def send_telegram_photo(
    chat_id: Union[int, str],
    photo: Union[str, bytes],
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Send a photo via Telegram Bot API.
    
    Args:
        chat_id: Unique identifier for the target chat
        photo: Photo to send (file_id, URL, or file data)
        caption: Photo caption (0-1024 characters)
        parse_mode: Send Markdown or HTML for caption formatting
        max_retries: Maximum number of retry attempts
    
    Returns:
        Dict containing the API response or error information
    """
    
    if not TELEGRAM_BOT_TOKEN:
        return {"error": "TELEGRAM_BOT_TOKEN not found"}
    
    logger.info(f"Sending photo to chat_id: {chat_id}")
    
    payload = {
        "chat_id": chat_id,
        "photo": photo
    }
    
    if caption:
        if len(caption) > 1024:
            caption = caption[:1021] + "..."
        payload["caption"] = caption
    
    if parse_mode:
        payload["parse_mode"] = parse_mode
    
    for attempt in range(max_retries + 1):
        try:
            rate_limiter.wait_if_needed()
            
            response = requests.post(
                f"{TELEGRAM_API_BASE_URL}/sendPhoto",
                json=payload,
                timeout=30
            )
            
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("ok"):
                logger.info(f"[SUCCESS] Photo sent successfully to chat_id: {chat_id}")
                return {"success": True, "response": response_data}
            
            logger.warning(f"[ATTEMPT {attempt + 1}] Failed to send photo: {response_data}")
            
        except Exception as e:
            logger.error(f"[ATTEMPT {attempt + 1}] Error sending photo: {str(e)}")
            
        if attempt < max_retries:
            time.sleep(2 * (attempt + 1))
    
    return {"error": "Failed to send photo after all retry attempts"}


def get_telegram_bot_info() -> Dict[str, Any]:
    """
    Get basic information about the bot.
    
    Returns:
        Dict containing bot information or error
    """
    
    if not TELEGRAM_BOT_TOKEN:
        return {"error": "TELEGRAM_BOT_TOKEN not found"}
    
    try:
        response = requests.get(f"{TELEGRAM_API_BASE_URL}/getMe", timeout=10)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get("ok"):
            bot_info = response_data["result"]
            logger.info(f"Bot info retrieved: @{bot_info.get('username', 'unknown')}")
            return {"success": True, "bot_info": bot_info}
        
        return {"error": f"Failed to get bot info: {response_data}"}
        
    except Exception as e:
        error_msg = f"Error getting bot info: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}


def set_telegram_webhook(webhook_url: str, secret_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Set the webhook URL for receiving updates.
    
    Args:
        webhook_url: HTTPS URL to send updates to
        secret_token: Secret token for webhook security
    
    Returns:
        Dict containing success status or error
    """
    
    if not TELEGRAM_BOT_TOKEN:
        return {"error": "TELEGRAM_BOT_TOKEN not found"}
    
    payload = {"url": webhook_url}
    
    if secret_token:
        payload["secret_token"] = secret_token
    
    try:
        response = requests.post(
            f"{TELEGRAM_API_BASE_URL}/setWebhook",
            json=payload,
            timeout=10
        )
        
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get("ok"):
            logger.info(f"Webhook set successfully: {webhook_url}")
            return {"success": True, "response": response_data}
        
        return {"error": f"Failed to set webhook: {response_data}"}
        
    except Exception as e:
        error_msg = f"Error setting webhook: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}