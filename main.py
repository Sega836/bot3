import os
import random
import sqlite3
import logging
import threading
import time
import io
from datetime import datetime, timedelta
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
import matplotlib
matplotlib.use('Agg')  # Важно для работы на сервере без экрана
import matplotlib.pyplot as plt

# --- НАСТРОЙКИ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 6597229121
DB_NAME = "game_bot.db"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# --- БЕЗОПАСНАЯ ОТПРАВКА ---
def safe_send(chat_id, text, reply_markup=None, reply_to=None):
    try:
        if reply_to:
            return bot.send_message(chat_id, text, reply_markup=reply_markup, reply_to_message_id=reply_to)
        return bot.send_message(chat_id, text, reply_markup=reply_markup)
    except ApiTelegramException as e:
        if e.error_code == 429:
            retry_after = e.result_json.get('parameters', {}).get('retry_after', 30)
            logging.warning(f"Флуд-бан! Ждем {retry_after} секунд...")
            time.sleep(retry_after)
            try:
                if reply_to:
                    return bot.send_message(chat_id, text, reply_markup=reply_markup, reply_to_message_id=reply_to)
                return bot.send_message(chat_id, text, reply_markup=reply_markup)
            except Exception as e2:
                logging.error(f"Повторная ошибка: {e2}")
        else:
            logging.error(f"Ошибка API: {e}")
    except Exception as e:
        logging.error(f"Ошибка: {e}")
    return None

# --- БАЗА ДАННЫХ ---
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            gold INTEGER DEFAULT 0, total_earned INTEGER DEFAULT 0, last_daily TEXT, join_date TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS chats (chat_id INTEGER PRIMARY KEY, title TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS accusations (
            msg_id INTEGER PRIMARY KEY, chat_id INTEGER, accuser_id INTEGER,
            target_id INTEGER, text TEXT, votes_yes INTEGER DEFAULT 0, votes_no INTEGER DEFAULT 0
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, action_type TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS clown_of_day (
            chat_id INTEGER PRIMARY KEY, user_id INTEGER, date TEXT
        )""")
        conn.commit()

init_db()

# --- ХЕЛПЕРЫ ---
def get_user(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

def register_user(user_id, username, first_name):
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""INSERT INTO users (user_id, username, first_name, join_date) 
                        VALUES (?, ?, ?, ?) 
                        ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name""",
                     (user_id, username, first_name, today))
        conn.commit()

def add_analytics(action_type):
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT INTO analytics (date, action_type) VALUES (?, ?)", (today, action_type))
        conn.commit()

def is_group(message):
    return message.chat.type in ["group", "supergroup"]

def is_admin(user_id):
    return user_id == ADMIN_ID

# --- СПИСКИ ---
NATIONALITIES = ["Русский 🇷🇺", "Казах 🇰🇿", "Татарин 🏳️", "Чеченец 🏳️", "Украинец 🇺🇦", "Белорус 🇧🇾",
                 "Узбек 🇺🇿", "Армянин 🇦🇲", "Грузин 🇬🇪", "Еврей ✡️", "Китаец 🇨🇳", "Японец 🇯🇵",
                 "Марсианин 👽", "Эльф 🧝", "Гном 🧔", "Пират 🏴‍☠️", "Самурай ⛩️", "Ковбой 🤠", "Викинг ⚔️"]
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
WORDS_OF_DAY = ["Кринж 😬", "Базед 🗿", "Скибиди 🚽", "Вайб ✨", "Ауф 🐺", "Рофл 😂",
                "Шейминг 👎", "Краш 😍", "Слэй 💅", "Чилл 🛋️", "Буллинг 🥊", "Гоуст 👻"]
CLOWN_TEMPLATES = [
    "🤡 <b>Клоун дня</b> в этом чате — {}\n\n📌 Причина: пытался доказать, что земля плоская.",
    "🤡 <b>Клоун дня</b> — {}\n\n📌 Причина: написал бывшей в 3 часа ночи.",
    "🤡 <b>Клоун дня</b> — {}\n\n📌 Причина: зашел в чат и сразу вышел.",
    "🤡 <b>Клоун дня</b> — {}\n\n📌 Причина: поспорил с ботом.",
    "🤡 <b>Клоун дня</b> — {}\n\n📌 Причина: съел шаурму с майонезом в 4 утра."
]

# ============================================================
# ИГРОВЫЕ КОМАНДЫ
# ============================================================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    if not is_group(message):
        return
    register_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT OR IGNORE INTO chats (chat_id, title) VALUES (?, ?)", (message.chat.id, message.chat.title))
        conn.commit()
    add_analytics("start")

    welcome_text = (
        f"┏━━━━━━━━━━━━━━━┓\n"
        f"  👋 <b>Привет, {message.from_user.first_name}!</b>\n"
        f"┗━━━━━━━━━━━━━━━┛\n\n\n"
        f"Я — игровой бот этого чата. Здесь ты можешь фармить голду, обвинять друзей, "
        f"кидаться какашками и узнавать много нового!\n\n\n"
        f"✨ <b>Как играть?</b>\n"
        f"Нажми на синюю кнопку <b>«/»</b> слева от поля ввода, чтобы увидеть список всех команд.\n\n"
        f"👇 <i>Все команды доступны в системном меню Telegram.</i>"
    )
    safe_send(message.chat.id, welcome_text)

@bot.message_handler(commands=["help"])
def cmd_help(message):
    if not is_group(message):
        return
    text = (
        "┏━━━━━━━━━━━━━━━┓\n"
        "  📖 <b>СПРАВОЧНИК КОМАНД</b>\n"
        "┗━━━━━━━━━━━━━━━┛\n\n\n"
        "💰 /golda — получить голду (раз в 1 час)\n\n"
        "🏆 /stats — топ-10 богачей чата\n\n"
        "📊 /gstats — твой отчет по голде\n\n"
        "🌍 /nation — случайная национальность\n\n"
        "💩 /govno (реплай) — кинуть какашку\n\n"
        "📰 /word — слово дня\n\n"
        "⚖️ /obvinit (реплай) — обвинить юзера\n\n"
        "🤡 /kloun — выбрать клоуна дня\n\n\n"
        "💡 <i>Все команды также доступны в меню «/».</i>"
    )
    safe_send(message.chat.id, text)

@bot.message_handler(commands=["golda"])
def cmd_golda(message):
    if not is_group(message):
        return
    user = get_user(message.from_user.id)
    if not user:
        register_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
        user = get_user(message.from_user.id)

    last_daily_str = user[5]
    now = datetime.now()

    if last_daily_str:
        last_daily = datetime.strptime(last_daily_str, "%Y-%m-%d %H:%M:%S")
        passed = now - last_daily
        if passed < timedelta(hours=1):
            remaining = timedelta(hours=1) - passed
            minutes = remaining.seconds // 60
            safe_send(message.chat.id, f"⏳ <b>Кулдаун!</b>\n\nТы уже забирал голду. Приходи через <b>{minutes} мин.</b>", reply_to=message.message_id)
            return

    earned_gold = random.randint(300, 800)
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("UPDATE users SET gold = gold + ?, total_earned = total_earned + ?, last_daily = ? WHERE user_id = ?",
                     (earned_gold, earned_gold, now.strftime("%Y-%m-%d %H:%M:%S"), message.from_user.id))
        conn.commit()
    add_analytics("daily")

    safe_send(message.chat.id,
        f"💸 <b>ГОЛДА ПОЛУЧЕНА!</b>\n\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"Тебе начислено: <b>{earned_gold}</b> 💰\n\n"
        f"Следующий сбор доступен через 1 час.\n\n"
        f"━━━━━━━━━━━━━━━", reply_to=message.message_id)

@bot.message_handler(commands=["gstats"])
def cmd_gstats(message):
    if not is_group(message):
        return
    user = get_user(message.from_user.id)
    if not user:
        safe_send(message.chat.id, "Сначала напиши /start, чтобы зарегистрироваться в игре.", reply_to=message.message_id)
        return

    gold, total_earned = user[3], user[4]
    last_daily_str = user[5]
    next_daily = "✅ Доступно прямо сейчас!"
    if last_daily_str:
        last_daily = datetime.strptime(last_daily_str, "%Y-%m-%d %H:%M:%S")
        next_time = last_daily + timedelta(hours=1)
        if datetime.now() < next_time:
            minutes = (next_time - datetime.now()).seconds // 60
            next_daily = f"⏳ Через {minutes} мин."

    text = (
        f"┏━━━━━━━━━━━━━━━┓\n"
        f"  📊 <b>ОТЧЕТ ПО ГОЛДЕ</b>\n"
        f"┗━━━━━━━━━━━━━━━┛\n\n\n"
        f"👤 Игрок: <b>{message.from_user.first_name}</b>\n\n"
        f"💰 Баланс: <b>{gold}</b> голды\n\n"
        f"💎 Заработано всего: <b>{total_earned}</b> голды\n\n"
        f"🕒 Следующий сбор: <b>{next_daily}</b>"
    )
    safe_send(message.chat.id, text, reply_to=message.message_id)

@bot.message_handler(commands=["nation"])
def cmd_nation(message):
    if not is_group(message):
        return
    nation = random.choice(NATIONALITIES)
    add_analytics("nation")
    safe_send(message.chat.id,
        f"🧬 <b>АНАЛИЗ ДНК ЗАВЕРШЕН</b>\n\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"Твоя национальность: <b>{nation}</b>\n\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"<i>Результат может измениться в следующий раз.</i>", reply_to=message.message_id)

@bot.message_handler(commands=["word"])
def cmd_word(message):
    if not is_group(message):
        return
    word = random.choice(WORDS_OF_DAY)
    safe_send(message.chat.id,
        f"📰 <b>СЛОВО ДНЯ</b>\n\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"👉 {word}\n\n"
        f"━━━━━━━━━━━━━━━", reply_to=message.message_id)

@bot.message_handler(commands=["kloun"])
def cmd_kloun(message):
    if not is_group(message):
        return
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id, date FROM clown_of_day WHERE chat_id = ?", (message.chat.id,))
        res = cur.fetchone()

        if res and res[1] == today:
            cur.execute("SELECT first_name FROM users WHERE user_id = ?", (res[0],))
            user_name = cur.fetchone()[0]
            safe_send(message.chat.id, f"🤡 Сегодняшний <b>Клоун дня</b> уже выбран!\n\nЭто <b>{user_name}</b>. Ждите завтра.", reply_to=message.message_id)
            return

        cur.execute("SELECT user_id, first_name FROM users ORDER BY RANDOM() LIMIT 1")
        clown = cur.fetchone()
        if not clown:
            safe_send(message.chat.id, "В базе пока нет пользователей.", reply_to=message.message_id)
            return

    clown_id, clown_name = clown
    text = random.choice(CLOWN_TEMPLATES).format(f'<a href="tg://user?id={clown_id}">{clown_name}</a>')

    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT OR REPLACE INTO clown_of_day (chat_id, user_id, date) VALUES (?, ?, ?)",
                     (message.chat.id, clown_id, today))
        conn.commit()
    add_analytics("kloun")

    safe_send(message.chat.id,
        f"🎪 <b>ЦИРК ПРИЕХАЛ!</b>\n\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"{text}\n\n"
        f"━━━━━━━━━━━━━━━", reply_to=message.message_id)

@bot.message_handler(commands=["govno"])
def cmd_govno(message):
    if not is_group(message):
        return
    if not message.reply_to_message:
        safe_send(message.chat.id, "🎯 Кинь какашку кому-то! Для этого ответь на сообщение жертвы командой /govno", reply_to=message.message_id)
        return
    target = message.reply_to_message.from_user
    sender = message.from_user
    if target.id == sender.id:
        safe_send(message.chat.id, "🤢 Нельзя кидать какашки в самого себя!", reply_to=message.message_id)
        return
    text = random.choice(POO_TEMPLATES).format(
        f'<a href="tg://user?id={sender.id}">{sender.first_name}</a>',
        f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
    )
    add_analytics("poo")
    safe_send(message.chat.id, f"💩 <b>АТАКА КАКАШКАМИ!</b>\n\n{text}", reply_to=message.message_id)

@bot.message_handler(commands=["stats"])
def cmd_stats(message):
    if not is_group(message):
        return
    with sqlite3.connect(DB_NAME) as conn:
        top_users = conn.execute("SELECT first_name, gold FROM users ORDER BY gold DESC LIMIT 10").fetchall()
    if not top_users:
        safe_send(message.chat.id, "Пока нет статистики.", reply_to=message.message_id)
        return

    text = "🏆 <b>ТОП-10 БОГАЧЕЙ ЧАТА</b>\n\n━━━━━━━━━━━━━━━\n\n<pre>"
    for i, (name, gold) in enumerate(top_users, 1):
        display_name = (name[:12] + '..') if len(name) > 12 else name
        text += f"{i:2}. {display_name:<14} | {gold:>6} 💰\n"
    text += "</pre>\n\n━━━━━━━━━━━━━━━"
    add_analytics("stats")
    safe_send(message.chat.id, text, reply_to=message.message_id)

# ============================================================
# ОБВИНЕНИЯ
# ============================================================

def finish_accusation(chat_id, msg_id):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT text, votes_yes, votes_no, target_id FROM accusations WHERE msg_id = ?", (msg_id,))
        res = cur.fetchone()
        if not res:
            return
        text, yes, no, target_id = res

        result = "🟢 <b>ПРАВДА!</b> Обвиняемый официально признан виновным."
        penalty = yes * 10
        if penalty > 0:
            cur.execute("UPDATE users SET gold = MAX(0, gold - ?) WHERE user_id = ?", (penalty, target_id))

        final_text = (
            f"⚖️ <b>СУД ОКОНЧЕН!</b>\n\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"{text}\n\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"✅ Голосов за обвинение: <b>{yes}</b>\n\n"
            f"❌ Голосов против: <b>{no}</b> <i>(проигнорированы)</i>\n\n\n"
            f"👨‍⚖️ Вердикт: {result}\n\n"
            f"💸 Обвиняемый оштрафован на <b>{penalty}</b> голды!"
        )
        try:
            bot.edit_message_text(final_text, chat_id=chat_id, message_id=msg_id)
        except Exception as e:
            logging.error(f"edit_message error: {e}")
        
        cur.execute("DELETE FROM accusations WHERE msg_id = ?", (msg_id,))
        conn.commit()

@bot.message_handler(commands=["obvinit"])
def cmd_obvinit(message):
    if not is_group(message):
        return
    if not message.reply_to_message:
        safe_send(message.chat.id, "⚖️ Чтобы обвинить кого-то, ответь на его сообщение командой /obvinit", reply_to=message.message_id)
        return
    target = message.reply_to_message.from_user
    accuser = message.from_user
    if target.id == accuser.id:
        safe_send(message.chat.id, "🩺 Шизофрения? Обвинять самого себя это кринж.", reply_to=message.message_id)
        return
    if target.is_bot:
        safe_send(message.chat.id, "🤖 Ботов обвинять нельзя.", reply_to=message.message_id)
        return

    template = random.choice(ACCUSATION_TEMPLATES)
    
    accusation_text = template.format(
        f'<a href="tg://user?id={target.id}">{target.first_name}</a>',
        f'<a href="tg://user?id={accuser.id}">{accuser.first_name}</a>'
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Виновен (0)", callback_data=f"vote_yes_{message.from_user.id}"),
        types.InlineKeyboardButton("❌ Опять невиновен (0)", callback_data=f"vote_no_{message.from_user.id}")
    )

    court_text = (
        f"⚖️ <b>ОБВИНЕНИЕ В СУДЕ!</b>\n\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"{accusation_text}\n\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"🗳️ <i>Голосуйте кнопками ниже! (1 минута)\nОбвинитель всегда побеждает, но каждый голос «Виновен» — это -10 голды для жертвы!</i>"
    )
    msg = safe_send(message.chat.id, court_text, reply_markup=markup, reply_to=message.message_id)

    if msg:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("INSERT INTO accusations (msg_id, chat_id, accuser_id, target_id, text) VALUES (?, ?, ?, ?, ?)",
                         (msg.message_id, message.chat.id, accuser.id, target.id, accusation_text))
            conn.commit()
        add_analytics("accuse")

        timer = threading.Timer(60, finish_accusation, args=[message.chat.id, msg.message_id])
        timer.daemon = True
        timer.start()

@bot.callback_query_handler(func=lambda call: call.data.startswith("vote_"))
def process_vote(call):
    parts = call.data.split("_")
    action, author_id = parts[1], int(parts[2])

    if call.from_user.id == author_id:
        bot.answer_callback_query(call.id, "Обвинитель не может голосовать за себя!", show_alert=True)
        return

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT votes_yes, votes_no FROM accusations WHERE msg_id = ?", (call.message.message_id,))
        res = cur.fetchone()
        if not res:
            bot.answer_callback_query(call.id, "Голосование уже завершено!", show_alert=True)
            return
        yes, no = res
        if action == "yes":
            yes += 1
        else:
            no += 1
        cur.execute("UPDATE accusations SET votes_yes = ?, votes_no = ? WHERE msg_id = ?",
                    (yes, no, call.message.message_id))
        conn.commit()

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(f"✅ Виновен ({yes})", callback_data=f"vote_yes_{author_id}"),
        types.InlineKeyboardButton(f"❌ Опять невиновен ({no})", callback_data=f"vote_no_{author_id}")
    )
    try:
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    except Exception:
        pass
    bot.answer_callback_query(call.id, "Голос учтен!")

# ============================================================
# АДМИН ПАНЕЛЬ (ВЫГРУЗКА ГРУПП В TXT + ГРАФИКИ)
# ============================================================

@bot.message_handler(commands=["admin"], func=lambda m: m.chat.type == "private")
def cmd_admin(message):
    if not is_admin(message.from_user.id):
        safe_send(message.chat.id, "У вас нет доступа.")
        return

    with sqlite3.connect(DB_NAME) as conn:
        chats = conn.execute("SELECT chat_id, title FROM chats").fetchall()
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_actions = conn.execute("SELECT COUNT(*) FROM analytics").fetchone()[0]
        today = datetime.now().strftime("%Y-%m-%d")
        today_actions = conn.execute("SELECT COUNT(*) FROM analytics WHERE date=?", (today,)).fetchone()[0]

    # 1. Отправляем краткую статистику
    stats_text = (
        f"👑 <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>\n\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"👥 Всего пользователей: <b>{total_users}</b>\n"
        f"⚡️ Действий за сегодня: <b>{today_actions}</b>\n"
        f"📊 Действий за всё время: <b>{total_actions}</b>\n"
        f"💬 Всего групп в базе: <b>{len(chats)}</b>\n\n"
        f"📄 <i>Полный список групп отправлен отдельным файлом ниже.</i>"
    )
    safe_send(message.chat.id, stats_text)

    # 2. Генерируем .txt файл со списком групп
    if chats:
        file_content = "СПИСОК ГРУПП, В КОТОРЫХ НАХОДИТСЯ БОТ\n"
        file_content += "=" * 40 + "\n\n"
        for i, (chat_id, title) in enumerate(chats, 1):
            t = title if title else "Без названия"
            file_content += f"{i}. {t}\n   ID: {chat_id}\n\n"
            
        with open("groups_list.txt", "w", encoding="utf-8") as f:
            f.write(file_content)
            
        with open("groups_list.txt", "rb") as f:
            bot.send_document(message.chat.id, f, caption="📄 <b>Список групп (.txt)</b>", parse_mode="HTML")
        os.remove("groups_list.txt")
    else:
        safe_send(message.chat.id, "⚠️ Бот пока не добавлен ни в одну группу.")

    # 3. Отправляем графики с переключателем
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📅 За 7 дней", callback_data="period_7"),
        types.InlineKeyboardButton("🗓 За всё время", callback_data="period_all")
    )
    safe_send(message.chat.id, "👇 <b>Выберите период для графиков:</b>", reply_markup=markup)
    
    # Графики по умолчанию за 7 дней
    send_graphs(message.chat.id, days=7)

@bot.callback_query_handler(func=lambda call: call.data.startswith("period_"))
def process_period(call):
    if not is_admin(call.from_user.id):
        return
    
    # Удаляем старое сообщение с кнопками
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    
    period = call.data.split("_")[1]
    
    # Удаляем прошлые графики (они были отправлены до кнопки)
    # В Telegram нельзя удалить пачку сообщений, поэтому просто отправляем новые
    if period == "7":
        send_graphs(call.message.chat.id, days=7)
    else:
        send_graphs(call.message.chat.id, days=0)
        
    bot.answer_callback_query(call.id, "Графики обновлены!")

def send_graphs(chat_id, days=7):
    with sqlite3.connect(DB_NAME) as conn:
        dates = []
        actions = []
        users = []
        
        if days > 0:
            for i in range(days - 1, -1, -1):
                d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                dates.append((datetime.now() - timedelta(days=i)).strftime("%d.%m"))
                
                act_count = conn.execute("SELECT COUNT(*) FROM analytics WHERE date=?", (d,)).fetchone()[0]
                actions.append(act_count)
                
                usr_count = conn.execute("SELECT COUNT(*) FROM users WHERE join_date=?", (d,)).fetchone()[0]
                users.append(usr_count)
        else:
            rows = conn.execute("SELECT date, COUNT(*) FROM analytics GROUP BY date ORDER BY date").fetchall()
            for d, count in rows:
                dates.append(d[5:])
                actions.append(count)
            
            rows_u = conn.execute("SELECT join_date, COUNT(*) FROM users GROUP BY join_date ORDER BY join_date").fetchall()
            for d, count in rows_u:
                if d[5:] in dates:
                    users[dates.index(d[5:])] = count

    if not dates:
        dates = ["Нет данных"]
        actions = [0]
        users = [0]

    # График 1: Активность
    plt.figure(figsize=(8, 4))
    plt.plot(dates, actions, marker='o', color='#2ecc71', linewidth=2)
    plt.title('Рост обращений к боту', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    buf1 = io.BytesIO()
    plt.savefig(buf1, format='png', dpi=100)
    buf1.seek(0)
    plt.close()
    bot.send_photo(chat_id, buf1, caption="📈 <b>График активности</b>", parse_mode="HTML")

    # График 2: Новые пользователи
    plt.figure(figsize=(8, 4))
    plt.bar(dates, users, color='#3498db')
    plt.title('Количество новых пользователей', fontsize=14)
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    buf2 = io.BytesIO()
    plt.savefig(buf2, format='png', dpi=100)
    buf2.seek(0)
    plt.close()
    bot.send_photo(chat_id, buf2, caption="📊 <b>График прироста</b>", parse_mode="HTML")

# ============================================================
# РАССЫЛКА
# ============================================================

@bot.message_handler(commands=["an"], func=lambda m: m.chat.type == "private")
def cmd_broadcast(message):
    if not is_admin(message.from_user.id): return
    if not message.reply_to_message:
        safe_send(message.chat.id, "Ответьте на сообщение, которое хотите разослать, командой /an")
        return
        
    text_to_send = message.reply_to_message.text or message.reply_to_message.caption
    if not text_to_send:
        safe_send(message.chat.id, "В сообщении нет текста.")
        return
        
    with sqlite3.connect(DB_NAME) as conn:
        chats = conn.execute("SELECT chat_id FROM chats").fetchall()
        
    success, fail = 0, 0
    msg = safe_send(message.chat.id, f"🚀 Начинаю рассылку на {len(chats)} чатов...")
    
    for (chat_id,) in chats:
        try:
            bot.send_message(chat_id, f"📢 <b>СООБЩЕНИЕ ОТ АДМИНА:</b>\n\n{text_to_send}")
            success += 1
            time.sleep(0.05)
        except Exception:
            fail += 1
            
    if msg:
        bot.edit_message_text(f"✅ Рассылка завершена.\nУспешно: {success}\nОшибок: {fail}",
                              chat_id=message.chat.id, message_id=msg.message_id)

# ============================================================
# ЗАПУСК
# ============================================================
if __name__ == "__main__":
    print("Бот запущен!")
    
    try:
        commands = [
            types.BotCommand("golda", "💰 Забрать голду"),
            types.BotCommand("gstats", "📊 Мой профиль"),
            types.BotCommand("stats", "🏆 Топ игроков"),
            types.BotCommand("nation", "🌍 Узнать национальность"),
            types.BotCommand("word", "📰 Слово дня"),
            types.BotCommand("kloun", "🤡 Клоун дня"),
            types.BotCommand("obvinit", "⚖️ Обвинить (реплай)"),
            types.BotCommand("govno", "💩 Кинуть какашку (реплай)")
        ]
        bot.set_my_commands(commands)
        print("Меню команд обновлено!")
    except Exception as e:
        print(f"Ошибка меню: {e}")

    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_send(
            ADMIN_ID,
            f"🚀 <b>БОТ УСПЕШНО ЗАПУЩЕН!</b>\n\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"🕒 Время: <b>{now_str}</b>\n\n"
            f"🟢 Статус: Онлайн\n\n"
            f"⚙️ Версия: 11.0 (TXT Group List)",
        )
    except Exception as e:
        print(f"Ошибка уведомления: {e}")

    bot.infinity_polling(timeout=30, long_polling_timeout=30)
