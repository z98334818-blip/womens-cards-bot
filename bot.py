import asyncio
import sqlite3
import random
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.environ.get("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def init_db():
    conn = sqlite3.connect('gacha.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, 
                  daily_spins INTEGER DEFAULT 2, diamonds INTEGER DEFAULT 2, total_cards INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_cards
                 (user_id INTEGER, card_id INTEGER, quantity INTEGER, PRIMARY KEY (user_id, card_id))''')
    conn.commit()
    conn.close()

CARDS = {
    1: {"name": "Юки", "rarity": "Обычная", "desc": "Скромная девушка из библиотеки"},
    2: {"name": "Мита", "rarity": "Редкая", "desc": "Загадочная создательница миров"},
    3: {"name": "Айко", "rarity": "Эпическая", "desc": "Поп-звезда с секретом"},
    4: {"name": "Сакура", "rarity": "Обычная", "desc": "Цветущая надежда"},
    5: {"name": "Хината", "rarity": "Редкая", "desc": "Солнечная улыбка"},
}

RARITIES = {"Обычная": 0.60, "Редкая": 0.30, "Эпическая": 0.10}

def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Крутить", callback_data="spin")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
    ])

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.first_name
    conn = sqlite3.connect('gacha.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()
    await message.answer("🌟 Добро пожаловать в гача-бот!\n\nИспользуй /profile чтобы посмотреть статистику", reply_markup=main_keyboard())

@dp.message(Command("profile"))
async def profile(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('gacha.db')
    c = conn.cursor()
    c.execute("SELECT username, daily_spins, diamonds, total_cards FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        await message.answer(f"👤 *{user[0]}*\n🎫 Круток: {user[1]}\n💎 Алмазов: {user[2]}\n🎴 Карт собрано: {user[3]}", parse_mode="Markdown", reply_markup=main_keyboard())
    else:
        await message.answer("Используй /start")

@dp.callback_query(F.data == "profile")
async def profile_callback(callback: types.CallbackQuery):
    await profile(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "spin")
async def spin(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = sqlite3.connect('gacha.db')
    c = conn.cursor()
    c.execute("SELECT daily_spins FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    if not result or result[0] <= 0:
        await callback.answer("❌ Нет круток! Ждите 8:00 МСК", show_alert=True)
        conn.close()
        return
    spins = result[0]
    roll = random.random()
    cumulative = 0
    selected_rarity = "Обычная"
    for rarity, chance in RARITIES.items():
        cumulative += chance
        if roll <= cumulative:
            selected_rarity = rarity
            break
    cards = [c for c in CARDS.values() if c["rarity"] == selected_rarity]
    if not cards:
        cards = list(CARDS.values())
    card = random.choice(cards)
    card_id = list(CARDS.keys())[list(CARDS.values()).index(card)]
    c.execute("UPDATE users SET daily_spins = ?, total_cards = total_cards + 1 WHERE user_id=?", (spins - 1, user_id))
    c.execute("INSERT INTO user_cards (user_id, card_id, quantity) VALUES (?, ?, 1) ON CONFLICT(user_id, card_id) DO UPDATE SET quantity = quantity + 1", (user_id, card_id))
    conn.commit()
    conn.close()
    emoji = {"Обычная": "⚪", "Редкая": "🔵", "Эпическая": "🟣"}.get(card["rarity"], "⭐")
    await callback.message.answer(f"{emoji} *{card['name']}* ({card['rarity']})\n📖 {card['desc']}", parse_mode="Markdown")
    await callback.answer()

async def main():
    init_db()
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
