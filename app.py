from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import time
import sqlite3
import os
import threading

# ТВОЙ ТОКЕН
TOKEN = "8757926776:AAH7nCAC0B8X3S_iFaBm6A11Ta4fmiHmFpU"

app = Flask(__name__)

# ========== БАЗА ДАННЫХ ДЛЯ МУТОВ И ВАРНОВ ==========
db = sqlite3.connect('chat_data.db', check_same_thread=False)
cursor = db.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS chat_states (
    chat_id INTEGER PRIMARY KEY,
    muted_until INTEGER DEFAULT 0,
    warns INTEGER DEFAULT 0,
    is_muted BOOLEAN DEFAULT FALSE
)
''')
db.commit()

# ========== ОБРАБОТЧИКИ КОМАНД ==========
async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда .mute N - мутит собеседника на N минут"""
    if not update.message or not update.message.text:
        return
    
    parts = update.message.text.split()
    if len(parts) != 2:
        await update.message.reply_text("❗ Используй: .mute 5 (мут на 5 минут)")
        return
    
    try:
        minutes = int(parts[1])
        chat_id = update.message.chat_id
        muted_until = int(time.time()) + (minutes * 60)
        
        cursor.execute('INSERT OR REPLACE INTO chat_states (chat_id, muted_until, is_muted) VALUES (?, ?, ?)',
                       (chat_id, muted_until, True))
        db.commit()
        
        await update.message.reply_text(f"🔇 Собеседник замучен на {minutes} минут")
        
        # Отключаем бота для этого чата через Business API
        await context.bot.set_business_chat_pause(chat_id, True)
        
    except ValueError:
        await update.message.reply_text("❗ Введи число минут")

async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Снимает мут"""
    chat_id = update.message.chat_id
    cursor.execute('UPDATE chat_states SET is_muted = FALSE, muted_until = 0 WHERE chat_id = ?', (chat_id,))
    db.commit()
    await context.bot.set_business_chat_pause(chat_id, False)
    await update.message.reply_text("🔊 Мут снят")

async def spam_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет текст N раз (до 50)"""
    parts = update.message.text.split(' ', 2)
    if len(parts) != 3:
        await update.message.reply_text("❗ Используй: .spam текст 10")
        return
    
    text = parts[1]
    try:
        count = min(int(parts[2]), 50)
        for i in range(count):
            await update.message.reply_text(text)
            await asyncio.sleep(0.3)
    except ValueError:
        await update.message.reply_text("❗ Введи число повторений")

async def text_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Анимация текста по буквам (.txt привет)"""
    parts = update.message.text.split(' ', 1)
    if len(parts) != 2:
        await update.message.reply_text("❗ Используй: .txt привет")
        return
    
    text = parts[1]
    msg = await update.message.reply_text("")
    
    # Анимация: редактируем сообщение, добавляя по одной букве
    for i in range(len(text)):
        await msg.edit_text(text[:i+1])
        await asyncio.sleep(0.15)
    
    # В конце показываем полный текст
    await msg.edit_text(text)

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выдаёт предупреждение, после 3-х мут 24ч"""
    chat_id = update.message.chat_id
    
    cursor.execute('SELECT warns FROM chat_states WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    warns = result[0] if result else 0
    warns += 1
    
    if warns >= 3:
        # Мут на 24 часа
        muted_until = int(time.time()) + (24 * 3600)
        cursor.execute('INSERT OR REPLACE INTO chat_states (chat_id, muted_until, is_muted, warns) VALUES (?, ?, ?, ?)',
                       (chat_id, muted_until, True, 0))
        db.commit()
        await context.bot.set_business_chat_pause(chat_id, True)
        await update.message.reply_text("⚠️ 3 предупреждения! Мут на 24 часа")
    else:
        cursor.execute('INSERT OR REPLACE INTO chat_states (chat_id, warns) VALUES (?, ?)', (chat_id, warns))
        db.commit()
        await update.message.reply_text(f"⚠️ Предупреждение {warns}/3")

async def unwarn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Снимает одно предупреждение"""
    chat_id = update.message.chat_id
    cursor.execute('UPDATE chat_states SET warns = 0 WHERE chat_id = ?', (chat_id,))
    db.commit()
    await update.message.reply_text("✅ Предупреждения сброшены")

# ========== ФЛАСК-СЕРВЕР ДЛЯ RENDER (ПРОБУЖДЕНИЕ) ==========
@app.route('/')
def home():
    return "🤖 Бот работает!", 200

@app.route('/ping')
def ping():
    return "OK", 200

# ========== ЗАПУСК БОТА ==========
def run_bot():
    """Запускает бота с polling"""
    application = Application.builder().token(TOKEN).build()
    
    # Регистрация команд
    application.add_handler(CommandHandler("mute", mute_command))
    application.add_handler(CommandHandler("unmute", unmute_command))
    application.add_handler(CommandHandler("spam", spam_command))
    application.add_handler(CommandHandler("txt", text_animation))
    application.add_handler(CommandHandler("warn", warn_command))
    application.add_handler(CommandHandler("unwarn", unwarn_command))
    
    # Запуск polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# ========== ЗАПУСК ВСЕГО ==========
if __name__ == '__main__':
    # Запускаем Flask в потоке
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False), daemon=True).start()
    # Запускаем бота
    run_bot()
