from flask import Flask, request, jsonify
from flask_cors import CORS
import os

from dotenv import load_dotenv

from sendMessage import send_whatsapp_message

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


@app.route("/chat", methods=["POST"])
def chat():
    incoming_data = request.json
    print("message recived")

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


    reply = "hi from meta"

    return send_whatsapp_message(phone_number, reply)


@app.route("/")
def home():
    return jsonify({
        "message": "Backend is running bro."
    })


if __name__ == "__main__":
    app.run(port=5000, debug=True)