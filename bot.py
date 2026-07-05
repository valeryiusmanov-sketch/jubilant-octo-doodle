import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

# ===== КОНФИГ =====
TOKEN = "8757926776:AAH7nCAC0B8X3S_iFaBm6A11Ta4fmiHmFpU"
ADMIN_ID = 8205534130
# ==================

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилище мутов: {chat_id: datetime_окончания}
muted_chats = {}
# Хранилище варнов: {chat_id: количество}
warns = {}

@dp.message(F.text & F.chat.type == "private")
async def handle_private_messages(message: Message):
    chat_id = message.chat.id
    text = message.text or ""
    user_id = message.from_user.id

    # === 1. УДАЛЕНИЕ СООБЩЕНИЙ ОТ СОБЕСЕДНИКА ===
    if user_id != bot.id:
        if chat_id in muted_chats and datetime.now() < muted_chats[chat_id]:
            try:
                await bot.delete_message(chat_id, message.message_id)
                warn_msg = await message.answer("🗑️ Удалено (мут активен)")
                await asyncio.sleep(2)
                await warn_msg.delete()
                await bot.send_message(
                    ADMIN_ID,
                    f"🗑️ Удалено от {message.from_user.first_name}: {text[:50]}"
                )
            except Exception as e:
                print(f"Ошибка удаления: {e}")
        return

    # === 2. ОБРАБОТКА КОМАНД ===

    # .mute N
    if text.startswith(".mute "):
        try:
            minutes = int(text.split()[1])
            if minutes < 1 or minutes > 1440:
                await message.answer("❌ От 1 до 1440 минут")
                return
        except:
            await message.answer("❌ Использование: .mute 10")
            return

        muted_chats[chat_id] = datetime.now() + timedelta(minutes=minutes)
        await message.answer(f"✅ Собеседник замучен на {minutes} мин.")
        await bot.send_message(ADMIN_ID, f"🔇 Мут чата {chat_id} на {minutes} мин.")
        asyncio.create_task(auto_unmute(chat_id, minutes))
        return

    # .unmute
    if text == ".unmute":
        if chat_id in muted_chats:
            del muted_chats[chat_id]
            await message.answer("✅ Мут снят")
            await bot.send_message(ADMIN_ID, f"🔊 Мут снят с чата {chat_id}")
        else:
            await message.answer("ℹ️ Мут не активен")
        return

    # .help
    if text == ".help":
        await message.answer(
            "👋 RootExe — управление ЛС\n\n"
            ".mute N — мут на N минут\n"
            ".unmute — снять мут\n"
            ".spam текст N — спам (до 30)\n"
            ".txt текст — анимация\n"
            ".info — данные собеседника\n"
            ".warn N — предупреждение (мут после N)\n"
            ".unwarn — снять варн\n"
            ".help — меню"
        )
        return

    # .info
    if text == ".info":
        chat = await bot.get_chat(chat_id)
        await message.answer(
            f"👤 {chat.first_name or 'Нет имени'}\n"
            f"🆔 {chat.id}\n"
            f"👀 @{chat.username or 'нет'}"
        )
        return

    # .spam текст N
    if text.startswith(".spam "):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer("❌ .spam Привет 5")
            return
        try:
            count = int(parts[2])
            if count > 30:
                count = 30
                await message.answer("⚠️ Ограничено до 30")
        except:
            count = 5
        for _ in range(count):
            await message.answer(parts[1])
            await asyncio.sleep(0.3)
        return

    # .txt текст
    if text.startswith(".txt "):
        t = text.replace(".txt ", "").strip()
        if not t:
            await message.answer("❌ Напиши текст")
            return
        msg = await message.answer("")
        for i in range(len(t)):
            await msg.edit_text(t[:i+1])
            await asyncio.sleep(0.15)
        return

    # .warn N
    if text.startswith(".warn "):
        try:
            limit = int(text.split()[1])
            if limit < 1:
                await message.answer("❌ Лимит > 0")
                return
        except:
            limit = 3

        warns[chat_id] = warns.get(chat_id, 0) + 1
        count = warns[chat_id]
        await message.answer(f"⚠️ Варн {count}/{limit}")

        if count >= limit:
            muted_chats[chat_id] = datetime.now() + timedelta(hours=24)
            await message.answer(f"🚫 Автомут на 24 часа")
            await bot.send_message(ADMIN_ID, f"🚫 Автомут {chat_id} за {limit} варнов")
            asyncio.create_task(auto_unmute(chat_id, 1440))
        return

    # .unwarn
    if text == ".unwarn":
        if chat_id in warns and warns[chat_id] > 0:
            warns[chat_id] -= 1
            await message.answer(f"✅ Варн снят. Осталось: {warns[chat_id]}")
        else:
            await message.answer("ℹ️ Нет варнов")
        return

async def auto_unmute(chat_id: int, minutes: int):
    await asyncio.sleep(minutes * 60)
    if chat_id in muted_chats:
        del muted_chats[chat_id]
        try:
            await bot.send_message(chat_id, "🔓 Мут автоматически снят")
        except:
            pass

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🤖 Бот запущен! Пиши .help в любом ЛС")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
