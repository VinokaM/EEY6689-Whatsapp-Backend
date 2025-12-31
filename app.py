from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return jsonify({
        "message": "Backend is running bro."
    })


if __name__ == "__main__":
    app.run(port=5000, debug=True)