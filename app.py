import os
import tempfile
import sqlite3
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler
from PyPDF2 import PdfReader
from docxtpl import DocxTemplate
import uuid

# ====== Configuration ======
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise RuntimeError("Environment variable BOT_TOKEN is not set")
PORT = int(os.getenv('PORT', 5000))

app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)

def init_db():
    conn = sqlite3.connect('chat_ids.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            token TEXT PRIMARY KEY,
            chat_id INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

dispatcher = Dispatcher(bot, None, use_context=True)

def start(update, context):
    chat_id = update.effective_chat.id
    # 1) создаём простой уникальный токен
    token = uuid.uuid4().hex  # например, '9f3b1c2a...'
    # 2) сохраняем в БД
    conn = sqlite3.connect('chat_ids.db')
    conn.execute(
        'REPLACE INTO users(token TEXT PRIMARY KEY, chat_id INTEGER)',
        (token, chat_id)
    )
    conn.commit(); conn.close()
    # 3) генерируем ссылку на форму, включая token
    form_url = f"https://forms.yandex.ru/u/ВАШ_ID_ФОРМЫ/?token={token}"
    update.message.reply_text(
        f"✅ Привет! Чтобы получить сертификат, пожалуйста, заполните форму по ссылке:\n\n{form_url}")
# Здесь _обязательно_ должна быть эта строка:
dispatcher.add_handler(CommandHandler('start', start))
# Webhook endpoint for Telegram
@app.route('/form_webhook', methods=['POST'])
def form_webhook():
    data = request.json.get('data', {})
    fio = data.get('fio', '').strip()
    token = data.get('token', '').strip()

    print("FORM_WEBHOOK:", "fio=", fio, "token=", token)

    # 1) Проверяем token → получаем chat_id
    conn = sqlite3.connect('chat_ids.db')
    c = conn.cursor()
    c.execute('SELECT chat_id FROM users WHERE token = ?', (token,))
    row = c.fetchone()
    conn.close()
    if not row:
        print("❌ Invalid token:", token)
        return {"status": "error", "message": "Invalid token"}, 400
    chat_id = row[0]
    print("Resolved chat_id:", chat_id)

    # 2) Проверяем ФИО в program.pdf как раньше…
    # 3) Генерируем сертификат и сохраняем в out_docx
    # 4) Отправляем в Telegram:

    try:
        with open(out_docx, 'rb') as doc:
            bot.send_document(chat_id=chat_id, document=doc)
        print("✅ Certificate sent to", chat_id)
    except Exception as e:
        print("❌ Failed to send certificate:", e)

    return {"status": "ok"}
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
