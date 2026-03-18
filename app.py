from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os

from dotenv import load_dotenv

from sendMessage import send_whatsapp_message, send_video_message, send_image_message
from llama_ai.llama_service import get_llama_response
from sign_service.sign_service import text_to_sign_list

load_dotenv()

app = Flask(__name__)
CORS(app)

VERIFY_TOKEN    = os.getenv('VERIFY_TOKEN')
BASE_URL = os.getenv("BASE_URL")


@app.route("/chat", methods=["GET"])
def verify():
    if request.args.get("hub.mode") == "subscribe" \
       and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Verification failed", 403


@app.route("/static/<filename>")
def serve_file(filename):
    return send_from_directory("static", filename)


@app.route("/chat", methods=["POST"])
def chat():
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


    reply = "hello"
    bot_reply = get_llama_response(user_message)

    signs = text_to_sign_list(reply)

    send_whatsapp_message(phone_number, "🤟 Sign Language:")

    for sign in signs:
        if sign["type"] == "letter":
            send_image_message(
                phone_number,
                sign["url"],
                caption=sign["text"].upper()
            )

    return send_whatsapp_message(phone_number, bot_reply)


@app.route("/")
def home():
    return jsonify({
        "message": "Backend is running bro."
    })


if __name__ == "__main__":
    app.run(port=5000, debug=True)