import json
import random
import os
import asyncio
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8785235169:AAFSyRBfJ4acy8fE5ip2bxWFXvVobTyzP1Y"
PORT = int(os.environ.get("PORT", 10000))

decks = {}
stats = {"газ": 0, "полный_газ": 0, "пиздец_газ": 0, "делай": 0}
original_decks = {}
current_player = 0
turn = 0
skips = [0, 0]
last_deck = None
player_names = ["", ""]
player_scores = [0, 0]
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
    global decks, stats, turn, current_player, skips, last_deck, game_started, player_scores
    decks = {name: cards[:] for name, cards in original_decks.items()}
    stats = {"газ": 0, "полный_газ": 0, "пиздец_газ": 0, "делай": 0}
    turn = 0
    skips = [0, 0]
    last_deck = None
    current_player = 0
    game_started = True
    player_scores = [0, 0]

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
    global decks, stats, turn, current_player, last_deck, player_scores

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
    await update.message.reply_text("Введите имя первой участницы:")
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
            f"🏰 Игра начинается!\n\nПервый ход — {player_names[0]}.\nВыбирай колоду:",
            reply_markup=main_keyboard
        )
        return

    if not game_started:
        await update.message.reply_text("Нажми /start чтобы начать игру.")
        return

    text_upper = update.message.text.upper().strip()

    deck_map = {
        "🕊 ГАЗ": "газ", "ГАЗ": "газ",
        "🔥 ПОЛНЫЙ ГАЗ": "полный_газ", "ПОЛНЫЙ ГАЗ": "полный_газ",
        "💀 ПИЗДЕЦ ГАЗ": "пиздец_газ", "ПИЗДЕЦ ГАЗ": "пиздец_газ",
        "🎬 ДЕЛАЙ": "делай", "ДЕЛАЙ": "делай"
    }

    if text_upper in deck_map:
        response = pull_card(deck_map[text_upper])
    elif text_upper in ("🎲 РАНДОМ", "РАНДОМ"):
        deck = random.choice(["газ", "полный_газ", "пиздец_газ", "делай"])
        response = f"🎯 Рандом выбрал: «{deck.upper()}»\n\n" + pull_card(deck)
    elif text_upper in ("⏭ НЕКСТ", "НЕКСТ"):
        if last_deck:
            skips[current_player] += 1
            score = card_score({"deck": last_deck, "level": ""})
            player_scores[current_player] -= score
            response = f"⏭ {player_names[current_player]} пропускает (−{score} балла).\n\n" + pull_card(last_deck)
        else:
            response = "Сначала вытяни карту."
    elif text_upper in ("📋 КОМАНДЫ", "КОМАНДЫ"):
        response = "📋 /start /restart /stats /finish /vibe /rules /top /ping"
    elif text_upper == "/START":
        await start(update, context)
        return
    elif text_upper == "/RESTART":
        reset_game()
        response = "🔄 Колоды сброшены!"
    elif text_upper == "/STATS":
        total = sum(stats.values())
        response = f"📊 Газ: {stats['газ']} | Полный газ: {stats['полный_газ']} | Пиздец газ: {stats['пиздец_газ']} | Делай: {stats['делай']}\nВсего: {total}"
    elif text_upper == "/FINISH":
        response = f"🏁 Игра завершена!\nГаз: {stats['газ']}\nПолный газ: {stats['полный_газ']}\nПиздец газ: {stats['пиздец_газ']}\nДелай: {stats['делай']}\n\nСпасибо за игру!"
        reset_game()
    elif text_upper == "/VIBE":
        response = "🌙 Атмосфера накаляется..."
    elif text_upper == "/RULES":
        response = "📜 Газ — лёгкие вопросы. Полный газ — интим. Пиздец газ — стыд. Делай — действия."
    elif text_upper == "/TOP":
        response = "🏆 ТОП-5 пока недоступен."
    elif text_upper == "/PING":
        response = "🏓 Понг!"
    else:
        response = "Используй кнопки или команды."

    await update.message.reply_text(response)

@flask_app.route("/")
def home():
    return "Bot is live!", 200

if __name__ == "__main__":
    load_decks()
    telegram_app = Application.builder().token(TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    async def run_bot():
        await telegram_app.initialize()
        await telegram_app.start()
        await telegram_app.updater.start_polling()
        print("Бот запущен!")
        await asyncio.Event().wait()

    asyncio.run(run_bot())
