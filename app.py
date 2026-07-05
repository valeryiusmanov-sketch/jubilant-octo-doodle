from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import sqlite3
import time
import threading
import asyncio
import sys

TOKEN = "8757926776:AAH7nCAC0B8X3S_iFaBm6A11Ta4fmiHmFpU"
app = Flask(__name__)

db = sqlite3.connect('mute_data.db', check_same_thread=False)
cursor = db.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS muted_chats (chat_id INTEGER PRIMARY KEY, muted_until INTEGER, warn_count INTEGER DEFAULT 0)')
db.commit()

async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.from_user.is_bot:
        return
    
    chat_id = update.message.chat_id
    text = update.message.text or ""
    
    if text.startswith('.'):
        await update.message.delete()
        
        if text.startswith('.mute '):
            try:
                minutes = int(text.split()[1])
                cursor.execute('INSERT OR REPLACE INTO muted_chats (chat_id, muted_until) VALUES (?, ?)',
                               (chat_id, int(time.time()) + minutes * 60))
                db.commit()
                msg = await update.message.reply_text(f"🔇 {minutes} мин")
                await asyncio.sleep(2)
                await msg.delete()
            except:
                pass
            
        elif text == '.unmute':
            cursor.execute('DELETE FROM muted_chats WHERE chat_id = ?', (chat_id,))
            db.commit()
            msg = await update.message.reply_text("🔊 Ок")
            await asyncio.sleep(2)
            await msg.delete()
            
        elif text.startswith('.spam '):
            parts = text.split(' ', 2)
            if len(parts) == 3:
                try:
                    count = min(int(parts[2]), 50)
                    for _ in range(count):
                        await update.message.reply_text(parts[1])
                        await asyncio.sleep(0.2)
                except:
                    pass
                    
        elif text.startswith('.txt '):
            t = text[5:]
            if t:
                msg = await update.message.reply_text("")
                for i in range(len(t)):
                    await msg.edit_text(t[:i+1])
                    await asyncio.sleep(0.15)
                    
        elif text == '.warn':
            cursor.execute('SELECT warn_count FROM muted_chats WHERE chat_id = ?', (chat_id,))
            result = cursor.fetchone()
            warns = (result[0] if result else 0) + 1
            if warns >= 3:
                cursor.execute('INSERT OR REPLACE INTO muted_chats (chat_id, muted_until, warn_count) VALUES (?, ?, ?)',
                               (chat_id, int(time.time()) + 86400, 0))
                db.commit()
                msg = await update.message.reply_text("⚠️ Мут 24ч")
            else:
                cursor.execute('INSERT OR REPLACE INTO muted_chats (chat_id, warn_count) VALUES (?, ?)', (chat_id, warns))
                db.commit()
                msg = await update.message.reply_text(f"⚠️ {warns}/3")
            await asyncio.sleep(3)
            await msg.delete()
            
        elif text == '.unwarn':
            cursor.execute('UPDATE muted_chats SET warn_count = 0 WHERE chat_id = ?', (chat_id,))
            db.commit()
            msg = await update.message.reply_text("✅ Сброс")
            await asyncio.sleep(2)
            await msg.delete()
        return
    
    cursor.execute('SELECT muted_until FROM muted_chats WHERE chat_id = ?', (chat_id,))
    r = cursor.fetchone()
    if r and int(time.time()) < r[0]:
        try:
            await update.message.delete()
        except:
            pass

@app.route('/')
def home():
    return "OK", 200

def run_bot():
    # СОЗДАЁМ EVENT LOOP ВРУЧНУЮ (ФИКС ДЛЯ PYTHON 3.14+)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL, handle_all))
    application.run_polling()

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080, debug=False), daemon=True).start()
    run_bot()
