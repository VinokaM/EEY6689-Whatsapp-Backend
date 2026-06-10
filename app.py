from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging

from dotenv import load_dotenv

# WhatsApp imports (unchanged)
from sendMessage import send_whatsapp_message


from whisper.whisper_service import transcribe_voicew


# Telegram imports (new)
from telegram.telegram_service import send_telegram_message, get_telegram_bot_info, download_telegram_voice
from telegram.telegram_webhook import TelegramWebhookHandler

# AI service import (shared)
from llama_ai.llama_service import get_llama_response, transcribe_voice


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


# @app.route("/chat", methods=["POST"])
# def chat():
#     incoming_data = request.json

#     try:
#         changes = incoming_data["entry"][0]["changes"][0]["value"]
#         messages = changes.get("messages")
#         if not messages or len(messages) == 0:
            
#             return jsonify({"status": "ignored", "reason": "No message received"}), 200

#         message = messages[0]
#         message_id = message["id"]
#         user_message = message["text"]["body"]
#         phone_number = message["from"]

#     except (KeyError, IndexError):
#         return jsonify({"status": "ignored", "reason": "Non-message webhook"}), 200
    
#     print(f"User Messge Received from webhook : {user_message}")


#     # reply = "hi from meta"
#     bot_reply = get_llama_response(user_message)

#     return send_whatsapp_message(phone_number, bot_reply)


# @app.route("/chat", methods=["POST"])
# def chat():
#     incoming_data = request.json

#     try:
#         changes = incoming_data["entry"][0]["changes"][0]["value"]
#         messages = changes.get("messages")
#         if not messages or len(messages) == 0:
#             return jsonify({"status": "ignored", "reason": "No message received"}), 200

#         message = messages[0]
#         phone_number = message["from"]
#         message_type = message.get("type")  # "text" or "audio"

#         # ---- TEXT MESSAGE ----
#         if message_type == "text":
#             user_message = message["text"]["body"]
#             print(f"Text Message: {user_message}")

#         # ---- VOICE MESSAGE ----
#         elif message_type == "audio":
#             media_id = message["audio"]["id"]
#             print(f"Voice message received, transcribing...")
            
#             user_message = transcribe_voice(media_id)
            
#             if not user_message:
#                 return send_whatsapp_message(phone_number, 
#                     "Sorry, I could not understand your voice message. Please try again.")
            
#             print(f"Transcribed: {user_message}")
#             # Optional - send transcribed text back to user
#             send_whatsapp_message(phone_number, f"🎤 I heard: {user_message}")

#         else:
#             return jsonify({"status": "ignored", "reason": "Unsupported message type"}), 200

#     except (KeyError, IndexError) as e:
#         print(f"Error: {e}")
#         return jsonify({"status": "ignored", "reason": "Non-message webhook"}), 200

#     # ---- Get AI Response ----
#     bot_reply = get_llama_response(user_message)
#     print(f"Bot Reply: {bot_reply}")

#     return send_whatsapp_message(phone_number, bot_reply)

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
        phone_number = message["from"]
        message_type = message.get("type")

        # ---- TEXT MESSAGE ----
        if message_type == "text":
            user_message = message["text"]["body"]
            print(f"Text Message: {user_message}")

            # Get AI response and reply
            bot_reply = get_llama_response(user_message)
            print(f"Bot Reply: {bot_reply}")
            return send_whatsapp_message(phone_number, bot_reply)

        # ---- VOICE MESSAGE ----
        elif message_type == "audio":
            media_id = message["audio"]["id"]
            print(f"Voice message received, transcribing...")

            transcribed_text = transcribe_voicew(media_id)

            if not transcribed_text:
                return send_whatsapp_message(phone_number,
                    "Sorry, I could not understand your voice message. Please try again.")

            print(f"Transcribed: {transcribed_text}")
            
            return send_whatsapp_message(phone_number, f"🎤 I heard: {transcribed_text}")

        else:
            return jsonify({"status": "ignored", "reason": "Unsupported message type"}), 200

    except (KeyError, IndexError) as e:
        print(f"Error: {e}")
        return jsonify({"status": "ignored", "reason": "Non-message webhook"}), 200
    

@app.route("/webhook/new-user", methods=["POST"])
def new_user_welcome():
    """Supabase webhook endpoint - triggers welcome message on new user registration"""
    try:
        incoming_data = request.json
        new_user = incoming_data.get("record", {})
        
        # Get phone number from supabase record
        # phone_number = new_user.get("phone_number", "94710958550")  # fallback for testing

        phone_number = "94710958550"
        
        welcome_message = (
            "👋 Welcome to *EchoTalk!*\n\n"
            "I'm your personal assistant 🤖\n\n"
            "You can send me anything you face problems with regarding *hearing* and I'll be happy to help you.\n\n"
            "🎤 You can also forward *voice messages* and I will translate them to text for you!\n\n"
            "Let's get started — feel free to send your first message! 😊"
        )
        
        return send_whatsapp_message(phone_number, welcome_message)

    except Exception as e:
        print(f"Welcome webhook error: {e}")
        return jsonify({"status": "error", "reason": str(e)}), 500

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
        
        # ----------------------------------------------------------------
        # Handle voice messages (recorded in-app, OGG/OPUS)
        # ----------------------------------------------------------------
        if parsed_update.get("message_type") == "voice":
            voice_data = parsed_update.get("raw_message", {}).get("voice", {})
            file_id = voice_data.get("file_id")
            is_forwarded = parsed_update.get("is_forwarded", False)

            if not file_id:
                logger.warning("Voice message received but no file_id found")
                send_telegram_message(chat_id, "⚠️ Sorry, I couldn't read your voice message.")
                return jsonify({"status": "error", "reason": "No file_id in voice message"}), 200

            logger.info(f"{'Forwarded v' if is_forwarded else 'V'}oice message from user {user_id}, file_id: {file_id}")

            audio_bytes = download_telegram_voice(file_id)
            if not audio_bytes:
                logger.error(f"Failed to download voice file {file_id}")
                send_telegram_message(chat_id, "⚠️ Sorry, I couldn't download your voice message. Please try again.")
                return jsonify({"status": "error", "reason": "Voice download failed"}), 200

            transcript = transcribe_voice(audio_bytes, filename="voice.ogg")
            if not transcript:
                logger.error("Transcription returned empty result")
                send_telegram_message(chat_id, "⚠️ Sorry, I couldn't understand your voice message. Please try again or send a text message.")
                return jsonify({"status": "error", "reason": "Transcription failed"}), 200

            logger.info(f"Voice transcribed for user {user_id}: {transcript[:80]}")
            prefix = "🔀 *Forwarded voice — I heard:*" if is_forwarded else "🎙️ *I heard:*"
            bot_reply = f"{prefix} _{transcript}_"
            response_result = send_telegram_message(chat_id, bot_reply, parse_mode="Markdown")

            if response_result.get("success"):
                logger.info(f"Sent voice transcript reply to chat {chat_id}")
                return jsonify({"status": "success", "message": "Voice transcription sent", "transcript": transcript, "message_id": response_result.get("message_id")}), 200
            else:
                logger.error(f"Failed to send transcript reply: {response_result.get('error')}")
                return jsonify({"status": "error", "message": "Failed to send transcript"}), 500

        # ----------------------------------------------------------------
        # Handle audio file attachments (MP3, M4A, WAV, etc.)
        # ----------------------------------------------------------------
        if parsed_update.get("message_type") == "audio":
            audio_data = parsed_update.get("raw_message", {}).get("audio", {})
            file_id = audio_data.get("file_id")
            mime_type = audio_data.get("mime_type", "audio/mpeg")
            file_name = audio_data.get("file_name", "audio.mp3")
            is_forwarded = parsed_update.get("is_forwarded", False)

            if not file_id:
                logger.warning("Audio attachment received but no file_id found")
                send_telegram_message(chat_id, "⚠️ Sorry, I couldn't read your audio file.")
                return jsonify({"status": "error", "reason": "No file_id in audio message"}), 200

            logger.info(f"{'Forwarded a' if is_forwarded else 'A'}udio file from user {user_id}: {file_name} ({mime_type}), file_id: {file_id}")

            audio_bytes = download_telegram_voice(file_id)
            if not audio_bytes:
                logger.error(f"Failed to download audio file {file_id}")
                send_telegram_message(chat_id, "⚠️ Sorry, I couldn't download your audio file. Please try again.")
                return jsonify({"status": "error", "reason": "Audio download failed"}), 200

            transcript = transcribe_voice(audio_bytes, filename=file_name)
            if not transcript:
                logger.error("Transcription of audio file returned empty result")
                send_telegram_message(chat_id, "⚠️ Sorry, I couldn't transcribe your audio file. Supported formats: MP3, MP4, M4A, WAV, OGG, WEBM, FLAC.")
                return jsonify({"status": "error", "reason": "Audio transcription failed"}), 200

            logger.info(f"Audio file transcribed for user {user_id}: {transcript[:80]}")
            prefix = "🔀 *Forwarded audio — Transcription:*" if is_forwarded else "🎵 *Transcription:*"
            bot_reply = f"{prefix} _{transcript}_"
            response_result = send_telegram_message(chat_id, bot_reply, parse_mode="Markdown")

            if response_result.get("success"):
                logger.info(f"Sent audio transcript reply to chat {chat_id}")
                return jsonify({"status": "success", "message": "Audio transcription sent", "transcript": transcript, "message_id": response_result.get("message_id")}), 200
            else:
                logger.error(f"Failed to send audio transcript reply: {response_result.get('error')}")
                return jsonify({"status": "error", "message": "Failed to send transcript"}), 500

        # ----------------------------------------------------------------
        # Handle video files and round video notes — transcribe audio track
        # ----------------------------------------------------------------
        if parsed_update.get("message_type") in ("video", "video_note"):
            msg_type = parsed_update.get("message_type")
            raw_key = "video_note" if msg_type == "video_note" else "video"
            media_data = parsed_update.get("raw_message", {}).get(raw_key, {})
            file_id = media_data.get("file_id")
            file_name = media_data.get("file_name", "video.mp4")
            is_forwarded = parsed_update.get("is_forwarded", False)

            if not file_id:
                logger.warning(f"{msg_type} received but no file_id found")
                send_telegram_message(chat_id, "⚠️ Sorry, I couldn't read your video file.")
                return jsonify({"status": "error", "reason": f"No file_id in {msg_type}"}), 200

            logger.info(f"{'Forwarded ' if is_forwarded else ''}{msg_type} from user {user_id}, file_id: {file_id}")

            audio_bytes = download_telegram_voice(file_id)
            if not audio_bytes:
                logger.error(f"Failed to download {msg_type} file {file_id}")
                send_telegram_message(chat_id, "⚠️ Sorry, I couldn't download your video. Please try again.")
                return jsonify({"status": "error", "reason": f"{msg_type} download failed"}), 200

            transcript = transcribe_voice(audio_bytes, filename=file_name)
            if not transcript:
                logger.error(f"Transcription of {msg_type} returned empty result")
                send_telegram_message(chat_id, "⚠️ Sorry, I couldn't transcribe the audio from your video. The video may have no speech or an unsupported format.")
                return jsonify({"status": "error", "reason": f"{msg_type} transcription failed"}), 200

            logger.info(f"{msg_type} transcribed for user {user_id}: {transcript[:80]}")
            fwd_label = "Forwarded video" if is_forwarded else "Video"
            bot_reply = f"🎬 *{fwd_label} — I heard:* _{transcript}_"
            response_result = send_telegram_message(chat_id, bot_reply, parse_mode="Markdown")

            if response_result.get("success"):
                logger.info(f"Sent {msg_type} transcript reply to chat {chat_id}")
                return jsonify({"status": "success", "message": f"{msg_type} transcription sent", "transcript": transcript, "message_id": response_result.get("message_id")}), 200
            else:
                logger.error(f"Failed to send {msg_type} transcript reply: {response_result.get('error')}")
                return jsonify({"status": "error", "message": "Failed to send transcript"}), 500

        # ----------------------------------------------------------------
        # Extract user message (for non-command, non-voice messages)
        # ----------------------------------------------------------------
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