"""
Telegram Webhook Handler

Processes incoming Telegram webhook updates with comprehensive message parsing,
security validation, and error handling.

Supports Telegram Bot API v7.0+ webhook format:
- Text messages
- Photo messages with captions
- Document messages
- Voice messages
- Callback queries from inline keyboards
- Bot commands
"""

import json
import logging
import hashlib
import hmac
import os
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# Telegram webhook configuration
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")

# Configure logging
logger = logging.getLogger("telegram_webhook")


@dataclass
class TelegramUser:
    """Represents a Telegram user"""
    id: int
    is_bot: bool
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None


@dataclass
class TelegramChat:
    """Represents a Telegram chat"""
    id: int
    type: str  # 'private', 'group', 'supergroup', 'channel'
    title: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


@dataclass
class TelegramMessage:
    """Represents a processed Telegram message"""
    message_id: int
    user: TelegramUser
    chat: TelegramChat
    date: int
    text: Optional[str] = None
    caption: Optional[str] = None
    photo: Optional[List[Dict]] = None
    document: Optional[Dict] = None
    voice: Optional[Dict] = None
    reply_to_message: Optional[Dict] = None
    entities: Optional[List[Dict]] = None


class TelegramWebhookHandler:
    """
    Handles Telegram webhook updates with security validation and message parsing
    """
    
    def __init__(self, secret_token: Optional[str] = None):
        """
        Initialize webhook handler
        
        Args:
            secret_token: Secret token for webhook validation
        """
        self.secret_token = secret_token or TELEGRAM_WEBHOOK_SECRET
        
    def validate_webhook_signature(self, request_body: bytes, signature_header: str) -> bool:
        """
        Validate webhook signature for security
        
        Args:
            request_body: Raw request body bytes
            signature_header: X-Telegram-Bot-Api-Secret-Token header value
            
        Returns:
            True if signature is valid, False otherwise
        """
        
        if not self.secret_token:
            logger.warning("No secret token configured - skipping signature validation")
            return True
        
        if not signature_header:
            logger.error("Missing signature header")
            return False
        
        try:
            # Telegram sends the secret token directly in the header
            return hmac.compare_digest(signature_header, self.secret_token)
            
        except Exception as e:
            logger.error(f"Error validating webhook signature: {str(e)}")
            return False
    
    def parse_webhook_update(self, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse Telegram webhook update and extract relevant information
        
        Args:
            update_data: Raw webhook update data
            
        Returns:
            Parsed update information or None if parsing fails
        """
        
        try:
            update_id = update_data.get("update_id")
            
            if not update_id:
                logger.error("Missing update_id in webhook data")
                return None
            
            logger.info(f"Processing Telegram update ID: {update_id}")
            
            # Handle different types of updates
            if "message" in update_data:
                return self._parse_message_update(update_data["message"], update_id)
            
            elif "edited_message" in update_data:
                return self._parse_message_update(update_data["edited_message"], update_id, is_edited=True)
            
            elif "callback_query" in update_data:
                return self._parse_callback_query(update_data["callback_query"], update_id)
            
            elif "inline_query" in update_data:
                return self._parse_inline_query(update_data["inline_query"], update_id)
            
            else:
                logger.info(f"Unsupported update type in update {update_id}")
                return {
                    "update_id": update_id,
                    "type": "unsupported",
                    "raw_data": update_data
                }
                
        except Exception as e:
            logger.error(f"Error parsing webhook update: {str(e)}")
            return None
    
    def _parse_message_update(self, message_data: Dict[str, Any], update_id: int, is_edited: bool = False) -> Dict[str, Any]:
        """Parse a message update"""
        
        try:
            # Extract user information
            user_data = message_data.get("from", {})
            user = TelegramUser(
                id=user_data.get("id"),
                is_bot=user_data.get("is_bot", False),
                first_name=user_data.get("first_name", ""),
                last_name=user_data.get("last_name"),
                username=user_data.get("username"),
                language_code=user_data.get("language_code")
            )
            
            # Extract chat information
            chat_data = message_data.get("chat", {})
            chat = TelegramChat(
                id=chat_data.get("id"),
                type=chat_data.get("type", "private"),
                title=chat_data.get("title"),
                username=chat_data.get("username"),
                first_name=chat_data.get("first_name"),
                last_name=chat_data.get("last_name")
            )
            
            # Extract message content
            message = TelegramMessage(
                message_id=message_data.get("message_id"),
                user=user,
                chat=chat,
                date=message_data.get("date"),
                text=message_data.get("text"),
                caption=message_data.get("caption"),
                photo=message_data.get("photo"),
                document=message_data.get("document"),
                voice=message_data.get("voice"),
                reply_to_message=message_data.get("reply_to_message"),
                entities=message_data.get("entities")
            )
            
            # Determine message type and content
            message_type = "text"
            content = message.text or ""
            
            if message.photo:
                message_type = "photo"
                content = message.caption or ""
            elif message.document:
                message_type = "document"
                content = message.caption or ""
            elif message.voice:
                message_type = "voice"
                content = ""
            
            # Extract bot commands if present
            commands = self._extract_bot_commands(message.text, message.entities)
            
            result = {
                "update_id": update_id,
                "type": "edited_message" if is_edited else "message",
                "message_type": message_type,
                "message_id": message.message_id,
                "user_id": user.id,
                "chat_id": chat.id,
                "chat_type": chat.type,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "content": content,
                "date": message.date,
                "commands": commands,
                "is_bot": user.is_bot,
                "language_code": user.language_code,
                "raw_message": message_data
            }
            
            logger.info(f"Parsed {message_type} message from user {user.id} in chat {chat.id}")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing message update: {str(e)}")
            return None
    
    def _parse_callback_query(self, callback_data: Dict[str, Any], update_id: int) -> Dict[str, Any]:
        """Parse a callback query from inline keyboard"""
        
        try:
            user_data = callback_data.get("from", {})
            message_data = callback_data.get("message", {})
            
            return {
                "update_id": update_id,
                "type": "callback_query",
                "callback_query_id": callback_data.get("id"),
                "user_id": user_data.get("id"),
                "chat_id": message_data.get("chat", {}).get("id"),
                "message_id": message_data.get("message_id"),
                "data": callback_data.get("data"),
                "username": user_data.get("username"),
                "first_name": user_data.get("first_name"),
                "raw_callback": callback_data
            }
            
        except Exception as e:
            logger.error(f"Error parsing callback query: {str(e)}")
            return None
    
    def _parse_inline_query(self, inline_data: Dict[str, Any], update_id: int) -> Dict[str, Any]:
        """Parse an inline query"""
        
        try:
            user_data = inline_data.get("from", {})
            
            return {
                "update_id": update_id,
                "type": "inline_query",
                "inline_query_id": inline_data.get("id"),
                "user_id": user_data.get("id"),
                "query": inline_data.get("query", ""),
                "offset": inline_data.get("offset", ""),
                "username": user_data.get("username"),
                "first_name": user_data.get("first_name"),
                "raw_inline": inline_data
            }
            
        except Exception as e:
            logger.error(f"Error parsing inline query: {str(e)}")
            return None
    
    def _extract_bot_commands(self, text: Optional[str], entities: Optional[List[Dict]]) -> List[Dict[str, str]]:
        """
        Extract bot commands from message text and entities
        
        Args:
            text: Message text
            entities: Message entities (formatting, mentions, commands, etc.)
            
        Returns:
            List of extracted commands with their arguments
        """
        
        commands = []
        
        if not text or not entities:
            return commands
        
        try:
            for entity in entities:
                if entity.get("type") == "bot_command":
                    offset = entity.get("offset", 0)
                    length = entity.get("length", 0)
                    
                    if offset + length <= len(text):
                        command_text = text[offset:offset + length]
                        
                        # Extract command and arguments
                        parts = text[offset:].split(maxsplit=1)
                        command = parts[0] if parts else command_text
                        args = parts[1] if len(parts) > 1 else ""
                        
                        commands.append({
                            "command": command,
                            "args": args,
                            "offset": offset,
                            "length": length
                        })
            
        except Exception as e:
            logger.error(f"Error extracting bot commands: {str(e)}")
        
        return commands
    
    def is_private_chat(self, parsed_update: Dict[str, Any]) -> bool:
        """Check if the message is from a private chat"""
        return parsed_update.get("chat_type") == "private"
    
    def is_group_chat(self, parsed_update: Dict[str, Any]) -> bool:
        """Check if the message is from a group chat"""
        return parsed_update.get("chat_type") in ["group", "supergroup"]
    
    def is_bot_mentioned(self, parsed_update: Dict[str, Any], bot_username: str) -> bool:
        """
        Check if the bot is mentioned in a group message
        
        Args:
            parsed_update: Parsed update data
            bot_username: Bot's username (without @)
            
        Returns:
            True if bot is mentioned or it's a private chat
        """
        
        # Always respond in private chats
        if self.is_private_chat(parsed_update):
            return True
        
        # Check for bot commands
        commands = parsed_update.get("commands", [])
        if commands:
            return True
        
        # Check for @bot_username mentions in text
        content = parsed_update.get("content", "").lower()
        if f"@{bot_username.lower()}" in content:
            return True
        
        # Check message entities for mentions
        raw_message = parsed_update.get("raw_message", {})
        entities = raw_message.get("entities", [])
        
        for entity in entities:
            if entity.get("type") == "mention":
                offset = entity.get("offset", 0)
                length = entity.get("length", 0)
                text = raw_message.get("text", "")
                
                if offset + length <= len(text):
                    mention = text[offset:offset + length]
                    if mention.lower() == f"@{bot_username.lower()}":
                        return True
        
        return False
    
    def extract_user_message(self, parsed_update: Dict[str, Any]) -> str:
        """
        Extract the actual user message content, removing bot mentions and commands
        
        Args:
            parsed_update: Parsed update data
            
        Returns:
            Clean user message text
        """
        
        content = parsed_update.get("content", "").strip()
        
        if not content:
            return ""
        
        # Remove bot commands from the beginning
        commands = parsed_update.get("commands", [])
        if commands:
            # Remove the first command and its arguments
            first_command = commands[0]
            command_end = first_command.get("offset", 0) + first_command.get("length", 0)
            
            # Get text after the command
            remaining_text = content[command_end:].strip()
            
            # If there are arguments, use them as the message
            args = first_command.get("args", "").strip()
            if args:
                return args
            elif remaining_text:
                return remaining_text
            else:
                return ""  # Command without arguments
        
        return content
    
    def should_respond_to_update(self, parsed_update: Dict[str, Any], bot_username: str) -> bool:
        """
        Determine if the bot should respond to this update
        
        Args:
            parsed_update: Parsed update data
            bot_username: Bot's username
            
        Returns:
            True if bot should respond
        """
        
        if not parsed_update:
            return False
        
        update_type = parsed_update.get("type")
        
        # Only respond to messages and edited messages
        if update_type not in ["message", "edited_message"]:
            return False
        
        # Don't respond to messages from bots
        if parsed_update.get("is_bot", False):
            return False
        
        # Check if bot is mentioned or it's a private chat
        return self.is_bot_mentioned(parsed_update, bot_username)