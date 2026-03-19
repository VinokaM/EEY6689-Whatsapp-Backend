#!/usr/bin/env python3
"""
Telegram Bot Setup and Testing Script

This script helps you configure and test your Telegram bot integration.
It provides utilities for:
- Setting up webhook
- Testing bot connectivity
- Validating configuration
- Sending test messages
"""

import os
import sys
import requests
import json
from typing import Dict, Any
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram.telegram_service import (
    get_telegram_bot_info, 
    set_telegram_webhook, 
    send_telegram_message
)

load_dotenv()

class TelegramBotSetup:
    """Telegram bot setup and testing utilities"""
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
        self.base_url = os.getenv("BASE_URL")
        
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate bot configuration"""
        
        issues = []
        
        if not self.bot_token:
            issues.append("TELEGRAM_BOT_TOKEN not found in environment")
        elif not self.bot_token.startswith("bot"):
            issues.append("TELEGRAM_BOT_TOKEN should start with 'bot'")
        
        if not self.webhook_secret:
            issues.append("TELEGRAM_WEBHOOK_SECRET not configured (recommended for security)")
        
        if not self.base_url:
            issues.append("BASE_URL not configured (needed for webhook)")
        elif not self.base_url.startswith("https://"):
            issues.append("BASE_URL must use HTTPS for Telegram webhooks")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "config": {
                "bot_token_configured": bool(self.bot_token),
                "webhook_secret_configured": bool(self.webhook_secret),
                "base_url_configured": bool(self.base_url),
                "base_url": self.base_url
            }
        }
    
    def test_bot_connection(self) -> Dict[str, Any]:
        """Test connection to Telegram Bot API"""
        
        print("Testing Telegram bot connection...")
        
        result = get_telegram_bot_info()
        
        if result.get("success"):
            bot_info = result["bot_info"]
            print(f"✅ Bot connection successful!")
            print(f"   Bot Name: {bot_info.get('first_name')}")
            print(f"   Username: @{bot_info.get('username')}")
            print(f"   Bot ID: {bot_info.get('id')}")
            print(f"   Can Join Groups: {bot_info.get('can_join_groups', False)}")
            print(f"   Can Read All Group Messages: {bot_info.get('can_read_all_group_messages', False)}")
            return {"success": True, "bot_info": bot_info}
        else:
            print(f"❌ Bot connection failed: {result.get('error')}")
            return {"success": False, "error": result.get("error")}
    
    def setup_webhook(self) -> Dict[str, Any]:
        """Set up Telegram webhook"""
        
        if not self.base_url:
            return {"success": False, "error": "BASE_URL not configured"}
        
        webhook_url = f"{self.base_url}/telegram"
        
        print(f"Setting up Telegram webhook...")
        print(f"Webhook URL: {webhook_url}")
        
        result = set_telegram_webhook(webhook_url, self.webhook_secret)
        
        if result.get("success"):
            print("✅ Webhook set successfully!")
            return {"success": True, "webhook_url": webhook_url}
        else:
            print(f"❌ Failed to set webhook: {result.get('error')}")
            return {"success": False, "error": result.get("error")}
    
    def get_webhook_info(self) -> Dict[str, Any]:
        """Get current webhook information"""
        
        if not self.bot_token:
            return {"success": False, "error": "Bot token not configured"}
        
        try:
            api_url = f"https://api.telegram.org/bot{self.bot_token}/getWebhookInfo"
            response = requests.get(api_url, timeout=10)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("ok"):
                webhook_info = response_data["result"]
                
                print("Current webhook information:")
                print(f"   URL: {webhook_info.get('url', 'Not set')}")
                print(f"   Has Custom Certificate: {webhook_info.get('has_custom_certificate', False)}")
                print(f"   Pending Update Count: {webhook_info.get('pending_update_count', 0)}")
                print(f"   Last Error Date: {webhook_info.get('last_error_date', 'None')}")
                print(f"   Last Error Message: {webhook_info.get('last_error_message', 'None')}")
                print(f"   Max Connections: {webhook_info.get('max_connections', 40)}")
                
                return {"success": True, "webhook_info": webhook_info}
            else:
                return {"success": False, "error": response_data}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_test_message(self, chat_id: str) -> Dict[str, Any]:
        """Send a test message to verify bot functionality"""
        
        test_message = """🤖 **Telegram Bot Test Message**

Hello! This is a test message from your Telegram bot.

✅ Bot is working correctly
✅ Webhook is configured
✅ AI integration is ready

You can now start chatting with the bot!"""
        
        print(f"Sending test message to chat ID: {chat_id}")
        
        result = send_telegram_message(
            chat_id=chat_id,
            message=test_message,
            parse_mode="Markdown"
        )
        
        if result.get("success"):
            print("✅ Test message sent successfully!")
            return {"success": True, "message_id": result.get("message_id")}
        else:
            print(f"❌ Failed to send test message: {result.get('error')}")
            return {"success": False, "error": result.get("error")}
    
    def run_full_setup(self):
        """Run complete setup process"""
        
        print("=" * 60)
        print("TELEGRAM BOT SETUP")
        print("=" * 60)
        
        # Step 1: Validate configuration
        print("\n1. Validating configuration...")
        config_result = self.validate_configuration()
        
        if not config_result["valid"]:
            print("❌ Configuration issues found:")
            for issue in config_result["issues"]:
                print(f"   - {issue}")
            print("\nPlease fix these issues before continuing.")
            return False
        else:
            print("✅ Configuration is valid!")
        
        # Step 2: Test bot connection
        print("\n2. Testing bot connection...")
        connection_result = self.test_bot_connection()
        
        if not connection_result.get("success"):
            print("❌ Cannot connect to Telegram Bot API. Please check your bot token.")
            return False
        
        # Step 3: Get current webhook info
        print("\n3. Checking current webhook status...")
        self.get_webhook_info()
        
        # Step 4: Set up webhook
        print("\n4. Setting up webhook...")
        webhook_result = self.setup_webhook()
        
        if not webhook_result.get("success"):
            print("❌ Failed to set up webhook.")
            return False
        
        # Step 5: Final verification
        print("\n5. Final webhook verification...")
        self.get_webhook_info()
        
        print("\n" + "=" * 60)
        print("SETUP COMPLETE!")
        print("=" * 60)
        print("\nYour Telegram bot is now configured and ready to use.")
        print(f"Webhook URL: {webhook_result.get('webhook_url')}")
        print("\nTo test the bot:")
        print("1. Start your Flask application")
        print("2. Send a message to your bot on Telegram")
        print("3. Check the logs for incoming messages")
        
        return True


def main():
    """Main setup function"""
    
    setup = TelegramBotSetup()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "validate":
            result = setup.validate_configuration()
            print(json.dumps(result, indent=2))
            
        elif command == "test":
            setup.test_bot_connection()
            
        elif command == "webhook":
            setup.setup_webhook()
            
        elif command == "info":
            setup.get_webhook_info()
            
        elif command == "send":
            if len(sys.argv) < 3:
                print("Usage: python telegram_setup.py send <chat_id>")
                return
            chat_id = sys.argv[2]
            setup.send_test_message(chat_id)
            
        else:
            print("Available commands:")
            print("  validate - Validate configuration")
            print("  test     - Test bot connection")
            print("  webhook  - Set up webhook")
            print("  info     - Get webhook info")
            print("  send     - Send test message")
            print("  (no args) - Run full setup")
    else:
        # Run full setup
        setup.run_full_setup()


if __name__ == "__main__":
    main()