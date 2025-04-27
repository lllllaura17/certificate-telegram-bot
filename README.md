# Certificate Bot Project

This project contains a Telegram bot that automatically issues certificates to conference participants.

## Files

- **app.py**: Main Flask application and Telegram bot logic.
- **program.pdf**: Conference program PDF (place your file here).
- **template.docx**: Word template for certificates (place your template here with {{ fio }} and {{ cert_no }} placeholders).
- **counter.txt**: Stores last issued certificate number (auto-generated).
- **requirements.txt**: Python dependencies.

## Setup

1. Place your `program.pdf` and `template.docx` in the project folder.
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set environment variable:
   ```bash
   export BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
   ```
5. Run the app:
   ```bash
   python app.py
   ```
   or with Gunicorn for production:
   ```bash
   gunicorn app:app --bind 0.0.0.0:${PORT}
   ```

## Deployment

### Render.com

- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT`
- Add environment variable `BOT_TOKEN`

### PythonAnywhere

- Upload files via the web interface.
- Configure a Web App with Flask pointing to `app.py`.
- Set environment variable `BOT_TOKEN`.
- Reload the web app.

## Webhooks

- Telegram: `https://YOUR_DOMAIN/${BOT_TOKEN}`
- Yandex.Form: `https://YOUR_DOMAIN/form_webhook`
