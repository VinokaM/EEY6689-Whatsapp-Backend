from flask import Flask, request, jsonify
from flask_cors import CORS
import os

from dotenv import load_dotenv

from sendMessage import send_whatsapp_message
from llama_ai.llama_service import get_llama_response
from whisper.whisper_service import transcribe_voice

load_dotenv()

app = Flask(__name__)
CORS(app)

VERIFY_TOKEN    = os.getenv('VERIFY_TOKEN')


@app.route("/chat", methods=["GET"])
def verify():
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


@app.route("/chat", methods=["POST"])
def chat():
    incoming_data = request.json

    try:
        changes = incoming_data["entry"][0]["changes"][0]["value"]
        messages = changes.get("messages")
        if not messages or len(messages) == 0:
            return jsonify({"status": "ignored", "reason": "No message received"}), 200

        message = messages[0]
        phone_number = message["from"]
        message_type = message.get("type")  # "text" or "audio"

        # ---- TEXT MESSAGE ----
        if message_type == "text":
            user_message = message["text"]["body"]
            print(f"Text Message: {user_message}")

        # ---- VOICE MESSAGE ----
        elif message_type == "audio":
            media_id = message["audio"]["id"]
            print(f"Voice message received, transcribing...")
            
            user_message = transcribe_voice(media_id)
            
            if not user_message:
                return send_whatsapp_message(phone_number, 
                    "Sorry, I could not understand your voice message. Please try again.")
            
            print(f"Transcribed: {user_message}")
            # Optional - send transcribed text back to user
            send_whatsapp_message(phone_number, f"🎤 I heard: {user_message}")

        else:
            return jsonify({"status": "ignored", "reason": "Unsupported message type"}), 200

    except (KeyError, IndexError) as e:
        print(f"Error: {e}")
        return jsonify({"status": "ignored", "reason": "Non-message webhook"}), 200

    # ---- Get AI Response ----
    bot_reply = get_llama_response(user_message)
    print(f"Bot Reply: {bot_reply}")

    return send_whatsapp_message(phone_number, bot_reply)

@app.route("/")
def home():
    return jsonify({
        "message": "Backend is running bro."
    })


if __name__ == "__main__":
    app.run(port=5000, debug=True)