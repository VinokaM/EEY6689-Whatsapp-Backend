from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging

from dotenv import load_dotenv

# WhatsApp imports (unchanged)
from sendMessage import send_whatsapp_message

# Telegram imports (new)
from telegram.telegram_service import send_telegram_message, get_telegram_bot_info
from telegram.telegram_webhook import TelegramWebhookHandler

# AI service import (shared)
from llama_ai.llama_service import get_llama_response

load_dotenv()

app = Flask(__name__)
CORS(app)

# WhatsApp configuration (unchanged)
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')

# Telegram configuration (new)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_WEBHOOK_SECRET = os.getenv('TELEGRAM_WEBHOOK_SECRET')

# Initialize Telegram webhook handler
telegram_handler = TelegramWebhookHandler(TELEGRAM_WEBHOOK_SECRET)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# WHATSAPP ENDPOINTS (UNCHANGED)
# ============================================================================

@app.route("/chat", methods=["GET"])
def verify():
    """WhatsApp webhook verification endpoint"""
    if request.args.get("hub.mode") == "subscribe" \
       and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Verification failed", 403


@app.route("/chat", methods=["POST"])
def chat():
    """WhatsApp webhook endpoint for receiving messages"""
    incoming_data = request.json

    try:
        changes = incoming_data["entry"][0]["changes"][0]["value"]
        messages = changes.get("messages")
        if not messages or len(messages) == 0:
            
            return jsonify({"status": "ignored", "reason": "No message received"}), 200

        message = messages[0]
        message_id = message["id"]
        user_message = message["text"]["body"]
        phone_number = message["from"]

    except (KeyError, IndexError):
        return jsonify({"status": "ignored", "reason": "Non-message webhook"}), 200
    
    print(f"User Messge Received from webhook : {user_message}")


    # reply = "hi from meta"
    bot_reply = get_llama_response(user_message)

    return send_whatsapp_message(phone_number, bot_reply)


# ============================================================================
# TELEGRAM ENDPOINTS (NEW)
# ============================================================================

@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    """Telegram webhook endpoint for receiving updates"""
    
    try:
        # Get request data
        request_data = request.get_json()
        
        if not request_data:
            logger.error("No JSON data received in Telegram webhook")
            return jsonify({"status": "error", "message": "No JSON data"}), 400
        
        # Validate webhook signature if secret token is configured
        signature_header = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
        
        if TELEGRAM_WEBHOOK_SECRET:
            if not telegram_handler.validate_webhook_signature(request.get_data(), signature_header):
                logger.error("Invalid Telegram webhook signature")
                return jsonify({"status": "error", "message": "Invalid signature"}), 403
        
        # Parse the webhook update
        parsed_update = telegram_handler.parse_webhook_update(request_data)
        
        if not parsed_update:
            logger.error("Failed to parse Telegram webhook update")
            return jsonify({"status": "ignored", "reason": "Failed to parse update"}), 200
        
        # Get bot info for mention checking
        bot_info_response = get_telegram_bot_info()
        bot_username = ""
        
        if bot_info_response.get("success"):
            bot_username = bot_info_response["bot_info"].get("username", "")
        
        # Check if we should respond to this update
        if not telegram_handler.should_respond_to_update(parsed_update, bot_username):
            logger.info(f"Ignoring Telegram update {parsed_update.get('update_id')} - not addressed to bot")
            return jsonify({"status": "ignored", "reason": "Not addressed to bot"}), 200
        
        # Get chat ID for response
        chat_id = parsed_update.get("chat_id")
        user_id = parsed_update.get("user_id")
        username = parsed_update.get("username", "Unknown")
        
        # Check for bot commands first (before extracting user message)
        commands = parsed_update.get("commands", [])
        if commands:
            command = commands[0].get("command", "").lower()
            
            logger.info(f"Telegram command received from user {user_id} (@{username}): {command}")
            
            # Handle /start command
            if command == "/start":
                bot_reply = (
                    "🎉 *Welcome to EchoTalk Chat Bot!*\n\n"
                    "I'm here to help you with Hearing Impaired Assistance.\n\n"
                    "📱 *Download EchoTalk App:*\n"
                    "Get the full experience on your smartphone!\n"
                    "[Download from Play Store](https://play.google.com/store/apps/test_url)\n\n"
                    "💬 *Get Started:*\n"
                    "Just send me a message and I'll respond!\n\n"
                    "Need help? Type /help to learn more."
                )
                response_result = send_telegram_message(chat_id, bot_reply, parse_mode="Markdown")
                
                if response_result.get("success"):
                    logger.info(f"Sent /start welcome message to chat {chat_id}")
                    return jsonify({
                        "status": "success", 
                        "message": "Welcome message sent",
                        "message_id": response_result.get("message_id")
                    }), 200
                else:
                    logger.error(f"Failed to send /start message: {response_result.get('error')}")
                    return jsonify({
                        "status": "error", 
                        "message": "Failed to send welcome message",
                        "error": response_result.get("error")
                    }), 500
            
            # Handle /help command
            elif command == "/help":
                bot_reply = (
                    "ℹ️ *How to Use EchoTalk Bot*\n\n"
                    "*What I Can Do:*\n"
                    "• Answer your questions\n"
                    "• Provide information and assistance\n"
                    "• Help with hearing impaired accessibility\n\n"
                    "*How to Chat:*\n"
                    "1️⃣ Simply type your message and send it\n"
                    "2️⃣ I'll process your message and respond\n"
                    "3️⃣ Continue the conversation naturally\n\n"
                    "*Example Messages:*\n"
                    "• \"Hello, how are you?\"\n"
                    "• \"Can you help me with...\"\n"
                    "• \"Tell me about...\"\n\n"
                    "*Available Commands:*\n"
                    "/start - Show welcome message\n"
                    "/help - Show this help message\n\n"
                    "📱 *Download the App:*\n"
                    "[Get EchoTalk on Play Store](https://play.google.com/store/apps/test_url)\n\n"
                    "Ready to chat? Just send me a message! 💬"
                )
                response_result = send_telegram_message(chat_id, bot_reply, parse_mode="Markdown")
                
                if response_result.get("success"):
                    logger.info(f"Sent /help message to chat {chat_id}")
                    return jsonify({
                        "status": "success", 
                        "message": "Help message sent",
                        "message_id": response_result.get("message_id")
                    }), 200
                else:
                    logger.error(f"Failed to send /help message: {response_result.get('error')}")
                    return jsonify({
                        "status": "error", 
                        "message": "Failed to send help message",
                        "error": response_result.get("error")
                    }), 500
        
        # Extract user message (for non-command messages)
        user_message = telegram_handler.extract_user_message(parsed_update)
        
        if not user_message:
            logger.info(f"No message content in Telegram update {parsed_update.get('update_id')}")
            return jsonify({"status": "ignored", "reason": "No message content"}), 200
        
        logger.info(f"Telegram message received from user {user_id} (@{username}): {user_message}")
        
        # Generate AI response using the same service as WhatsApp
        bot_reply = get_llama_response(user_message)
        
        # Send response back to Telegram
        response_result = send_telegram_message(chat_id, bot_reply)
        
        if response_result.get("success"):
            logger.info(f"Successfully sent Telegram response to chat {chat_id}")
            return jsonify({
                "status": "success", 
                "message": "Response sent",
                "message_id": response_result.get("message_id")
            }), 200
        else:
            logger.error(f"Failed to send Telegram response: {response_result.get('error')}")
            return jsonify({
                "status": "error", 
                "message": "Failed to send response",
                "error": response_result.get("error")
            }), 500
    
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {str(e)}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.route("/telegram/info", methods=["GET"])
def telegram_bot_info():
    """Get Telegram bot information"""
    
    if not TELEGRAM_BOT_TOKEN:
        return jsonify({"error": "Telegram bot token not configured"}), 400
    
    bot_info = get_telegram_bot_info()
    
    if bot_info.get("success"):
        return jsonify({
            "status": "success",
            "bot_info": bot_info["bot_info"]
        }), 200
    else:
        return jsonify({
            "status": "error",
            "error": bot_info.get("error")
        }), 500


@app.route("/telegram/webhook", methods=["POST"])
def set_telegram_webhook():
    """Set Telegram webhook URL"""
    
    if not TELEGRAM_BOT_TOKEN:
        return jsonify({"error": "Telegram bot token not configured"}), 400
    
    request_data = request.get_json()
    webhook_url = request_data.get("webhook_url")
    
    if not webhook_url:
        return jsonify({"error": "webhook_url is required"}), 400
    
    from telegram.telegram_service import set_telegram_webhook
    
    result = set_telegram_webhook(webhook_url, TELEGRAM_WEBHOOK_SECRET)
    
    if result.get("success"):
        return jsonify({
            "status": "success",
            "message": "Webhook set successfully",
            "webhook_url": webhook_url
        }), 200
    else:
        return jsonify({
            "status": "error",
            "error": result.get("error")
        }), 500


# ============================================================================
# SHARED ENDPOINTS
# ============================================================================


@app.route("/")
def home():
    """Health check endpoint"""
    return jsonify({
        "message": "Multi-platform chatbot backend is running",
        "platforms": {
            "whatsapp": "enabled" if VERIFY_TOKEN else "not configured",
            "telegram": "enabled" if TELEGRAM_BOT_TOKEN else "not configured"
        },
        "endpoints": {
            "whatsapp_webhook": "/chat",
            "telegram_webhook": "/telegram",
            "telegram_info": "/telegram/info",
            "set_telegram_webhook": "/telegram/webhook"
        }
    })


if __name__ == "__main__":
    # Log startup information
    logger.info("Starting multi-platform chatbot backend...")
    logger.info(f"WhatsApp: {'Configured' if VERIFY_TOKEN else 'Not configured'}")
    logger.info(f"Telegram: {'Configured' if TELEGRAM_BOT_TOKEN else 'Not configured'}")
    
    app.run(port=5000, debug=True)