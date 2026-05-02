# Quick Start

## Set up Python virtual environment (if not already activated):

```bash
python -m venv venv
venv\Scripts\activate
```

## Install dependencies:

```bash
pip install -r requirements.txt
```

## Configure environment variables:

1. Copy `.env.example` to `.env`
2. Fill in your credentials:
   - **WhatsApp**: `VERIFY_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`
   - **Telegram**: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`
   - **AI**: `GROQ_API_KEY`
   - **BASE_URL**: Your ngrok or public HTTPS URL

## Set up ngrok (for webhook testing):

```bash
ngrok http 5000
```

Copy the HTTPS URL to your `.env` as `BASE_URL`.

## Verify For Telegram:

```bash
python telegram_setup.py
```

## Run the application:

```bash
python app.py
```

The server will start on [http://localhost:5000](http://localhost:5000).

---

# Testing



This validates config, tests bot connectivity, and sets up webhooks automatically.

## For WhatsApp:

Configure your webhook URL in Meta Developer Console to point to `{BASE_URL}/chat`.

## Health Check:

Visit [http://localhost:5000/](http://localhost:5000/) to see platform status and available endpoints.

---

The app supports both WhatsApp and Telegram bots using a shared AI service (LLaMA via Groq).