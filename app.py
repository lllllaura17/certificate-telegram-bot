import os
import tempfile
import sqlite3
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler
from PyPDF2 import PdfReader
from docxtpl import DocxTemplate

# ====== Configuration ======
# Set environment variables before running:
# BOT_TOKEN: your Telegram Bot token
# PORT: (optional) port to listen on, defaults to 5000

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
        CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY,
            chat_id INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def load_program():
    reader = PdfReader('program.pdf')
    program = set()
    for page in reader.pages:
        text = page.extract_text() or ''
        for line in text.split('\n'):
            clean = line.strip()
            if clean:
                program.add(clean)
    return program

PROGRAM = load_program()

def get_chat_id(username: str):
    conn = sqlite3.connect('chat_ids.db')
    c = conn.cursor()
    c.execute('SELECT chat_id FROM users WHERE username=?', (username,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_next_cert_no():
    counter_file = 'counter.txt'
    num = 1
    if os.path.exists(counter_file):
        with open(counter_file) as f:
            num = int(f.read().strip()) + 1
    with open(counter_file, 'w') as f:
        f.write(str(num))
    return f"ШК-2025 №{num:04d}"

# Telegram setup
dispatcher = Dispatcher(bot, None, use_context=True)

def start(update, context):
    user = update.effective_user
    chat_id = update.effective_chat.id
    username = user.username
    if not username:
        update.message.reply_text("Please set a Telegram username in your settings.")
        return
    conn = sqlite3.connect('chat_ids.db')
    c = conn.cursor()
    c.execute('REPLACE INTO users(username, chat_id) VALUES (?, ?)', (username, chat_id))
    conn.commit()
    conn.close()
    update.message.reply_text(f"Hello, @{username}! You'll receive your certificate when it's ready.")

dispatcher.add_handler(CommandHandler('start', start))

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'ok'

@app.route('/form_webhook', methods=['POST'])
def form_webhook():
    data = request.json.get('data', {})
    fio = data.get('fio', '').strip()
    username = data.get('username', '').strip()

    if fio not in PROGRAM:
        return {"status": "error", "message": "ФИО не найдено в программе"}, 400

    tpl = DocxTemplate('template.docx')
    cert_no = get_next_cert_no()
    tpl.render({'fio': fio, 'cert_no': cert_no})
    out_docx = tempfile.NamedTemporaryFile(delete=False, suffix='.docx').name
    tpl.save(out_docx)

    chat_id = get_chat_id(username)
    if chat_id:
        with open(out_docx, 'rb') as f:
            bot.send_document(chat_id=chat_id, document=f)
    else:
        print(f"User @{username} did not initiate the bot with /start.")

    return {"status": "ok"}

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=PORT)
