import os
import tempfile
import sqlite3
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler
from PyPDF2 import PdfReader
from docxtpl import DocxTemplate

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
            username TEXT PRIMARY KEY,
            chat_id INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

dispatcher = Dispatcher(bot, None, use_context=True)

def start(update, context):
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    if not username:
        return bot.send_message(chat_id=chat_id,
                                text="❗️ Установите username в настройках Telegram.")
    conn = sqlite3.connect('chat_ids.db')
    # … сохраняем chat_id …
    bot.send_message(chat_id=chat_id,
                     text=f"✅ Привет, @{username}! Я буду присылать сертификат.")
# Здесь _обязательно_ должна быть эта строка:
dispatcher.add_handler(CommandHandler('start', start))
# Webhook endpoint for Telegram
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'ok'

def generate_certificate_number():
    counter_file = 'counter.txt'
    if not os.path.exists(counter_file):
        with open(counter_file, 'w') as f:
            f.write('0')
    with open(counter_file, 'r+') as f:
        content = f.read().strip()
        # если файл пустой — считаем, что в нём 0
        prev = int(content) if content.isdigit() else 0
        num = prev + 1      
        f.seek(0)
        f.write(str(num))
        f.truncate()
    return f"ШК-2025 №{num:04d}"

# Helper to get chat_id from username
def get_chat_id(username):
    conn = sqlite3.connect('chat_ids.db')
    c = conn.cursor()
    c.execute('SELECT chat_id FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# Webhook endpoint for form submissions
@app.route('/form_webhook', methods=['POST'])
def form_webhook():
    # 1) Логируем входящий запрос
    print("FORM_WEBHOOK called with data:", request.json)

    data = request.json.get('data', {})
    fio = data.get('fio', '').strip()
    username = data.get('username', '').strip()

    # 2) Загрузка списка участников и проверка ФИО
    with open('program.pdf', 'rb') as f:
        reader = PdfReader(f)
        text = ''
        for page in reader.pages:
            text += page.extract_text() or ''

    # Заменяем простой approved = fio in text на расширенную проверку:
    if fio not in text:
        print("❌ FIO not found in program.pdf:", fio)
        return {"status": "error", "message": "ФИО не найдено в программе"}, 400
    else:
        print("✅ FIO approved:", fio)

    # 3) Генерация сертификата
    tpl = DocxTemplate('template.docx')
    context = {"FIO": fio, "number": generate_certificate_number()}
    tpl.render(context)
    out_docx = tempfile.NamedTemporaryFile(delete=False, suffix='.docx').name
    tpl.save(out_docx)
    print("Certificate generated at", out_docx)

    # Send to user
    chat_id = get_chat_id(username)
    if chat_id:
        with open(out_docx, 'rb') as doc:
            bot.send_document(chat_id=chat_id, document=doc)
    else:
        print(f"User @{username} did not initiate the bot with /start.")

    return {"status": "ok"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
