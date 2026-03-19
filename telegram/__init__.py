"""
Telegram Bot Integration Module

This module provides Telegram Bot API integration for the chatbot system.
It includes webhook handling, message processing, and response sending.
"""

__version__ = "1.0.0"
__author__ = "Your Team"

from .telegram_service import send_telegram_message
from .telegram_webhook import TelegramWebhookHandler

__all__ = [
    'send_telegram_message',
    'TelegramWebhookHandler'
]