import asyncio
import os
import random
import sqlite3
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, Message, ChatType
from aiogram.enums import ParseMode

# --- НАСТРОЙКИ ---
BOT_TOKEN = os.getenv("BOT_TOKEN") 
ADMIN_ID = 6597229121  # Ваш ID
DB_NAME = "game_bot.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, 
            gold INTEGER DEFAULT 0, total_earned INTEGER DEFAULT 0, last_daily TEXT
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS chats (chat_id INTEGER PRIMARY KEY)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS accusations (
            msg_id INTEGER PRIMARY KEY, chat_id INTEGER, accuser_id INTEGER, 
            target_id INTEGER, text TEXT, end_time TIMESTAMP, votes_yes INTEGER DEFAULT 0, votes_no INTEGER DEFAULT 0
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, action_type TEXT
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS clown_of_day (
            chat_id INTEGER PRIMARY KEY, user_id INTEGER, date TEXT
        )""")
        conn.commit()

init_db()

# --- ХЕЛПЕРЫ ---
def get_user(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()

def register_user(user_id, username, first_name):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", (user_id, username, first_name))
        conn.commit()

def add_analytics(action_type):
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO analytics (date, action_type) VALUES (?, ?)", (today, action_type))
        conn.commit()

# --- СПИСКИ ДЛЯ РАНДОМА ---
NATIONALITIES = ["Русский 🇷🇺", "Казах 🇰🇿", "Татарин 🏳️", "Чеченец 🏳️", "Украинец 🇺🇦", "Белорус 🇧🇾", "Узбек 🇺🇿", "Армянин 🇦🇲", "Грузин 🇬🇪", "Еврей ✡️", "Китаец 🇨🇳", "Японец 🇯🇵", "Марсианин 👽", "Эльф 🧝", "Гном 🧔", "Пират 🏴‍☠️", "Самурай ⛩️", "Ковбой 🤠", "Викинг ⚔️"]
ACCUSATION_TEMPLATES = [
    "{} кушал каки {}", "{} невероятно возбудился от {}", "{} украл трусы {}",
    "{} признался в любви {}", "{} подглядывал за {} в душе", "{} пукнул в сторону {}",
    "{} тайно влюблен в {}", "{} съел последнюю печеньку {}", "{} назвал {} лохом",
    "{} продал душу дьяволу ради внимания {}", "{} вчера ночью плакал из-за {}",
    "{} тайно пишет стихи про {}"
]
POO_TEMPLATES = [
    "{} кинул какашку в {}! Прямое попадание в лицо! 💩",
    "{} запустил снаряд из какашек в {}! 💩🚀",
    "{} незаметно подложил какашку в карман {} 💩",
    "{} обмазал {} с ног до головы какашками! 💩"
]
WORDS_OF_DAY = ["Кринж 😬", "Базед 🗿", "Скибиди 🚽", "Вайб ✨", "Ауф 🐺", "Рофл 😂", "Шейминг 👎", "Краш 😍", "Слэй 💅", "Чилл 🛋️", "Буллинг 🥊", "Гоуст 👻"]
CLOWN_TEMPLATES = [
    "🤡 **Клоун дня** в этом чате — {}\n📌 Причина: пытался доказать, что земля плоская.",
    "🤡 **Клоун дня** — {}\n📌 Причина: написал бывшей в 3 часа ночи.",
    "🤡 **Клоун дня** — {}\n📌 Причина: зашел в чат и сразу вышел.",
    "🤡 **Клоун дня** — {}\n📌 Причина: поспорил с ботом.",
    "🤡 **Клоун дня** — {}\n📌 Причина: съел шаурму с майонезом в 4 утра."
]

# --- ПРОВЕРКИ ---
def is_group(message: Message) -> bool:
    return message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# --- КОМАНДЫ ИГРЫ (ТОЛЬКО ДЛЯ ГРУПП) ---

@dp.message(Command("start"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_start(message: Message):
    register_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT OR IGNORE INTO chats (chat_id) VALUES (?)", (message.chat.id,))
        conn.commit()
    add_analytics("start")
    
    welcome_text = (
        f"┏━━━━━━━━━━━━━━━┓\n"
        f"  👋 **Привет, {message.from_user.first_name}!**\n"
        f"┗━━━━━━━━━━━━━━━┛\n\n"
        f"Я — игровой бот этого чата. Здесь ты можешь фармить голду, обвинять друзей, кидаться какашками и узнавать много нового!\n\n"
        f"✨ **Доступные команды:**\n"
        f"💰 <code>/daily</code> — забрать голду (раз в час!)\n"
        f"🏆 <code>/stats</code> — топ богачей чата\n"
        f"📊 <code>/gstats</code> — твой личный отчет\n"
        f"🌍 <code>/nation</code> — узнать национальность\n"
        f"💩 <code>/poo</code> — кинуть какашку (реплаем)\n"
        f"⚖️ <code>/accuse</code> — обвинить (реплаем)\n"
        f"🤡 <code>/kloun</code> — клоун дня\n"
        f"📰 <code>/word</code> — слово дня\n\n"
        f"👇 *Нажми на команду, чтобы скопировать её.*"
    )
    await message.answer(welcome_text, parse_mode=ParseMode.HTML)

@dp.message(Command("help"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_help(message: Message):
    text = (
        "┏━━━━━━━━━━━━━━━┓\n"
        "  📖 **СПРАВОЧНИК КОМАНД**\n"
        "┗━━━━━━━━━━━━━━━┛\n\n"
        "💰 <code>/daily</code> — получить голду (раз в 1 час)\n"
        "🏆 <code>/stats</code> — топ-10 богачей чата\n"
        "📊 <code>/gstats</code> — твой отчет по голде\n"
        "🌍 <code>/nation</code> — случайная национальность\n"
        "💩 <code>/poo</code> (реплай) — кинуть какашку\n"
        "📰 <code>/word</code> — слово дня\n"
        "⚖️ <code>/accuse</code> (реплай) — обвинить юзера\n"
        "🤡 <code>/kloun</code> — выбрать клоуна дня\n\n"
        "💡 *Совет: нажми на команду, чтобы она скопировалась.*"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("daily"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_daily(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        register_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
        user = get_user(message.from_user.id)
    
    last_daily_str = user[5]
    now = datetime.now()
    
    if last_daily_str:
        last_daily = datetime.strptime(last_daily_str, "%Y-%m-%d %H:%M:%S")
        time_passed = now - last_daily
        if time_passed < timedelta(hours=1):
            remaining = timedelta(hours=1) - time_passed
            minutes = remaining.seconds // 60
            await message.reply(f"⏳ **Кулдаун!**\nТы уже забирал голду. Приходи через **{minutes} мин.**")
            return

    # Рандомное количество голды от 300 до 800
    earned_gold = random.randint(300, 800)
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET gold = gold + ?, total_earned = total_earned + ?, last_daily = ? WHERE user_id = ?", 
                       (earned_gold, earned_gold, now.strftime("%Y-%m-%d %H:%M:%S"), message.from_user.id))
        conn.commit()
    add_analytics("daily")
    
    await message.reply(
        f"💸 **ГОЛДА ПОЛУЧЕНА!**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Тебе начислено: **{earned_gold}** 💰\n"
        f"Следующий сбор доступен через 1 час.\n"
        f"━━━━━━━━━━━━━━━"
    )

@dp.message(Command("gstats"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_gstats(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.reply("Сначала напиши /start, чтобы зарегистрироваться в игре.")
        return
    
    gold, total_earned = user[3], user[4]
    last_daily_str = user[5]
    
    next_daily = "✅ Доступно прямо сейчас!"
    if last_daily_str:
        last_daily = datetime.strptime(last_daily_str, "%Y-%m-%d %H:%M:%S")
        next_time = last_daily + timedelta(hours=1)
        if datetime.now() < next_time:
            remaining = next_time - datetime.now()
            minutes = remaining.seconds // 60
            next_daily = f"⏳ Через {minutes} мин."

    text = (
        f"┏━━━━━━━━━━━━━━━┓\n"
        f"  📊 **ОТЧЕТ ПО ГОЛДЕ**\n"
        f"┗━━━━━━━━━━━━━━━┛\n\n"
        f"👤 Игрок: **{message.from_user.first_name}**\n"
        f"💰 Баланс: **{gold}** голды\n"
        f"💎 Заработано всего: **{total_earned}** голды\n"
        f"🕒 Следующий сбор: **{next_daily}**"
    )
    await message.reply(text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("nation"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_nation(message: Message):
    nation = random.choice(NATIONALITIES)
    add_analytics("nation")
    await message.reply(
        f"🧬 **АНАЛИЗ ДНК ЗАВЕРШЕН**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Твоя национальность: **{nation}**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"*Результат может измениться в следующий раз.*"
    )

@dp.message(Command("word"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_word(message: Message):
    word = random.choice(WORDS_OF_DAY)
    await message.reply(
        f"📰 **СЛОВО ДНЯ**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👉 {word}\n"
        f"━━━━━━━━━━━━━━━"
    )

@dp.message(Command("kloun"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_kloun(message: Message):
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, date FROM clown_of_day WHERE chat_id = ?", (message.chat.id,))
        res = cursor.fetchone()
        
        if res and res[1] == today:
            cursor.execute("SELECT first_name FROM users WHERE user_id = ?", (res[0],))
            user_name = cursor.fetchone()[0]
            await message.reply(f"🤡 Сегодняшний **Клоун дня** уже выбран!\nЭто **{user_name}**. Ждите завтра.")
            return

        cursor.execute("SELECT user_id, first_name FROM users ORDER BY RANDOM() LIMIT 1")
        clown = cursor.fetchone()
        
        if not clown:
            await message.reply("В базе пока нет пользователей.")
            return

    clown_id, clown_name = clown
    template = random.choice(CLOWN_TEMPLATES)
    text = template.format(f"[{clown_name}](tg://user?id={clown_id})")
    
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT OR REPLACE INTO clown_of_day (chat_id, user_id, date) VALUES (?, ?, ?)", (message.chat.id, clown_id, today))
        conn.commit()
    add_analytics("kloun")
    
    await message.reply(
        f"🎪 **ЦИРК ПРИЕХАЛ!**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{text}\n"
        f"━━━━━━━━━━━━━━━"
    , parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("poo"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_poo(message: Message):
    if not message.reply_to_message:
        await message.reply("🎯 Кинь какашку кому-то! Для этого ответь на сообщение жертвы командой /poo")
        return
    target = message.reply_to_message.from_user
    sender = message.from_user
    if target.id == sender.id:
        await message.reply("🤢 Нельзя кидать какашки в самого себя!")
        return
    text = random.choice(POO_TEMPLATES).format(f"[{sender.first_name}](tg://user?id={sender.id})", f"[{target.first_name}](tg://user?id={target.id})")
    add_analytics("poo")
    await message.reply(f"💩 **АТАКА КАКАШКАМИ!**\n\n{text}", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("stats"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_stats(message: Message):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT first_name, gold FROM users ORDER BY gold DESC LIMIT 10")
        top_users = cursor.fetchall()
    if not top_users:
        await message.reply("Пока нет статистики.")
        return
    
    text = "🏆 **ТОП-10 БОГАЧЕЙ ЧАТА**\n━━━━━━━━━━━━━━━\n<pre>"
    for i, (name, gold) in enumerate(top_users, 1):
        # Обрезаем имя, если оно слишком длинное, чтобы таблица не ломалась
        display_name = (name[:12] + '..') if len(name) > 12 else name
        text += f"{i:2}. {display_name:<14} | {gold:>6} 💰\n"
    text += "</pre>━━━━━━━━━━━━━━━"
    
    add_analytics("stats")
    await message.answer(text, parse_mode=ParseMode.HTML)

# --- МЕХАНИКА ОБВИНЕНИЙ ---

@dp.message(Command("accuse"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_accuse(message: Message):
    if not message.reply_to_message:
        await message.reply("⚖️ Чтобы обвинить кого-то, ответь на его сообщение командой /accuse")
        return
    target = message.reply_to_message.from_user
    accuser = message.from_user
    if target.id == accuser.id:
        await message.reply("🩺 Шизофрения? Обвинять самого себя это кринж.")
        return
    if target.is_bot:
        await message.reply("🤖 Ботов обвинять нельзя.")
        return

    template = random.choice(ACCUSATION_TEMPLATES)
    accusation_text = template.format(f"[{accuser.first_name}](tg://user?id={accuser.id})", f"[{target.first_name}](tg://user?id={target.id})")
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Правда (0)", callback_data=f"vote_yes_{message.from_user.id}"),
        InlineKeyboardButton(text="❌ Ложь (0)", callback_data=f"vote_no_{message.from_user.id}")
    )
    end_time = datetime.now() + timedelta(minutes=1)
    
    court_text = (
        f"⚖️ **ОБВИНЕНИЕ В СУДЕ!**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{accusation_text}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🗳️ *Голосуйте кнопками ниже! (1 минута)*"
    )
    
    msg = await message.reply(court_text, reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN)
    
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT INTO accusations (msg_id, chat_id, accuser_id, target_id, text, end_time) VALUES (?, ?, ?, ?, ?, ?)",
                     (msg.message_id, message.chat.id, accuser.id, target.id, accusation_text, end_time))
        conn.commit()
    add_analytics("accuse")
    asyncio.create_task(finish_accusation(message.chat.id, msg.message_id, 60))

async def finish_accusation(chat_id, msg_id, delay):
    await asyncio.sleep(delay)
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT text, votes_yes, votes_no FROM accusations WHERE msg_id = ?", (msg_id,))
        res = cursor.fetchone()
        if res:
            text, yes, no = res
            if yes > no:
                result = "🟢 **ПРАВДА!** Обвиняемый признан виновным."
            elif no > yes:
                result = "🔴 **НЕПРАВДА!** Это была грязная клевета."
            else:
                result = "🟡 **НИЧЬЯ!** Голоса разделились."
                
            final_text = (
                f"⚖️ **СУД ОКОНЧЕН!**\n"
                f"━━━━━━━━━━━━━━━\n"
                f"{text}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"✅ Правда: **{yes}**\n"
                f"❌ Ложь: **{no}**\n\n"
                f"👨‍⚖️ Вердикт: {result}"
            )
            try:
                await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=final_text, parse_mode=ParseMode.MARKDOWN)
            except: pass
            conn.execute("DELETE FROM accusations WHERE msg_id = ?", (msg_id,))
            conn.commit()

@dp.callback_query(F.data.startswith("vote_"))
async def process_vote(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    action, user_id = parts[1], parts[2]
    if callback.from_user.id == int(user_id):
        await callback.answer("Нельзя голосовать за себя!", show_alert=True)
        return
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT votes_yes, votes_no FROM accusations WHERE msg_id = ?", (callback.message.message_id,))
        res = cursor.fetchone()
        if not res:
            await callback.answer("Голосование уже завершено!", show_alert=True)
            return
        yes, no = res
        if action == "yes": yes += 1
        else: no += 1
        cursor.execute("UPDATE accusations SET votes_yes = ?, votes_no = ? WHERE msg_id = ?", (yes, no, callback.message.message_id))
        conn.commit()
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=f"✅ Правда ({yes})", callback_data=f"vote_yes_{user_id}"),
        InlineKeyboardButton(text=f"❌ Ложь ({no})", callback_data=f"vote_no_{user_id}")
    )
    try: await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    except: pass
    await callback.answer("Голос учтен!")

# --- АДМИН ПАНЕЛЬ (ТОЛЬКО В ЛС) ---

@dp.message(Command("admin"), F.chat.type == ChatType.PRIVATE)
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к этой команде.")
        return
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Статистика (Текст)", callback_data="admin_stats"))
    builder.row(InlineKeyboardButton(text="📈 График прироста", callback_data="admin_graph"))
    
    text = (
        "┏━━━━━━━━━━━━━━━┓\n"
        "  👑 **АДМИН-ПАНЕЛЬ**\n"
        "┗━━━━━━━━━━━━━━━┛\n\n"
        "Выберите действие:"
    )
    await message.answer(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chats")
        total_chats = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM analytics WHERE action_type='daily'")
        total_daily = cursor.fetchone()[0]
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM analytics WHERE date=?", (today,))
        today_actions = cursor.fetchone()[0]
        
    text = (
        f"📊 **ОБЩАЯ СТАТИСТИКА БОТА**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👥 Пользователей: **{total_users}**\n"
        f"💬 Чатов: **{total_chats}**\n"
        f"💰 Выдано дейликов: **{total_daily}**\n"
        f"⚡️ Действий за сегодня: **{today_actions}**"
    )
    await callback.message.answer(text, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query(F.data == "admin_graph")
async def admin_graph(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT date, COUNT(*) FROM analytics GROUP BY date ORDER BY date DESC LIMIT 7")
        data = cursor.fetchall()[::-1]
    if not data:
        await callback.message.answer("Пока нет данных для графика.")
        return
    
    text = "📈 **ГРАФИК АКТИВНОСТИ**\n━━━━━━━━━━━━━━━\n<pre>"
    max_val = max([row[1] for row in data]) if data else 1
    for date, count in data:
        bar = "█" * int((count / max_val) * 10)
        text += f"{date} | {bar} ({count})\n"
    text += "</pre>"
    
    await callback.message.answer(text, parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.message(Command("rass"), F.chat.type == ChatType.PRIVATE)
async def cmd_rass(message: Message):
    if not is_admin(message.from_user.id): return
    if not message.reply_to_message:
        await message.reply("Ответьте на сообщение, которое хотите разослать, командой /rass")
        return
    broadcast_text = message.reply_to_message.text or message.reply_to_message.caption
    if not broadcast_text:
        await message.reply("В сообщении нет текста.")
        return
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM chats")
        chats = cursor.fetchall()
    success = 0
    fail = 0
    msg = await message.reply(f"🚀 Начинаю рассылку на {len(chats)} чатов...")
    for (chat_id,) in chats:
        try:
            await bot.send_message(chat_id, f"📢 **РАССЫЛКА ОТ АДМИНА:**\n\n{broadcast_text}", parse_mode=ParseMode.MARKDOWN)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail += 1
    await msg.edit_text(f"✅ Рассылка завершена.\nУспешно: {success}\nОшибок: {fail}")

# --- ЗАПУСК И УВЕДОМЛЕНИЕ ---
async def main():
    print("Бот запущен!")
    # Отправка уведомления админу при старте
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await bot.send_message(
            ADMIN_ID, 
            f"🚀 **БОТ УСПЕШНО ЗАПУЩЕН!**\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🕒 Время: `{now_str}`\n"
            f"🟢 Статус: Онлайн\n"
            f"⚙️ Версия: 2.0 (Красивая)",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"Не удалось отправить уведомление админу: {e}")
        
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
