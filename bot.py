import json
import random
import os
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8539185338:AAFfeRhe-uGYE_znA5f1QPTSVsTOUtmOY90"
PORT = int(os.environ.get("PORT", 10000))
RENDER_URL = "https://gas-bot-4cyt.onrender.com"

decks = {}
stats = {"газ": 0, "полный_газ": 0, "пиздец_газ": 0, "делай": 0}
original_decks = {}
current_player = 0
turn = 0
skips = [0, 0]
last_deck = None
player_names = ["", ""]
player_scores = [0, 0]
player_cards = {"ебанутый": [[], []], "мегаебанутый": [[], []]}
combo_counter = [0, 0]
combo_deck = [None, None]
achievements = [set(), set()]
current_story_id = None
game_started = False

flask_app = Flask(__name__)

main_keyboard = ReplyKeyboardMarkup([
    ["🕊 ГАЗ", "🔥 ПОЛНЫЙ ГАЗ"],
    ["💀 ПИЗДЕЦ ГАЗ", "🎬 ДЕЛАЙ"],
    ["🎲 РАНДОМ", "⏭ НЕКСТ"],
    ["📋 КОМАНДЫ"]
], resize_keyboard=True)

def load_decks():
    global decks, original_decks
    files = {
        "газ": "data/cards_gas.txt",
        "полный_газ": "data/cards_full_gas.txt",
        "пиздец_газ": "data/cards_pizdec_gas.txt",
        "делай": "data/cards_delai.txt"
    }
    for deck_name, filepath in files.items():
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            decks[deck_name] = data["cards"][:]
            original_decks[deck_name] = data["cards"][:]

def reset_game():
    global decks, stats, turn, current_player, skips, last_deck, game_started
    global player_scores, player_cards, combo_counter, combo_deck, achievements
    decks = {name: cards[:] for name, cards in original_decks.items()}
    stats = {"газ": 0, "полный_газ": 0, "пиздец_газ": 0, "делай": 0}
    turn = 0
    skips = [0, 0]
    last_deck = None
    current_player = 0
    game_started = True
    player_scores = [0, 0]
    player_cards = {"ебанутый": [[], []], "мегаебанутый": [[], []]}
    combo_counter = [0, 0]
    combo_deck = [None, None]
    achievements = [set(), set()]

def is_x2():
    return random.randint(1, 100) <= 13

def card_score(card):
    level = card.get("level", "")
    if level == "мегаебанутый":
        return 7
    if level == "ебанутый":
        return 5
    deck = card.get("deck", "")
    if deck == "газ":
        return 1
    if deck in ("полный_газ", "делай"):
        return 3
    if deck == "пиздец_газ":
        return 5
    return 1

def pull_card(deck_name, is_arrow=False):
    global decks, stats, turn, current_player, last_deck
    global player_scores, player_cards, combo_counter, combo_deck, achievements

    if deck_name not in decks or not decks[deck_name]:
        reset_game()
        return "🃏 Колода была пуста и сброшена. Тяни снова."

    card = random.choice(decks[deck_name])
    decks[deck_name].remove(card)
    stats[deck_name] += 1

    if not is_arrow:
        turn += 1
        player_idx = current_player
        current_player = 1 - current_player
    else:
        player_idx = current_player

    last_deck = deck_name
    score = card_score(card)
    player_scores[player_idx] += score
    level = card.get("level", "")

    if level == "ебанутый":
        player_cards["ебанутый"][player_idx].append(card["text"])
    elif level == "мегаебанутый":
        player_cards["мегаебанутый"][player_idx].append(card["text"])

    response = f"🎲 {deck_name.upper()} — ход {turn}\n"
    response += f"👤 Тянет: {player_names[player_idx]}\n\n"
    
    if level == "мегаебанутый":
        response += "👑 МЕГАЕБАНУТАЯ КАРТА! (7 баллов)\n\n"
    elif level == "ебанутый":
        response += "☠️ ЕБАНУТАЯ КАРТА! (5 баллов)\n\n"
    elif deck_name == "пиздец_газ":
        response += "⚠️ ВНИМАНИЕ! Карта из Пиздец газа!\n\n"
    
    response += card["text"]

    if card["type"] == "arrow":
        target = card["target"]
        response += f"\n\n➡️ Переход в «{target.upper()}»"
        if target == "рандом":
            target = random.choice(["газ", "полный_газ", "пиздец_газ", "делай"])
            response += f"\n🎯 Выпало: «{target.upper()}»"
        response += "\n\n" + pull_card(target, is_arrow=True)

    if is_x2() and card["type"] != "arrow":
        response += "\n\n🔥 Х2! Карта для обоих!"

    return response

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Добро пожаловать в GAZ!\n\n"
        "Введите имя первой участницы:"
    )
    context.user_data["awaiting_name"] = 1

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_player, player_names, game_started, skips, last_deck, player_scores

    text = update.message.text.strip()
    
    if context.user_data.get("awaiting_name") == 1:
        player_names[0] = text
        context.user_data["awaiting_name"] = 2
        await update.message.reply_text("Теперь введите имя второго участника:")
        return
    
    if context.user_data.get("awaiting_name") == 2:
        player_names[1] = text
        context.user_data["awaiting_name"] = 0
        reset_game()
        await update.message.reply_text(
            f"🏰 Игра начинается!\n\n"
            f"Первый ход — {player_names[0]}.\n"
            f"Выбирай колоду:",
            reply_markup=main_keyboard
        )
        return

    if not game_started:
        await update.message.reply_text("Нажми /start чтобы начать игру.")
        return

    text = update.message.text.upper().strip()
    
    deck_map = {
        "🕊 ГАЗ": "газ",
        "ГАЗ": "газ",
        "🔥 ПОЛНЫЙ ГАЗ": "полный_газ",
        "ПОЛНЫЙ ГАЗ": "полный_газ",
        "💀 ПИЗДЕЦ ГАЗ": "пиздец_газ",
        "ПИЗДЕЦ ГАЗ": "пиздец_газ",
        "🎬 ДЕЛАЙ": "делай",
        "ДЕЛАЙ": "делай"
    }

    if text in deck_map:
        response = pull_card(deck_map[text])
    elif text in ("🎲 РАНДОМ", "РАНДОМ"):
        deck = random.choice(["газ", "полный_газ", "пиздец_газ", "делай"])
        response = f"🎯 Рандом выбрал: «{deck.upper()}»\n\n" + pull_card(deck)
    elif text in ("⏭ НЕКСТ", "НЕКСТ"):
        if last_deck:
            skips[current_player] += 1
            score = card_score({"deck": last_deck, "level": ""})
            player_scores[current_player] -= score
            response = f"⏭ {player_names[current_player]} пропускает ход (−{score} балла).\n\n" + pull_card(last_deck)
        else:
            response = "Сначала вытяни карту."
    elif text in ("📋 КОМАНДЫ", "КОМАНДЫ"):
        response = (
            "📋 ДОСТУПНЫЕ КОМАНДЫ:\n\n"
            "/start — новая игра\n"
            "/restart — сброс колод\n"
            "/vibe — атмосфера\n"
            "/rules — правила\n"
            "/top — топ-5 карт\n"
            "/stats — статистика\n"
            "/finish — завершить игру"
        )
    else:
        response = "Используй кнопки или команды."

    await update.message.reply_text(response)

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_game()
    await update.message.reply_text("🔄 Колоды сброшены!", reply_markup=main_keyboard)

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = sum(stats.values())
    text = "📊 СТАТИСТИКА\n\n"
    for deck, count in stats.items():
        text += f"{deck.upper()}: {count} карт\n"
    text += f"\nВсего: {total} карт"
    await update.message.reply_text(text)

async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🏁 ИГРА ЗАВЕРШЕНА!\n\n"
    text += f"Газ: {stats['газ']}\nПолный газ: {stats['полный_газ']}\n"
    text += f"Пиздец газ: {stats['пиздец_газ']}\nДелай: {stats['делай']}\n"
    text += f"\nСпасибо за игру! 🔥"
    await update.message.reply_text(text)
    reset_game()

async def vibe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌙 Атмосфера накаляется... Продолжаем игру.", reply_markup=main_keyboard)

async def rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📜 ПРАВИЛА ИГРЫ:\n\n"
        "🕊 Газ — лёгкие вопросы\n"
        "🔥 Полный газ — интим\n"
        "💀 Пиздец газ — стыд и треш\n"
        "🎬 Делай — действия\n\n"
        "⏭ Некст — пропуск карты\n"
        "🎲 Рандом — случайная колода"
    )

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏆 ТОП-5 карт за игру пока недоступен. Сыграйте больше!")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Понг! Бот жив.")

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    telegram_app.update_queue.put_nowait(update)
    return "OK", 200

@flask_app.route("/")
def home():
    return "Bot is live!", 200

if __name__ == "__main__":
    load_decks()
    telegram_app = Application.builder().token(TOKEN).build()
    
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("restart", restart))
    telegram_app.add_handler(CommandHandler("stats", stats_cmd))
    telegram_app.add_handler(CommandHandler("finish", finish))
    telegram_app.add_handler(CommandHandler("vibe", vibe))
    telegram_app.add_handler(CommandHandler("rules", rules_cmd))
    telegram_app.add_handler(CommandHandler("top", top_cmd))
    telegram_app.add_handler(CommandHandler("ping", ping))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    import asyncio
    async def init():
        await telegram_app.initialize()
        await telegram_app.start()
    asyncio.run(init())

    import requests
    requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={RENDER_URL}/webhook")

    flask_app.run(host="0.0.0.0", port=PORT)
