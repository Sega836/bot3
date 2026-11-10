# bot.py
# Запуск: BOT_TOKEN=xxx python bot.py
# Зависимости: pip install pyTelegramBotAPI
# Опционально: pip install matplotlib  (для графиков; без него — ASCII-график)

import os
import io
import time
import random
import sqlite3
import threading
from datetime import datetime, date
from contextlib import contextmanager

import telebot
from telebot import types

# ============================================================
#  КОНФИГ
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = 6597229121
BOT_USERNAME = "Shutki_za_200_bot"
GROUP_URL = f"https://t.me/{BOT_USERNAME}?startgroup=true"

GAME_DB = "game.db"
ANALYTICS_DB = "analytics.db"

GOLDA_COOLDOWN = 3600
KAZIK_TIMEOUT = 120
COURT_DURATION = 60

# Пробуем импортировать matplotlib один раз при старте
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from collections import Counter as _Counter
    HAS_MPL = True
except Exception:
    HAS_MPL = False

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ============================================================
#  ДАННЫЕ
# ============================================================
NATIONALITIES = [
    "Русский", "Украинец", "Белорус", "Казах", "Татарин",
    "Чеченец", "Узбек", "Армянин", "Грузин", "Азербайджанец",
    "Киргиз", "Таджик", "Молдаванин", "Литвин", "Латыш",
    "Эстонец", "Финн", "Швед", "Норвежец", "Датчанин",
    "Немец", "Француз", "Итальянец", "Испанец", "Португалец",
    "Британец", "Ирландец", "Шотландец", "Поляк", "Чех",
    "Словак", "Венгр", "Румын", "Болгарин", "Серб",
    "Хорват", "Грек", "Турок", "Израильтянин", "Египтянин",
    "Американец", "Канадец", "Мексиканец", "Бразилец", "Аргентинец",
    "Кубинец", "Китаец", "Японец", "Кореец", "Индиец",
    "Тайец", "Вьетнамец", "Австралиец", "Новозеландец", "Марсианин 👽",
    "Эльф 🧝", "Гном 🧔", "Пират 🏴‍☠️", "Самурай ⛩️", "Ковбой 🤠",
    "Гоблин 👺",
]

WORDS_OF_DAY = [
    "Кринж 😬", "Базед 🗿", "Скибиди 🚽", "Вайб ✨", "Ауф 🐺",
    "Рофл 😂", "Шейминг 👎", "Краш 😍", "Слэй 💅", "Чилл 🛋️",
    "Буллинг 🥊", "Гоуст 👻", "Сигма 🗿", "Альфа 🐺", "Бета 🐑",
    "Омега 🐜", "Кек 🍞", "Лол 🤣", "Ору 🗣️", "Топчик 🔥",
    "Зашквар 🚫", "Кринж-мастер 😬", "Мемас 🐸", "Вайб-чек ✨",
    "Скибиди-туалет 🚽", "Сас 🕵️", "Амогус 📮", "Сас-сигма 🗿",
    "Шипперить 💘", "Краш-культура 💔", "Слэй-квин 👑", "Герл-босс 💼",
    "Флекс 💪", "Йоу-йоу 🎤", "Бро 🫂", "Систер 👯",
    "Дота-бояр 🎮", "Майнкрафтер ⛏️", "Тиктокер 📱", "Стример 🎥",
    "Геймер 🕹️", "Нуб 🐣", "Про 🏆", "Керри ⚔️", "Саппорт 🛡️",
    "Мид 🏹", "Оффлейн 🪓", "Хардлейн 🧱", "Фид 😢", "Рампейдж 🔥",
    "Кринж-стрим 📺", "Летсплей 🎬", "Спидран ⏱️",
    "Тильт 😤", "Бомбит 💣", "Агрессивный чилл 😤🛋️", "Депресняк 😢",
    "Эйфория 🤩", "Меланхолия 🌧️", "Нирвана 🧘", "Дзен 🧘‍♂️",
    "Паника 😱", "Ступор 🥶", "Апатия 😑", "Хайп 🔥",
    "Бумер 👴", "Зумер 🧢", "Миллениал 💼", "Альфа-поколение 👶",
    "Бумер-стайл 👴🕶️", "Зумер-сленг 🧢🗣️", "Тикток-челлендж 📱",
    "Кринжово 😬", "Скибиди-доп-доп 🚽🎵", "Сигма-мейл 🗿♂️",
    "Ауф-ауф 🐺🐺", "Вайб-чек ✨✅", "Рофл-мастер 😂🏆",
    "Кек-лол 🍞🤣", "Топ-топ 🔥🔥", "Зашквар-шоу 🚫📺",
    "Мем-лорд 🐸👑", "Кринж-фест 😬🎪", "Вайб-кризис ✨😰",
]

CLOWN_REASONS = [
    "пытался доказать, что Скибиди-туалет — это высшая форма искусства",
    "скинул в чат видео с какашкой и назвал его 'мемом года'",
    "написал 'я сигма', но испугался Скибиди-туалета в зеркале",
    "съел шаурму с майонезом в 4 утра и назвал это 'завтраком'",
    "попытался смыть Скибиди-туалет, но он оказался сильнее",
    "прислал голосовое со звуком смыва на 3 минуты",
    "сказал, что какашки — это новый тренд, и обиделся, когда все засмеялись",
    "нарисовал Скибиди-туалет на уроке и получил двойку",
    "назвал свой ник 'Какашка_В_Туалете' и удивился реакции",
    "поспорил с ботом, что Скибиди-туалет существует, и проиграл",
    "скинул стикер с какашкой 20 раз подряд",
    "сказал 'я не Скибиди-туалет', но все уже поняли",
    "попытался флиртовать с Скибиди-туалетом в чате",
    "написал 'я умный', а потом спросил, что такое 'какашка'",
    "поздравил Скибиди-туалет с днём рождения",
]

ACCUSATION_TEMPLATES = [
    "{} кушал каки {}", "{} невероятно возбудился от {}", "{} украл трусы {}",
    "{} признался в любви {}", "{} подглядывал за {} в душе",
    "{} пукнул в сторону {}", "{} тайно влюблён в {}",
    "{} съел последнюю печеньку {}", "{} назвал {} лохом",
]

GOVNO_TEMPLATES = [
    "💩 {a} кинул какашку в {b}! Прямое попадание в лицо! 💩",
    "💩🚀 {a} запустил снаряд из какашек в {b}!",
    "💩 {a} незаметно подложил какашку в карман {b} 💩",
    "💩 {a} обмазал {b} с ног до головы какашками!",
]

# ============================================================
#  БАЗЫ ДАННЫХ
# ============================================================
def init_dbs():
    with sqlite3.connect(GAME_DB) as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
            username TEXT, first_name TEXT, gold INTEGER DEFAULT 0,
            last_gold INTEGER DEFAULT 0, last_pet INTEGER DEFAULT 0,
            pet_id INTEGER, pet_name TEXT, marry_id INTEGER,
            PRIMARY KEY (chat_id, user_id));
        CREATE TABLE IF NOT EXISTS clowns (
            chat_id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT,
            reason TEXT, day TEXT);
        CREATE TABLE IF NOT EXISTS court_votes (
            court_id TEXT, user_id INTEGER, vote TEXT,
            PRIMARY KEY (court_id, user_id));
        CREATE TABLE IF NOT EXISTS kazik_state (
            chat_id INTEGER, user_id INTEGER, step INTEGER,
            bet_what TEXT, bet_on TEXT, updated INTEGER,
            PRIMARY KEY (chat_id, user_id));
        """)
    with sqlite3.connect(ANALYTICS_DB) as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY, title TEXT,
            added_at INTEGER, last_seen INTEGER);
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER, user_id INTEGER,
            event TEXT, ts INTEGER);
        CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
        CREATE INDEX IF NOT EXISTS idx_events_chat ON events(chat_id);
        """)

@contextmanager
def gdb():
    con = sqlite3.connect(GAME_DB); con.row_factory = sqlite3.Row
    try:
        yield con; con.commit()
    finally:
        con.close()

@contextmanager
def adb():
    con = sqlite3.connect(ANALYTICS_DB); con.row_factory = sqlite3.Row
    try:
        yield con; con.commit()
    finally:
        con.close()

# ---------- analytics ----------
def track_group(chat_id, title):
    now = int(time.time())
    with adb() as con:
        con.execute("""INSERT INTO groups (chat_id, title, added_at, last_seen)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(chat_id) DO UPDATE SET
                         title=excluded.title, last_seen=excluded.last_seen""",
                    (chat_id, title, now, now))

def track_event(chat_id, user_id, event):
    with adb() as con:
        con.execute("INSERT INTO events (chat_id, user_id, event, ts) VALUES (?, ?, ?, ?)",
                    (chat_id, user_id, event, int(time.time())))

# ---------- players ----------
def ensure_player(chat_id, user_id, username, first_name):
    with gdb() as con:
        con.execute("""INSERT INTO players (chat_id, user_id, username, first_name)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(chat_id, user_id) DO UPDATE SET
                         username=excluded.username, first_name=excluded.first_name""",
                    (chat_id, user_id, username, first_name))

def get_player(chat_id, user_id):
    with gdb() as con:
        return con.execute("SELECT * FROM players WHERE chat_id=? AND user_id=?",
                           (chat_id, user_id)).fetchone()

def add_gold(chat_id, user_id, amount):
    with gdb() as con:
        con.execute("UPDATE players SET gold=gold+? WHERE chat_id=? AND user_id=?",
                    (amount, chat_id, user_id))

def set_last_gold(chat_id, user_id, ts):
    with gdb() as con:
        con.execute("UPDATE players SET last_gold=? WHERE chat_id=? AND user_id=?",
                    (ts, chat_id, user_id))

def take_gold(chat_id, user_id, amount):
    with gdb() as con:
        row = con.execute("SELECT gold FROM players WHERE chat_id=? AND user_id=?",
                          (chat_id, user_id)).fetchone()
        if not row: return 0
        taken = min(row["gold"], amount)
        con.execute("UPDATE players SET gold=gold-? WHERE chat_id=? AND user_id=?",
                    (taken, chat_id, user_id))
        return taken

def top_players(chat_id, limit=10):
    with gdb() as con:
        return con.execute("SELECT first_name, gold FROM players WHERE chat_id=? AND gold>0 "
                           "ORDER BY gold DESC LIMIT ?", (chat_id, limit)).fetchall()

def chat_players(chat_id):
    with gdb() as con:
        return con.execute("SELECT user_id, first_name FROM players WHERE chat_id=?",
                           (chat_id,)).fetchall()

# ---------- clown ----------
def get_clown(chat_id):
    with gdb() as con:
        return con.execute("SELECT * FROM clowns WHERE chat_id=?", (chat_id,)).fetchone()

def set_clown(chat_id, user_id, name, reason, day):
    with gdb() as con:
        con.execute("""INSERT INTO clowns (chat_id, user_id, name, reason, day)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(chat_id) DO UPDATE SET
                         user_id=excluded.user_id, name=excluded.name,
                         reason=excluded.reason, day=excluded.day""",
                    (chat_id, user_id, name, reason, day))

# ---------- pet/marry ----------
def set_pet(chat_id, user_id, pet_id, pet_name, ts):
    with gdb() as con:
        con.execute("UPDATE players SET pet_id=?, pet_name=?, last_pet=? "
                    "WHERE chat_id=? AND user_id=?",
                    (pet_id, pet_name, ts, chat_id, user_id))

def marry(chat_id, user_id, partner_id):
    with gdb() as con:
        con.execute("UPDATE players SET marry_id=? WHERE chat_id=? AND user_id=?",
                    (partner_id, chat_id, user_id))
        con.execute("UPDATE players SET marry_id=? WHERE chat_id=? AND user_id=?",
                    (user_id, chat_id, partner_id))

# ---------- court ----------
def court_vote(court_id, user_id, vote):
    with gdb() as con:
        con.execute("""INSERT INTO court_votes (court_id, user_id, vote) VALUES (?, ?, ?)
                       ON CONFLICT(court_id, user_id) DO UPDATE SET vote=excluded.vote""",
                    (court_id, user_id, vote))

def court_tally(court_id):
    with gdb() as con:
        rows = con.execute("SELECT vote, COUNT(*) c FROM court_votes WHERE court_id=? "
                           "GROUP BY vote", (court_id,)).fetchall()
        return {r["vote"]: r["c"] for r in rows}

def clear_court(court_id):
    with gdb() as con:
        con.execute("DELETE FROM court_votes WHERE court_id=?", (court_id,))

# ---------- kazik ----------
def kazik_set(chat_id, user_id, step, what=None, on=None):
    with gdb() as con:
        con.execute("""INSERT INTO kazik_state (chat_id, user_id, step, bet_what, bet_on, updated)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT(chat_id, user_id) DO UPDATE SET
                         step=excluded.step, bet_what=excluded.bet_what,
                         bet_on=excluded.bet_on, updated=excluded.updated""",
                    (chat_id, user_id, step, what, on, int(time.time())))

def kazik_get(chat_id, user_id):
    with gdb() as con:
        return con.execute("SELECT * FROM kazik_state WHERE chat_id=? AND user_id=?",
                           (chat_id, user_id)).fetchone()

def kazik_clear(chat_id, user_id):
    with gdb() as con:
        con.execute("DELETE FROM kazik_state WHERE chat_id=? AND user_id=?",
                    (chat_id, user_id))

# ============================================================
#  УТИЛИТЫ
# ============================================================
def mention(user_id, first_name):
    return f'<a href="tg://user?id={user_id}">{first_name}</a>'

def is_group(message):
    return message.chat.type in ("group", "supergroup")

def is_private(message):
    return message.chat.type == "private"

def humanize_minutes(sec):
    return max(1, int(sec // 60))

def today_str():
    return date.today().isoformat()

def ascii_bar_chart(xs, ys, width=30):
    """ASCII-фолбэк, если matplotlib недоступен."""
    if not xs:
        return "Нет данных."
    maxy = max(ys) or 1
    lines = []
    for x, y in zip(xs, ys):
        bar = "█" * max(1, int(width * y / maxy))
        lines.append(f"{x}: {bar} {y}")
    return "\n".join(lines)

# ============================================================
#  РЕГИСТРАЦИЯ КОМАНД
# ============================================================
GAME_COMMANDS = [
    ("start", "👋 Приветствие и добавление в группу"),
    ("help", "📖 Справочник команд"),
    ("golda", "💰 Получить голду (раз в час)"),
    ("stats", "🏆 Топ-10 богачей чата"),
    ("gstats", "📊 Твой отчёт по голде"),
    ("nation", "🌍 Случайная национальность"),
    ("govno", "💩 Кинуть какашку (реплай)"),
    ("word", "📰 Слово дня"),
    ("obvinit", "⚖️ Обвинить юзера (реплай)"),
    ("kloun", "🤡 Выбрать клоуна дня"),
    ("kazik", "🎲 Сыграть в казик"),
    ("pet", "🐾 Выбрать питомца (реплай, раз в день)"),
    ("marry", "💍 Пожениться (реплай)"),
]

def register_commands():
    cmds = [types.BotCommand(c, d) for c, d in GAME_COMMANDS]
    bot.set_my_commands(cmds)

# ============================================================
#  ДОБАВЛЕНИЕ БОТА В ГРУППУ / УДАЛЕНИЕ  (работает даже в privacy mode)
# ============================================================
@bot.my_chat_member_handler()
def on_my_chat_member(upd: types.ChatMemberUpdated):
    chat = upd.chat
    if chat.type not in ("group", "supergroup"):
        return
    status = upd.new_chat_member.status
    if status in ("member", "administrator", "creator"):
        track_group(chat.id, chat.title or str(chat.id))
        # сразу пытаемся поприветствовать, если стали админом/добавили
        try:
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("➕ Добавить в группу", url=GROUP_URL))
            bot.send_message(chat.id,
                             "👋 Привет, группа!\n\n"
                             "Я — игровой бот «Шутки за 200». "
                             "Введи /help, чтобы посмотреть команды.",
                             reply_markup=kb)
        except Exception:
            pass
    elif status in ("left", "kicked"):
        # можно пометить как неактивную, но оставим для истории
        pass

# ============================================================
#  /start  и  /help
# ============================================================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    if is_group(message):
        track_group(message.chat.id, message.chat.title or str(message.chat.id))
        ensure_player(message.chat.id, message.from_user.id,
                      message.from_user.username, message.from_user.first_name)
        track_event(message.chat.id, message.from_user.id, "start")
    name = message.from_user.first_name
    text = (f"👋 Привет, {name}!\n\n"
            "Я — игровой бот. При помощи меня можно кидаться какашками "
            "и заниматься саморазвитием.\nДоступен только в группах.")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➕ Добавить в группу", url=GROUP_URL))
    bot.send_message(message.chat.id, text, reply_markup=kb)


@bot.message_handler(commands=["help"])
def cmd_help(message):
    if not is_group(message):
        bot.reply_to(message, "📖 Справочник доступен в группах. Добавь меня в группу!")
        return
    ensure_player(message.chat.id, message.from_user.id,
                  message.from_user.username, message.from_user.first_name)
    track_event(message.chat.id, message.from_user.id, "help")
    text = ("📖 <b>СПРАВОЧНИК КОМАНД</b>\n\n"
            "💰 /golda — получить голду (раз в 1 час)\n"
            "🏆 /stats — топ-10 богачей чата\n"
            "📊 /gstats — твой отчёт по голде\n"
            "🌍 /nation — случайная национальность\n"
            "💩 /govno (реплай) — кинуть какашку\n"
            "📰 /word — слово дня\n"
            "⚖️ /obvinit (реплай) — обвинить юзера\n"
            "🤡 /kloun — выбрать клоуна дня\n"
            "🎲 /kazik — сыграть в казик\n"
            "🐾 /pet (реплай) — выбрать питомца (раз в день)\n"
            "💍 /marry (реплай) — пожениться\n\n"
            "💡 Все команды также доступны в меню «/».")
    bot.reply_to(message, text)

# ============================================================
#  /golda
# ============================================================
@bot.message_handler(commands=["golda"])
def cmd_golda(message):
    if not is_group(message): return
    ensure_player(message.chat.id, message.from_user.id,
                  message.from_user.username, message.from_user.first_name)
    p = get_player(message.chat.id, message.from_user.id)
    now = int(time.time())
    if now - p["last_gold"] < GOLDA_COOLDOWN:
        left = GOLDA_COOLDOWN - (now - p["last_gold"])
        bot.reply_to(message, f"⏳ <b>Кулдаун!</b>\n\nТы уже забирал голду. "
                              f"Приходи через {humanize_minutes(left)} мин.")
        return
    amount = random.randint(0, 100)
    add_gold(message.chat.id, message.from_user.id, amount)
    set_last_gold(message.chat.id, message.from_user.id, now)
    track_event(message.chat.id, message.from_user.id, "golda")
    bot.reply_to(message, f"💸 <b>ГОЛДА ПОЛУЧЕНА!</b>\n\n"
                          f"Тебе начислено: {amount} 💰\n\n"
                          f"Следующий сбор доступен через 1 час.")

# ============================================================
#  /stats  — универсальный:
#    • в ЛС + админ  → полная аналитика
#    • в группе      → топ-10 чата
# ============================================================
@bot.message_handler(commands=["stats"])
def cmd_stats(message):
    if is_private(message):
        if message.from_user.id != ADMIN_ID:
            return
        # ---------- АДМИН-СТАТИСТИКА ----------
        now = int(time.time())
        week_ago = now - 7 * 86400
        with adb() as con:
            groups_total = con.execute("SELECT COUNT(*) c FROM groups").fetchone()["c"]
            users_total = con.execute(
                "SELECT COUNT(DISTINCT user_id) c FROM events").fetchone()["c"]
            records = con.execute("SELECT COUNT(*) c FROM events").fetchone()["c"]
            week = con.execute(
                "SELECT COUNT(*) c FROM events WHERE ts>?", (week_ago,)).fetchone()["c"]
        with gdb() as con:
            players = con.execute(
                "SELECT COUNT(DISTINCT user_id) c FROM players").fetchone()["c"]
        text = ("📈 <b>ПОЛНАЯ СТАТИСТИКА БОТА</b>\n\n"
                f"👥 Охват аудитории:\n"
                f"• Людей в группах (игроки): {players}\n"
                f"• Всего активных групп: {groups_total}\n"
                f"• Групп с ошибкой доступа: 0\n\n"
                f"🎮 Вовлечённость:\n"
                f"• Уникальных игроков (всего): {users_total}\n"
                f"• Всего записей в базе: {records}\n\n"
                f"🐞 Игровой процесс:\n"
                f"• Всего нажатий: {records}\n"
                f"• Нажатий за 7 дней: {week}\n\n"
                f"ℹ️ Дополнительно: /groups /globaltop /fullreport /ex /exall /debug")
        bot.send_message(message.chat.id, text)
        return

    if is_group(message):
        # ---------- ТОП ЧАТА ----------
        rows = top_players(message.chat.id, 10)
        if not rows:
            bot.reply_to(message, "🏆 Пока нет игроков с голдой. Начни с /golda!")
            return
        lines = ["🏆 <b>ТОП-10 БОГАЧЕЙ ЧАТА</b>\n"]
        for i, r in enumerate(rows, 1):
            lines.append(f"{i}. {r['first_name']} — {r['gold']} 💰")
        bot.reply_to(message, "\n".join(lines))
        track_event(message.chat.id, message.from_user.id, "stats")

# ============================================================
#  /gstats
# ============================================================
@bot.message_handler(commands=["gstats"])
def cmd_gstats(message):
    if not is_group(message): return
    ensure_player(message.chat.id, message.from_user.id,
                  message.from_user.username, message.from_user.first_name)
    p = get_player(message.chat.id, message.from_user.id)
    last = (datetime.fromtimestamp(p["last_gold"]).strftime("%d.%m %H:%M")
            if p["last_gold"] else "ещё не собирал")
    text = (f"📊 <b>ТВОЙ ОТЧЁТ</b>\n\n"
            f"👤 {message.from_user.first_name}\n"
            f"💰 Баланс: {p['gold']}\n"
            f"📅 Последний сбор: {last}")
    bot.reply_to(message, text)
    track_event(message.chat.id, message.from_user.id, "gstats")

# ============================================================
#  /nation  и  /word
# ============================================================
@bot.message_handler(commands=["nation"])
def cmd_nation(message):
    if not is_group(message): return
    nat = random.choice(NATIONALITIES)
    bot.reply_to(message, f"🧬 <b>АНАЛИЗ ДНК ЗАВЕРШЁН</b>\n\n"
                          f"Твоя национальность: <b>{nat}</b>\n\n"
                          f"Результат может измениться в следующий раз.")
    track_event(message.chat.id, message.from_user.id, "nation")


@bot.message_handler(commands=["word"])
def cmd_word(message):
    if not is_group(message): return
    bot.reply_to(message, f"📰 <b>СЛОВО ДНЯ</b>\n\n👉 {random.choice(WORDS_OF_DAY)}")
    track_event(message.chat.id, message.from_user.id, "word")

# ============================================================
#  /govno
# ============================================================
@bot.message_handler(commands=["govno"])
def cmd_govno(message):
    if not is_group(message): return
    if not message.reply_to_message:
        bot.reply_to(message, "🎯 Кинь какашку кому-то! Для этого ответь на "
                              "сообщение жертвы командой /govno")
        return
    target = message.reply_to_message.from_user
    if target.id == message.from_user.id:
        bot.reply_to(message, "🤢 Нельзя кидать какашки в самого себя!")
        return
    if target.is_bot:
        bot.reply_to(message, "🤖 Ботов обмазывать нельзя, они и так в какашках.")
        return
    a = mention(message.from_user.id, message.from_user.first_name)
    b = mention(target.id, target.first_name)
    text = random.choice(GOVNO_TEMPLATES).format(a=a, b=b)
    bot.reply_to(message, text)
    track_event(message.chat.id, message.from_user.id, "govno")

# ============================================================
#  /obvinit
# ============================================================
@bot.message_handler(commands=["obvinit"])
def cmd_obvinit(message):
    if not is_group(message): return
    if not message.reply_to_message:
        bot.reply_to(message, "⚖️ Чтобы обвинить кого-то, ответь на его сообщение "
                              "командой /obvinit")
        return
    target = message.reply_to_message.from_user
    if target.id == message.from_user.id:
        bot.reply_to(message, "🩺 Шизофрения? Обвинять самого себя это кринж.")
        return
    if target.is_bot:
        bot.reply_to(message, "🤖 Ботов обвинять нельзя.")
        return

    tpl = random.choice(ACCUSATION_TEMPLATES)
    accuser = message.from_user.first_name
    defendant = target.first_name
    accusation = tpl.format(defendant, accuser)

    court_id = f"{message.chat.id}:{message.message_id}"
    text = (f"⚖️ <b>ОБВИНЕНИЕ В СУДЕ!</b>\n\n{accusation}\n\n"
            f"🗳️ Голосуйте кнопками ниже! (1 минута)\n"
            f"<i>Обвинитель всегда побеждает, но каждый голос «Виновен» — "
            f"это -10 голды для жертвы!</i>")

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Виновен (0)", callback_data=f"court:{court_id}:guilty"),
        types.InlineKeyboardButton("❌ Опять невиновен (0)", callback_data=f"court:{court_id}:not"),
    )
    sent = bot.send_message(message.chat.id, text, reply_markup=kb)
    track_event(message.chat.id, message.from_user.id, "obvinit")

    chat_id = message.chat.id
    target_id = target.id

    def finish():
        time.sleep(COURT_DURATION)
        tally = court_tally(court_id)
        guilty = tally.get("guilty", 0)
        notv = tally.get("not", 0)
        fine = guilty * 10
        taken = take_gold(chat_id, target_id, fine)
        result = (
            f"⚖️ <b>СУД ОКОНЧЕН!</b>\n\n━━━━━━━━━━━━━━━\n\n{accusation}\n\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"✅ Голосов за обвинение: {guilty}\n\n"
            f"❌ Голосов против: {notv} (проигнорированы)\n\n"
            f"👨‍⚖️ Вердикт: 🟢 <b>ПРАВДА!</b> Обвиняемый официально признан виновным.\n\n"
            f"💸 Обвиняемый оштрафован на {taken} голды!"
        )
        try:
            bot.edit_message_text(result, chat_id=sent.chat.id,
                                  message_id=sent.message_id)
        except Exception:
            pass
        clear_court(court_id)

    threading.Thread(target=finish, daemon=True).start()


@bot.callback_query_handler(func=lambda c: c.data.startswith("court:"))
def cb_court(call):
    parts = call.data.split(":")
    if len(parts) != 3: return
    _, court_id, vote = parts
    court_vote(court_id, call.from_user.id, vote)
    tally = court_tally(court_id)
    g = tally.get("guilty", 0)
    n = tally.get("not", 0)
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(f"✅ Виновен ({g})", callback_data=f"court:{court_id}:guilty"),
        types.InlineKeyboardButton(f"❌ Опять невиновен ({n})", callback_data=f"court:{court_id}:not"),
    )
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=kb)
    except Exception:
        pass
    bot.answer_callback_query(call.id, "Голос учтён!")

# ============================================================
#  /kloun
# ============================================================
@bot.message_handler(commands=["kloun"])
def cmd_kloun(message):
    if not is_group(message): return
    chat_id = message.chat.id
    today = today_str()
    existing = get_clown(chat_id)
    if existing and existing["day"] == today:
        bot.reply_to(message, f"🤡 Сегодняшний Клоун дня уже выбран!\n\n"
                              f"Это {existing['name']}. Ждите завтра.")
        return

    players = chat_players(chat_id)
    ids = {p["user_id"]: p["first_name"] for p in players}
    ids[message.from_user.id] = message.from_user.first_name
    if not ids:
        bot.reply_to(message, "🎪 Цирк пуст! Сначала кто-нибудь должен написать /golda.")
        return
    uid, name = random.choice(list(ids.items()))
    reason = random.choice(CLOWN_REASONS)
    set_clown(chat_id, uid, name, reason, today)
    track_event(chat_id, message.from_user.id, "kloun")
    bot.reply_to(message, f"🎪 <b>ЦИРК ПРИЕХАЛ!</b>\n\n"
                          f"🤡 Клоун дня в этом чате — <b>{name}</b>\n\n"
                          f"📌 Причина: {reason}")

# ============================================================
#  /kazik
# ============================================================
@bot.message_handler(commands=["kazik"])
def cmd_kazik(message):
    if not is_group(message): return
    chat_id = message.chat.id
    uid = message.from_user.id
    ensure_player(chat_id, uid, message.from_user.username, message.from_user.first_name)
    kazik_set(chat_id, uid, step=1)
    track_event(chat_id, uid, "kazik_start")
    bot.reply_to(message, "🎲 <b>КАЗИК</b>\n\nНа что хочешь поставить?\n\n"
                          "(например: «то что Сева толстый»)")


@bot.message_handler(func=lambda m: is_group(m) and
                     kazik_get(m.chat.id, m.from_user.id) is not None and
                     kazik_get(m.chat.id, m.from_user.id)["step"] in (1, 2),
                     content_types=["text"])
def kazik_step(message):
    chat_id = message.chat.id
    uid = message.from_user.id
    st = kazik_get(chat_id, uid)
    if not st: return
    text = (message.text or "").strip()
    if not text:
        bot.reply_to(message, "🤔 Пусто. Напиши что-нибудь!")
        return

    if st["step"] == 1:
        kazik_set(chat_id, uid, step=2, what=text)
        bot.reply_to(message, "🎯 А что ты хочешь поставить?\n\n"
                              "(например: «свою огромную попу»)")
        return

    if st["step"] == 2:
        what = st["bet_what"]
        on = text
        win = random.random() < 0.5
        if win:
            out = (f"🎉 <b>ВЫИГРАЛ!</b>\n\nТы поставил: «{what}»\n"
                   f"На кону было: «{on}»\n\nКазик решил: ДА! ✅")
        else:
            out = (f"😢 <b>ПРОИГРАЛ!</b>\n\nТы поставил: «{what}»\n"
                   f"На кону было: «{on}»\n\nКазик решил: НЕТ! ❌")
        kazik_clear(chat_id, uid)
        track_event(chat_id, uid, "kazik")
        bot.reply_to(message, out)

# ============================================================
#  /pet
# ============================================================
@bot.message_handler(commands=["pet"])
def cmd_pet(message):
    if not is_group(message): return
    if not message.reply_to_message:
        bot.reply_to(message, "🐾 Чтобы выбрать питомца, ответь на сообщение "
                              "человека командой /pet")
        return
    target = message.reply_to_message.from_user
    if target.id == message.from_user.id:
        bot.reply_to(message, "🐾 Себя в питомцы? Ну ты и фантазёр.")
        return
    if target.is_bot:
        bot.reply_to(message, "🤖 Бот не может быть питомцем, он и так всем служит.")
        return

    chat_id = message.chat.id
    uid = message.from_user.id
    ensure_player(chat_id, uid, message.from_user.username, message.from_user.first_name)
    p = get_player(chat_id, uid)
    now = int(time.time())
    if p["last_pet"]:
        last_day = datetime.fromtimestamp(p["last_pet"]).date()
        if last_day == date.today():
            bot.reply_to(message, "🐾 Ты уже выбирал питомца сегодня. Приходи завтра!")
            return

    emoji = random.choice(["🐕", "🐈", "🐹", "🦜"])
    set_pet(chat_id, uid, target.id, target.first_name, now)
    track_event(chat_id, uid, "pet")
    bot.reply_to(message, f"🐾 <b>ПИТОМЕЦ ВЫБРАН!</b>\n\n"
                          f"{target.first_name} теперь твой питомец на сегодня! {emoji}")

# ============================================================
#  /marry
# ============================================================
@bot.message_handler(commands=["marry"])
def cmd_marry(message):
    if not is_group(message): return
    if not message.reply_to_message:
        bot.reply_to(message, "💍 Чтобы пожениться, ответь на сообщение партнёра "
                              "командой /marry")
        return
    target = message.reply_to_message.from_user
    if target.id == message.from_user.id:
        bot.reply_to(message, "💍 Жениться на себе? Это уже нарциссизм.")
        return
    if target.is_bot:
        bot.reply_to(message, "🤖 Бот не может жениться, у него обет безбрачия.")
        return

    chat_id = message.chat.id
    uid = message.from_user.id
    ensure_player(chat_id, uid, message.from_user.username, message.from_user.first_name)
    ensure_player(chat_id, target.id, target.username, target.first_name)
    me = get_player(chat_id, uid)
    other = get_player(chat_id, target.id)

    if me["marry_id"]:
        bot.reply_to(message, f"💍 {me['first_name']} уже состоит в браке!")
        return
    if other["marry_id"]:
        bot.reply_to(message, f"💍 {other['first_name']} уже состоит в браке!")
        return

    marry(chat_id, uid, target.id)
    track_event(chat_id, uid, "marry")
    bot.reply_to(message, f"💍 <b>СВАДЬБА!</b>\n\n"
                          f"{me['first_name']} и {target.first_name} теперь женаты! 💒\n\n"
                          f"Горько! 🥂")

# ============================================================
#  АДМИН-КОМАНДЫ
# ============================================================
def admin_only(func):
    def wrapper(message, *args, **kwargs):
        if not is_private(message):
            return
        if message.from_user.id != ADMIN_ID:
            return
        return func(message, *args, **kwargs)
    return wrapper


@bot.message_handler(commands=["adminhelp"])
@admin_only
def cmd_adminhelp(message):
    text = ("👑 <b>Команды администратора</b>\n\n"
            "📊 Аналитика:\n"
            "• /stats — Подробная статистика (в ЛС)\n"
            "• /fullreport — Выгрузить ВСЮ аналитику в TXT\n"
            "• /ex — Графики за 7 дней\n"
            "• /exall — Графики за всё время\n"
            "• /groups — Список групп из базы\n"
            "• /globaltop — Глобальный топ игроков\n"
            "• /debug — Диагностика БД\n\n"
            "🛠 Управление:\n"
            "• /an (ответом) — Рассылка\n"
            "• /do — Скачать базы данных")
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=["fullreport"])
@admin_only
def cmd_fullreport(message):
    lines = ["=== ПОЛНЫЙ ОТЧЁТ ===", f"Сформирован: {datetime.now():%Y-%m-%d %H:%M}", ""]
    with adb() as con:
        groups = con.execute("SELECT * FROM groups ORDER BY added_at").fetchall()
        lines.append(f"Всего групп: {len(groups)}\n")
        for g in groups:
            # Подтягиваем актуальное название из API, если в БД нет
            title = g["title"] or "?"
            try:
                chat = bot.get_chat(g["chat_id"])
                title = chat.title or title
            except Exception:
                pass
            lines.append(f"• {title} (id={g['chat_id']})")
            with gdb() as gcon:
                ps = gcon.execute(
                    "SELECT user_id, first_name, username, gold FROM players WHERE chat_id=?",
                    (g["chat_id"],)).fetchall()
                if not ps:
                    lines.append("    (игроков пока нет)")
                for p in ps:
                    lines.append(f"    - {p['first_name']} (@{p['username'] or '-'}) "
                                 f"id={p['user_id']} gold={p['gold']}")
            lines.append("")
        total_events = con.execute("SELECT COUNT(*) c FROM events").fetchone()["c"]
        lines.append(f"Всего событий: {total_events}")
    data = "\n".join(lines).encode("utf-8")
    bot.send_document(message.chat.id, ("report.txt", data))


@bot.message_handler(commands=["groups"])
@admin_only
def cmd_groups(message):
    with adb() as con:
        groups = con.execute("SELECT * FROM groups ORDER BY added_at").fetchall()
    if not groups:
        bot.send_message(message.chat.id,
                         "Групп пока нет.\n"
                         "Добавь бота в группу — он сразу отреагирует на событие "
                         "my_chat_member и запишется в БД.")
        return
    lines = ["📋 <b>Группы из базы:</b>"]
    for g in groups:
        title = g["title"] or "?"
        try:
            chat = bot.get_chat(g["chat_id"])
            title = chat.title or title
        except Exception:
            title += " (нет доступа)"
        lines.append(f"• {title} — <code>{g['chat_id']}</code>")
    bot.send_message(message.chat.id, "\n".join(lines))


@bot.message_handler(commands=["globaltop"])
@admin_only
def cmd_globaltop(message):
    with gdb() as con:
        rows = con.execute("SELECT chat_id, first_name, gold FROM players "
                           "WHERE gold>0 ORDER BY gold DESC LIMIT 20").fetchall()
    if not rows:
        bot.send_message(message.chat.id, "Пусто.")
        return
    lines = ["🌍 <b>ГЛОБАЛЬНЫЙ ТОП</b>"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r['first_name']} (chat {r['chat_id']}) — {r['gold']} 💰")
    bot.send_message(message.chat.id, "\n".join(lines))


@bot.message_handler(commands=["debug"])
@admin_only
def cmd_debug(message):
    with adb() as con:
        e = con.execute("SELECT COUNT(*) c FROM events").fetchone()["c"]
        recent = con.execute("SELECT * FROM events ORDER BY ts DESC LIMIT 10").fetchall()
        glist = con.execute("SELECT chat_id, title FROM groups").fetchall()
    with gdb() as con:
        p = con.execute("SELECT COUNT(*) c FROM players").fetchone()["c"]
        sample = con.execute(
            "SELECT chat_id, user_id, first_name, gold FROM players LIMIT 10").fetchall()

    parts = [f"groups={len(glist)}, events={e}, players={p}",
             f"matplotlib={'OK' if HAS_MPL else 'НЕ УСТАНОВЛЕН'}", "", "Группы:"]
    for r in glist:
        title = r["title"] or "?"
        try:
            chat = bot.get_chat(r["chat_id"])
            title = chat.title or title
        except Exception:
            title += " (нет доступа)"
        parts.append(f"  {r['chat_id']} — {title}")
    parts.append("")
    parts.append("Последние события:")
    for r in recent:
        parts.append(f"  {r['event']} chat={r['chat_id']} user={r['user_id']} "
                     f"{datetime.fromtimestamp(r['ts']):%m-%d %H:%M}")
    parts.append("")
    parts.append("Игроки (пример):")
    for r in sample:
        parts.append(f"  {r['first_name']} chat={r['chat_id']} gold={r['gold']}")
    bot.send_message(message.chat.id, "\n".join(parts))


@bot.message_handler(commands=["do"])
@admin_only
def cmd_do(message):
    for path in (GAME_DB, ANALYTICS_DB):
        if os.path.exists(path):
            with open(path, "rb") as f:
                bot.send_document(message.chat.id, (path, f.read()))


@bot.message_handler(commands=["an"])
@admin_only
def cmd_an(message):
    if not message.reply_to_message:
        bot.send_message(message.chat.id, "Ответь на сообщение, которое нужно разослать.")
        return
    src = message.reply_to_message
    with adb() as con:
        groups = con.execute("SELECT chat_id FROM groups").fetchall()
    ok = fail = 0
    for g in groups:
        try:
            bot.copy_message(g["chat_id"], src.chat.id, src.message_id)
            ok += 1
            time.sleep(0.05)
        except Exception:
            fail += 1
    bot.send_message(message.chat.id, f"✅ Успешно: {ok}\n❌ Ошибок: {fail}")


@bot.message_handler(commands=["ex", "exall"])
@admin_only
def cmd_ex(message):
    is_all = message.text.startswith("/exall")
    since = 0 if is_all else int(time.time()) - 7 * 86400
    with adb() as con:
        rows = con.execute("SELECT ts FROM events WHERE ts>? ORDER BY ts",
                           (since,)).fetchall()
    if not rows:
        bot.send_message(message.chat.id,
                         "Нет данных за выбранный период.\n"
                         "События пишутся при игровых действиях и обычных сообщениях.")
        return

    from collections import Counter
    days = Counter(datetime.fromtimestamp(r["ts"]).strftime("%Y-%m-%d") for r in rows)
    xs = sorted(days)
    ys = [days[d] for d in xs]

    # ---- matplotlib есть → PNG ----
    if HAS_MPL:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(xs, ys, marker="o")
        ax.set_title("Активность" + (" (всё время)" if is_all else " (7 дней)"))
        ax.set_ylabel("Событий")
        ax.tick_params(axis="x", rotation=45)
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        plt.close(fig)
        bot.send_photo(message.chat.id, buf)
        return

    # ---- matplotlib нет → ASCII-фолбэк ----
    chart = ascii_bar_chart(xs, ys)
    header = ("📊 <b>Активность</b>"
              + (" (всё время)" if is_all else " (7 дней)"))
    footer = ("\n\n<i>Совет: установи matplotlib в тот же venv, где запущен бот, "
              "чтобы получать PNG-графики: pip install matplotlib</i>")
    # Telegram лимит 4096 символов
    body = chart
    max_len = 3500
    if len(body) > max_len:
        body = body[-max_len:]
        body = "…(начало обрезано)\n" + body
    bot.send_message(message.chat.id, header + "\n\n<pre>" + body + "</pre>" + footer)


# ============================================================
#  ФОНОВЫЙ ТРЕКИНГ
# ============================================================
@bot.message_handler(func=lambda m: True,
                     content_types=["text", "photo", "sticker", "video",
                                    "voice", "document", "audio"])
def track_all(message):
    if not is_group(message):
        return
    track_group(message.chat.id, message.chat.title or str(message.chat.id))
    ensure_player(message.chat.id, message.from_user.id,
                  message.from_user.username, message.from_user.first_name)
    if message.content_type == "text" and (message.text or "").startswith("/"):
        return
    track_event(message.chat.id, message.from_user.id, "message")


# ============================================================
#  MAIN
# ============================================================
if __name__ == "__main__":
    if not BOT_TOKEN:
        raise SystemExit("Не задан BOT_TOKEN")
    init_dbs()
    register_commands()
    print(f"Бот запущен... matplotlib={'OK' if HAS_MPL else 'НЕ УСТАНОВЛЕН (будет ASCII-график)'}")
    bot.infinity_polling(skip_pending=True, timeout=30)
