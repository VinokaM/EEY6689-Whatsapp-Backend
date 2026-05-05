# Telegram Bot Integration Setup Guide

This guide will help you set up Telegram bot functionality alongside your existing WhatsApp bot without affecting the WhatsApp implementation.

## Prerequisites

1. **Telegram Bot Token**: Get this from @BotFather on Telegram
2. **HTTPS URL**: Your webhook URL must use HTTPS (ngrok provides this)
3. **Python Dependencies**: Install the updated requirements

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Configure Environment Variables

Update your `.env` file with Telegram configuration:

```env
# Existing WhatsApp configuration (unchanged)
VERIFY_TOKEN=your_whatsapp_verify_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
WHATSAPP_ACCESS_TOKEN=your_whatsapp_token
GROQ_API_KEY=your_groq_api_key
BASE_URL=https://your-ngrok-url.ngrok.io

# New Telegram configuration
TELEGRAM_BOT_TOKEN=bot123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_WEBHOOK_SECRET=your_random_secret_string
```

### Getting Your Telegram Bot Token

1. Open Telegram and search for @BotFather
2. Send `/start` to begin
3. Send `/newbot` to create a new bot (or use existing bot)
4. Follow the prompts to set bot name and username
5. Copy the bot token (format: `bot123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
6. Paste it as `TELEGRAM_BOT_TOKEN` in your `.env` file

### Generating Webhook Secret

Generate a random string for webhook security:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Step 3: Set Up Webhook

### Option A: Using the Setup Script (Recommended)

```bash
python telegram_setup.py
```

This will:
- Validate your configuration
- Test bot connectivity
- Set up the webhook automatically
- Provide detailed feedback

### Option B: Manual Setup

1. **Start your Flask application**:
   ```bash
   python app.py
   ```

2. **Set webhook using curl**:
   ```bash
   curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
        -H "Content-Type: application/json" \
        -d '{"url": "https://your-ngrok-url.ngrok.io/telegram", "secret_token": "your_webhook_secret"}'
   ```

3. **Verify webhook**:
   ```bash
   curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
   ```

## Step 4: Test Your Bot

1. **Start the Flask application**:
   ```bash
   python app.py
   ```

2. **Send a message to your bot on Telegram**

3. **Check the logs** for incoming messages and responses

## API Endpoints

Your Flask application now provides these endpoints:

### WhatsApp Endpoints (Unchanged)
- `GET /chat` - WhatsApp webhook verification
- `POST /chat` - WhatsApp message webhook

### Telegram Endpoints (New)
- `POST /telegram` - Telegram webhook for receiving messages
- `GET /telegram/info` - Get bot information
- `POST /telegram/webhook` - Set webhook URL

### Shared Endpoints
- `GET /` - Health check and status

## Project Structure

```
project/
├── app.py                          # Main Flask app (updated)
├── sendMessage.py                  # WhatsApp service (unchanged)
├── telegram/                       # New Telegram module
│   ├── __init__.py                 # Module initialization
│   ├── telegram_service.py         # Message sending service
│   └── telegram_webhook.py         # Webhook handling
├── llama_ai/
│   └── llama_service.py            # AI service (shared)
├── requirements.txt                # Updated dependencies
├── telegram_setup.py               # Setup and testing script
├── telegram_messages.log           # Telegram operation logs
└── whatsapp_messages.log           # WhatsApp operation logs (unchanged)
```

## Key Features

### Telegram Integration Features
- **Robust Message Handling**: Supports text, photos, documents, voice messages
- **Group Chat Support**: Responds when mentioned or with commands
- **Rate Limiting**: Respects Telegram's 30 messages/second limit
- **Error Handling**: Comprehensive retry logic and error recovery
- **Security**: Webhook signature validation
- **Logging**: Detailed operation logs

### Shared AI Service
- Both WhatsApp and Telegram use the same LLaMA AI service
- Consistent responses across platforms
- Accessibility-focused responses for hearing-impaired users

## Testing Commands

Use the setup script for various testing operations:

```bash
# Run full setup
python telegram_setup.py

# Validate configuration only
python telegram_setup.py validate

# Test bot connection
python telegram_setup.py test

# Set up webhook
python telegram_setup.py webhook

# Get webhook info
python telegram_setup.py info

# Send test message (requires chat ID)
python telegram_setup.py send <chat_id>
```

## Troubleshooting

### Common Issues

1. **"Invalid bot token"**
   - Verify your bot token starts with "bot"
   - Check for extra spaces or characters
   - Ensure the token is from @BotFather

2. **"Webhook setup failed"**
   - Ensure your BASE_URL uses HTTPS
   - Check that your Flask app is running
   - Verify ngrok is forwarding to port 5000

3. **"Bot not responding"**
   - Check Flask application logs
   - Verify webhook is set correctly
   - Ensure bot is not blocked by user

4. **"Rate limiting errors"**
   - The bot automatically handles rate limiting
   - Check logs for rate limit messages
   - Consider reducing message frequency

### Debug Steps

1. **Check configuration**:
   ```bash
   python telegram_setup.py validate
   ```

2. **Test bot connectivity**:
   ```bash
   python telegram_setup.py test
   ```

3. **Check webhook status**:
   ```bash
   python telegram_setup.py info
   ```

4. **Monitor logs**:
   ```bash
   tail -f telegram_messages.log
   ```

## Security Considerations

1. **Webhook Secret**: Always use a webhook secret for production
2. **HTTPS Only**: Telegram requires HTTPS for webhooks
3. **Token Security**: Keep your bot token secure and never commit it to version control
4. **Rate Limiting**: The bot includes built-in rate limiting protection

## Production Deployment

For production deployment:

1. **Use a production WSGI server** (e.g., Gunicorn, uWSGI)
2. **Set up proper logging** with log rotation
3. **Use environment variables** for all sensitive configuration
4. **Implement monitoring** for webhook health
5. **Set up SSL certificates** for your domain

## Support

If you encounter issues:

1. Check the logs in `telegram_messages.log`
2. Use the setup script's diagnostic commands
3. Verify your configuration with `python telegram_setup.py validate`
4. Test bot connectivity with `python telegram_setup.py test`

The WhatsApp functionality remains completely unchanged and will continue to work as before.