import json
import random
import os
import asyncio
from datetime import datetime
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
player_deck_stats = [{"газ": 0, "полный_газ": 0, "пиздец_газ": 0, "делай": 0}, {"газ": 0, "полный_газ": 0, "пиздец_газ": 0, "делай": 0}]
player_cards = {"ебанутый": [[], []], "мегаебанутый": [[], []]}
all_player_cards = [[], []]
achievements = [set(), set()]
game_started = False
current_story = None

flask_app = Flask(__name__)

main_keyboard = ReplyKeyboardMarkup([
    ["🕊 ГАЗ", "🔥 ПОЛНЫЙ ГАЗ"],
    ["💀 ПИЗДЕЦ ГАЗ", "🎬 ДЕЛАЙ"],
    ["🎲 РАНДОМ", "⏭ НЕКСТ"],
    ["📋 КОМАНДЫ"]
], resize_keyboard=True)

welcome_text = (
    "🔥 **Добро пожаловать в GAZ!**\n\n"
    "Привет, игрок!\n\n"
    "Хочешь новых ощущений в коктейле с незабываемым вечером? 🍸 Тогда испытай себя в нашей игре **«GAZ»**.\n\n"
    "**1499 разнообразных карт.** Четыре колоды. Пять этапов. От лёгкого флирта до мегаебанутых вопросов на грани. "
    "Секретные карты, стрелки, брудершафты, парные задания, доминантные действия, ачивки.\n\n"
    "🕊 **Ходы 1–49 — Разогрев:** лёгкий флирт и разговоры.\n"
    "🔥 **Ходы 50–74 — Жара:** Пиздец газ и ебанутые карты выходят на сцену.\n"
    "💀 **Ходы 75–99 — Ад:** доминантные и мегаебанутые карты пробуждаются.\n"
    "☠️ **Ходы 100+ — Финал:** шанс экстрима ×1.5.\n\n"
    "Если смелости не хватает — придётся выпить. 🥃\n\n"
    "Кто же ты — игрок или лузер? Не испугался?\n\n"
    "Тогда жми **/start** и попытайся продержаться как можно дольше. Удачи! 🃏"
)

brudershaft_phrases = [
    "🍻 Брудершафт! Глоток — и поцелуй. Такова традиция.",
    "🍻 Брудершафт! Пьём из рук друг друга. И губы в губы.",
    "🍻 Брудершафт! Скрестите бокалы. Скрестите взгляды. Поцелуй.",
    "🍻 Брудершафт! Глоток за смелость. Поцелуй за честность.",
    "🍻 Брудершафт! Ритуал. Нарушать нельзя."
]

stories = [
    {
        "id": "castle", "title": "Замок Мерлина",
        "start": "🏰 Вы проникли в замок Мерлина. Двери захлопнулись. Из подвала — вой нежити. В центре зала — светящаяся колода. «Тот, кто пройдёт испытание — откроет портал. Но цена — ваши тайны.»",
        "vibes": ["🕯 Свечи гаснут одна за другой.", "🌙 Нежить скребётся о каменные стены.", "📜 Древние письмена светятся на стенах."],
        "ch50": "🔥 Полколоды позади. Замок дрожит. Нежить пробивается сквозь каменную кладку.\n\n🔥 Этап: ЖАРА (ходы 50-74)",
        "ch75": "💀 Нежить ворвалась в зал! Вы сражаетесь, но колода всё ещё в игре.\n\n💀 Этап: АД (ходы 75-99)",
        "ch100": "☠️ Портал открывается! Финальная битва. Кто победит — тот выйдет.\n\n☠️ Этап: ФИНАЛ (ходы 100+)",
        "end_score_f": "{name} набрала больше баллов и открыла портал. Но она не уходит одна — протягивает руку {partner}. Вы выходите вместе.",
        "end_score_m": "{name} набрал больше баллов. Портал открыт. «Без неё я не уйду». Портал расширяется. Вы свободны.",
        "end_brave_f": "{name} не пропустила ни карты. Мерлин: «Твоя смелость впечатляет». Вы оба свободны.",
        "end_brave_m": "{name} не струсил ни разу. Мерлин: «Такой смелости я не видел сто лет». Портал открыт."
    },
    {
        "id": "pirate", "title": "Чёрная жемчужина",
        "start": "🏴‍☠️ Вы в плену у капитана Блэквуда. Он бросает колоду: «Развлеките меня — или акулам. Победитель получит шлюпку».",
        "vibes": ["🌊 Волны бьются о борт.", "🦜 Попугай орёт: «Отвечай!»", "🍺 Боцман пьёт ром и смотрит на вас."],
        "ch50": "🔥 Полколоды позади. Капитан спускается: «А вы не так просты». Он приказал готовить акул.\n\n🔥 Этап: ЖАРА",
        "ch75": "💀 Шторм. Корабль трещит. Акулы кружат.\n\n💀 Этап: АД",
        "ch100": "☠️ Капитан: «Финал решит всё. Шлюпка или море».\n\n☠️ Этап: ФИНАЛ",
        "end_score_f": "{name} побеждает и получает ключ. Но не уходит одна — помогает {partner}. Вы в шлюпке. Впереди — свобода.",
        "end_score_m": "{name} побеждает. Вырубает боцмана плечом. Вы угоняете шлюпку. Пираты орут с борта.",
        "end_brave_f": "{name} не пропустила ни карты. Капитан снимает шляпу: «Крепче стали». Дарит золотую монету.",
        "end_brave_m": "{name} не струсил. Капитан: «Смелый. Глупый, но смелый. Приходи ещё»."
    },
    {
        "id": "space", "title": "Станция Прометей",
        "start": "🚀 Вы вдвоём на орбитальной станции. Кислорода на час. ИИ корабля: «Я запущу систему, если вы пройдёте тест на совместимость». Он выводит колоду вопросов.",
        "vibes": ["🌍 Земля в иллюминаторе — крошечная.", "🤖 ИИ: «Уровень кислорода — 47%. Рекомендую поторопиться».", "⚡ Короткое замыкание. Свет моргает."],
        "ch50": "🔥 Половина позади. ИИ: «Совместимость: 67%. Но нужно 90% для запуска».\n\n🔥 Этап: ЖАРА",
        "ch75": "💀 Кислорода на 15 минут. ИИ: «Ускорьтесь. Время истекает».\n\n💀 Этап: АД",
        "ch100": "☠️ Последние минуты. ИИ: «Финальный вопрос. Ответ определит вашу судьбу».\n\n☠️ Этап: ФИНАЛ",
        "end_score_f": "{name} набрала больше баллов. ИИ: «Совместимость 94%. Система запущена». Вы пристёгиваетесь и летите домой.",
        "end_score_m": "{name} набрал больше баллов. ИИ: «Вы прошли». Кислород поступает. Вы спасены.",
        "end_brave_f": "{name} не пропустила ни карты. ИИ: «Исключительная честность». Система запущена досрочно.",
        "end_brave_m": "{name} не струсил. ИИ: «Высокий уровень смелости». Кислород включён."
    },
    {
        "id": "cowboy", "title": "Дикий Запад",
        "start": "🤠 Тихий городок Дасти Крик. Шериф арестовал вас за карточную игру. «Если выиграете в мою игру — уйдёте. Проиграете — виселица». На столе — колода.",
        "vibes": ["🌵 Закат в пустыне.", "🥃 Виски налито. Шериф ждёт.", "🐴 Лошади фыркают у коновязи."],
        "ch50": "🔥 Полколоды позади. Шериф: «Я думал, вы сломаетесь раньше».\n\n🔥 Этап: ЖАРА",
        "ch75": "💀 Шериф злится. Он поставил на кон свой значок.\n\n💀 Этап: АД",
        "ch100": "☠️ Шериф встаёт: «Последняя карта. Или свобода, или петля».\n\n☠️ Этап: ФИНАЛ",
        "end_score_f": "{name} выигрывает. Шериф бросает ключи. «Забирай своего парня и уходите». Вы на лошадях. Впереди — прерия.",
        "end_score_m": "{name} выигрывает. Шериф: «Ты блефовал и победил». Вы свободны. Салун гудит.",
        "end_brave_f": "{name} не пропустила ни карты. Шериф: «Леди, вы крепкий орешек». Отпускает обоих.",
        "end_brave_m": "{name} не струсил. Шериф: «Смелый парень. Уважаю». Кидает ключи."
    },
    {
        "id": "tomb", "title": "Гробница Нефертити",
        "start": "🏺 Вы — археологи в гробнице. Ловушка захлопнулась. На саркофаге — колода и надпись: «Ответьте на вопросы — двери откроются. Солгите — останетесь навечно».",
        "vibes": ["🏜 Песок сыплется с потолка.", "🕯 Факелы гаснут.", "👁 Иероглифы светятся."],
        "ch50": "🔥 Полгробницы позади. Стены медленно сдвигаются.\n\n🔥 Этап: ЖАРА",
        "ch75": "💀 Песок по колено. Времени всё меньше.\n\n💀 Этап: АД",
        "ch100": "☠️ Саркофаг открывается. Фараон ждёт ответа.\n\n☠️ Этап: ФИНАЛ",
        "end_score_f": "{name} побеждает. Двери открываются. Вы выходите на рассветный песок.",
        "end_score_m": "{name} побеждает. Фараон: «Ты достоин». Выход открыт. Вы свободны.",
        "end_brave_f": "{name} не пропустила ни карты. Фараон: «Царица». Дарит амулет.",
        "end_brave_m": "{name} не струсил. Фараон: «Фараон». Дарит скипетр."
    },
    {
        "id": "detective", "title": "Нуарный детектив",
        "start": "🕵️ Дождливый Чикаго, 1947. Вас подставили. Вы в заброшенном офисе, на столе — колода и записка: «Ответьте на вопросы — я сниму обвинения». Детектив наблюдает через зеркало.",
        "vibes": ["🌧 Дождь барабанит по крыше.", "🚬 Дым от сигареты.", "📞 Телефон молчит."],
        "ch50": "🔥 Полколоды позади. Детектив: «Вы интересные подозреваемые».\n\n🔥 Этап: ЖАРА",
        "ch75": "💀 Детектив достаёт наручники. «Время истекает».\n\n💀 Этап: АД",
        "ch100": "☠️ Детектив: «Последний вопрос. От него зависит ваш приговор».\n\n☠️ Этап: ФИНАЛ",
        "end_score_f": "{name} побеждает. Детектив рвёт ордер. «Вы свободны. Настоящий преступник арестован».",
        "end_score_m": "{name} побеждает. Детектив: «Ты снял все подозрения». Вы выходите под дождь.",
        "end_brave_f": "{name} не пропустила ни карты. Детектив: «Вы невиновны». Отпускает.",
        "end_brave_m": "{name} не струсил. Детектив: «Честный парень». Снимает обвинения."
    },
    {
        "id": "vampire", "title": "Бал вампиров",
        "start": "🧛 Вы приглашены на бал к графу Дракуле. Это ловушка. Граф: «Сыграйте в мою игру. Понравитесь — станете одними из нас. Нет — ужином». Он бросает колоду.",
        "vibes": ["🕯 Канделябры мерцают.", "🍷 В бокалах — красное.", "🦇 Летучие мыши за окном."],
        "ch50": "🔥 Полколоды позади. Граф: «Вы интереснее, чем я думал».\n\n🔥 Этап: ЖАРА",
        "ch75": "💀 Вампиры окружают стол. «Время выбора близко».\n\n💀 Этап: АД",
        "ch100": "☠️ Граф встаёт: «Последняя карта. Или вечность, или свобода».\n\n☠️ Этап: ФИНАЛ",
        "end_score_f": "{name} побеждает. Граф: «Ты достойна бессмертия». Но вы выбираете свободу. Двери замка открываются.",
        "end_score_m": "{name} побеждает. Граф: «Смелый смертный». Отпускает вас обоих.",
        "end_brave_f": "{name} не пропустила ни карты. Граф: «Такая смелость — редкость». Вы свободны.",
        "end_brave_m": "{name} не струсил. Граф: «Я не видел такого сто лет». Отпускает."
    },
    {
        "id": "train", "title": "Поезд-призрак",
        "start": "🚂 Вы сели на ночной поезд. Кроме вас — ни души. Проводник с бледным лицом: «Этот поезд идёт до конечной. Выйти можно только если ответите на вопросы. Каждая карта — станция. Финиш — свобода».",
        "vibes": ["🌙 За окном — тьма.", "🕰 Часы тикают в купе.", "🚪 Дверь в соседнее купе скрипит."],
        "ch50": "🔥 Полпути позади. Проводник: «Следующая станция — ваша судьба».\n\n🔥 Этап: ЖАРА",
        "ch75": "💀 Поезд ускоряется. «Тормозов нет. Только вперёд».\n\n💀 Этап: АД",
        "ch100": "☠️ Проводник: «Конечная. Последняя карта. Или выход, или вечность в поезде».\n\n☠️ Этап: ФИНАЛ",
        "end_score_f": "{name} побеждает. Двери открываются. Вы выходите на рассветный перрон. Поезд исчезает.",
        "end_score_m": "{name} побеждает. Проводник: «Ты прошёл». Двери открываются. Вы свободны.",
        "end_brave_f": "{name} не пропустила ни карты. Проводник: «Я не видел такой смелости». Поезд останавливается.",
        "end_brave_m": "{name} не струсил. Проводник: «Редкий пассажир». Отпускает."
    }
]

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
    global player_scores, player_deck_stats, player_cards, all_player_cards, achievements, current_story
    decks = {name: cards[:] for name, cards in original_decks.items()}
    stats = {"газ": 0, "полный_газ": 0, "пиздец_газ": 0, "делай": 0}
    turn = 0
    skips = [0, 0]
    last_deck = None
    current_player = 0
    game_started = True
    player_scores = [0, 0]
    player_deck_stats = [{"газ": 0, "полный_газ": 0, "пиздец_газ": 0, "делай": 0}, {"газ": 0, "полный_газ": 0, "пиздец_газ": 0, "делай": 0}]
    player_cards = {"ебанутый": [[], []], "мегаебанутый": [[], []]}
    all_player_cards = [[], []]
    achievements = [set(), set()]
    current_story = random.choice(stories)

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

def get_stage():
    if turn < 50:
        return "Разогрев"
    elif turn < 75:
        return "Жара"
    elif turn < 100:
        return "Ад"
    else:
        return "Финал"

def stage_emoji():
    s = get_stage()
    if s == "Разогрев":
        return "🕊"
    elif s == "Жара":
        return "🔥"
    elif s == "Ад":
        return "💀"
    else:
        return "☠️"

def filter_cards_by_stage(deck_name):
    cards = decks[deck_name]
    stage = get_stage()
    if deck_name == "пиздец_газ" and stage == "Разогрев":
        return None
    if deck_name == "делай":
        if stage == "Разогрев":
            allowed = ["легкий"]
        elif stage == "Жара":
            allowed = ["легкий", "средний", "тяжелый", "ебанутый"]
        elif stage == "Ад":
            allowed = ["легкий", "средний", "тяжелый", "ебанутый", "мегаебанутый", "спец"]
        else:
            allowed = ["легкий", "средний", "тяжелый", "ебанутый", "мегаебанутый", "спец"]
        filtered = [c for c in cards if c.get("level") in allowed]
        return filtered if filtered else cards
    if deck_name == "полный_газ":
        if stage == "Разогрев":
            filtered = [c for c in cards if c.get("level") not in ("ебанутый", "мегаебанутый")]
        else:
            filtered = [c for c in cards if c.get("level") != "мегаебанутый"]
        return filtered if filtered else cards
    return cards

def pull_card(deck_name, is_arrow=False):
    global decks, stats, turn, current_player, last_deck, player_scores, player_deck_stats, player_cards, all_player_cards, achievements

    filtered = filter_cards_by_stage(deck_name)
    if filtered is None:
        return "❌ Пиздец газ ещё спит. Он откроется после 50 хода. Терпи 😉"
    if not filtered:
        reset_game()
        return "🃏 Колода была пуста и сброшена. Тяни снова."

    card = random.choice(filtered)
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
    player_deck_stats[player_idx][deck_name] += 1
    level = card.get("level", "")
    all_player_cards[player_idx].append(card["text"])

    if level == "ебанутый":
        player_cards["ебанутый"][player_idx].append(card["text"])
        if "первая_кровь" not in achievements[player_idx]:
            achievements[player_idx].add("первая_кровь")
    elif level == "мегаебанутый":
        player_cards["мегаебанутый"][player_idx].append(card["text"])
        if "первая_кровь" not in achievements[player_idx]:
            achievements[player_idx].add("первая_кровь")

    if len(player_cards["ебанутый"][player_idx]) + len(player_cards["мегаебанутый"][player_idx]) >= 10:
        achievements[player_idx].add("бесстрашный")

    card_type = card.get("type", "")
    if card_type == "brudershaft":
        prefix = random.choice(brudershaft_phrases) + "\n\n"
    else:
        prefix = ""

    response = f"{stage_emoji()} {deck_name.upper()} — ход {turn}\n"
    response += f"👤 Тянет: {player_names[player_idx]}\n\n"

    if level == "мегаебанутый":
        response += "👑 МЕГАЕБАНУТАЯ КАРТА! (7 баллов)\n\n"
    elif level == "ебанутый":
        response += "☠️ ЕБАНУТАЯ КАРТА! (5 баллов)\n\n"
    elif deck_name == "пиздец_газ":
        response += "⚠️ ВНИМАНИЕ! Карта из Пиздец газа!\n\n"

    response += prefix + card["text"]

    if card_type == "arrow":
        target = card["target"]
        response += f"\n\n➡️ Переход в «{target.upper()}»"
        if target == "рандом":
            if get_stage() == "Разогрев":
                target = random.choice(["газ", "полный_газ", "делай"])
            else:
                target = random.choice(["газ", "полный_газ", "пиздец_газ", "делай"])
            response += f"\n🎯 Выпало: «{target.upper()}»"
        response += "\n\n" + pull_card(target, is_arrow=True)

    if is_x2() and card_type != "arrow":
        response += "\n\n🔥 Х2! Карта для обоих!"

    if random.randint(1, 100) <= 7 and card_type != "arrow":
        player_scores[player_idx] += score
        response += f"\n\n🎰 ×2 БАЛЛОВ! +{score} дополнительно!"

    # Прогресс-бар каждые 20 ходов
    if turn % 20 == 0 and not is_arrow:
        stage = get_stage()
        next_stage = "Жара" if turn < 50 else "Ад" if turn < 75 else "Финал" if turn < 100 else "Конец"
        response += f"\n\n📊 Прогресс: {turn} ходов. Текущий этап: {stage}. Следующий: {next_stage}"

    # Чекпоинты
    if turn == 50 and current_story:
        response += f"\n\n{current_story['ch50']}"
    elif turn == 75 and current_story:
        response += f"\n\n{current_story['ch75']}"
    elif turn == 100 and current_story:
        response += f"\n\n{current_story['ch100']}"

    return response

def next_phrase(name, score):
    phrases = [
        f"{name} дал заднюю. −{score} балла.",
        f"Опа! {name} слился. −{score} балла.",
        f"{name} решил не отвечать. −{score} балла.",
        f"Страшно? {name} тоже так думает. −{score}.",
        f"{name} моргнул первым. −{score}.",
        f"Ой! {name} пропустил. −{score}.",
        f"{name} не готов. −{score}.",
        f"{name} ушёл в отказ. −{score}.",
        f"Пропуск. {name} теряет {score} балла.",
        f"{name}, смелость не твой конёк. −{score}."
    ]
    return random.choice(phrases)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hour = datetime.now().hour
    if hour < 6:
        greeting = "🌙 Доброй ночи"
    elif hour < 12:
        greeting = "☀️ Доброе утро"
    elif hour < 18:
        greeting = "🌤 Добрый день"
    elif hour < 22:
        greeting = "🌅 Добрый вечер"
    else:
        greeting = "🌙 Доброй ночи"
    await update.message.reply_text(f"{greeting}, смельчаки!\n\nВведите имя первой участницы:")
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
        story_text = current_story["start"] if current_story else ""
        await update.message.reply_text(
            f"{story_text}\n\n🕊 ЭТАП: РАЗОГРЕВ (ходы 1-49)\nПервый ход — {player_names[0]}.\nВыбирай колоду:",
            reply_markup=main_keyboard
        )
        return

    if not game_started:
        if text.upper() == "/START":
            await start(update, context)
            return
        await update.message.reply_text(welcome_text)
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
        if get_stage() == "Разогрев":
            deck = random.choice(["газ", "полный_газ", "делай"])
        else:
            deck = random.choice(["газ", "полный_газ", "пиздец_газ", "делай"])
        response = f"🎯 Рандом выбрал: «{deck.upper()}»\n\n" + pull_card(deck)
    elif text_upper in ("⏭ НЕКСТ", "НЕКСТ"):
        if last_deck:
            score = card_score({"deck": last_deck, "level": ""})
            player_scores[current_player] -= score
            skips[current_player] += 1
            if skips[current_player] >= 5:
                achievements[current_player].add("читер")
            if random.randint(1, 100) <= 40:
                response = next_phrase(player_names[current_player], score) + "\n\n"
            else:
                response = f"⏭ {player_names[current_player]} пропускает (−{score} балла).\n\n"
            response += pull_card(last_deck)
        else:
            response = "Сначала вытяни карту."
    elif text_upper in ("📋 КОМАНДЫ", "КОМАНДЫ"):
        response = "📋 /start /restart /stats /finish /vibe /rules /top /ping"
    elif text_upper in ("/RESTART",):
        reset_game()
        response = "🔄 Колоды сброшены!"
    elif text_upper in ("/STATS",):
        total = sum(stats.values())
        response = f"📊 Газ: {stats['газ']} | ПГ: {stats['полный_газ']} | Пиздец: {stats['пиздец_газ']} | Делай: {stats['делай']}\nВсего: {total}\nХод: {turn}"
    elif text_upper in ("/FINISH",):
        total = sum(stats.values())
        top_cards = []
        for i in range(2):
            all_eb = player_cards["ебанутый"][i] + player_cards["мегаебанутый"][i]
            if all_eb:
                top_cards.append(f"👤 {player_names[i]}:\n" + "\n".join(f"• {c}" for c in all_eb[:3]))
        top_text = "\n\n".join(top_cards) if top_cards else "Нет ебанутых карт."

        for i in range(2):
            if skips[i] == 0:
                achievements[i].add("непробиваемый")

        ach_text = []
        for i in range(2):
            a_list = []
            if "первая_кровь" in achievements[i]:
                a_list.append("🩸 Первая кровь")
            if "бесстрашный" in achievements[i]:
                a_list.append("💀 Бесстрашный")
            if "читер" in achievements[i]:
                a_list.append("⏭ Читер")
            if "непробиваемый" in achievements[i]:
                a_list.append("🛡 Непробиваемый")
            if a_list:
                ach_text.append(f"👤 {player_names[i]}: {', '.join(a_list)}")
        ach_str = "\n".join(ach_text) if ach_text else "Нет ачивок."

        winner_idx = 0 if player_scores[0] > player_scores[1] else 1 if player_scores[1] > player_scores[0] else -1
        brave_idx = 0 if skips[0] < skips[1] else 1 if skips[1] < skips[0] else -1

        winner = "Ничья!" if winner_idx == -1 else player_names[winner_idx]
        brave = "Ничья!" if brave_idx == -1 else player_names[brave_idx]
        gold = winner if winner != "Ничья!" else player_names[0]
        partner = player_names[1] if gold == player_names[0] else player_names[0]

        response = "🏁 ИГРА ЗАВЕРШЕНА!\n\n"
        response += f"🕊 Газ: {stats['газ']}\n🔥 Полный газ: {stats['полный_газ']}\n"
        response += f"💀 Пиздец газ: {stats['пиздец_газ']}\n🎬 Делай: {stats['делай']}\nВсего карт: {total}\n\n"

        for i in range(2):
            ds = player_deck_stats[i]
            response += f"👤 {player_names[i]}:\n"
            response += f"🕊 Газ: {ds['газ']} × 1 = {ds['газ'] * 1}\n"
            response += f"🔥 Полный газ: {ds['полный_газ']} × 3 = {ds['полный_газ'] * 3}\n"
            response += f"💀 Пиздец газ: {ds['пиздец_газ']} × 5 = {ds['пиздец_газ'] * 5}\n"
            response += f"🎬 Делай: {ds['делай']} × 3 = {ds['делай'] * 3}\n"
            response += f"⏭ Пропуски: {skips[i]}\n"
            response += f"📊 ИТОГО: {player_scores[i]} баллов\n\n"

        response += f"🏅 АЧИВКИ:\n{ach_str}\n\n"
        response += f"🔥 ТОП-3 ЖАРКИХ КАРТ:\n{top_text}\n\n"
        response += f"🏆 ПОБЕДИТЕЛЬ ПО БАЛЛАМ: {winner}\n"
        response += f"🥈 ПОБЕДИТЕЛЬ ПО СМЕЛОСТИ: {brave}\n\n"
        response += f"🃏 ЗОЛОТАЯ КАРТА уходит {gold}!\nОдин раз. Одно желание. Без отказа.\n\n"

        if current_story and winner_idx != -1:
            if winner_idx == 0:
                response += current_story.get("end_score_f", "").format(name=player_names[0], partner=player_names[1])
            else:
                response += current_story.get("end_score_m", "").format(name=player_names[1], partner=player_names[0])
        elif current_story and brave_idx != -1:
            if brave_idx == 0:
                response += current_story.get("end_brave_f", "").format(name=player_names[0], partner=player_names[1])
            else:
                response += current_story.get("end_brave_m", "").format(name=player_names[1], partner=player_names[0])

        response += "\n\nСпасибо за игру! /start — новая игра."
        reset_game()
    elif text_upper in ("/VIBE",):
        if current_story:
            response = random.choice(current_story["vibes"])
        else:
            response = "🌙 Атмосфера накаляется..."
    elif text_upper in ("/RULES",):
        response = "📜 🕊 Газ — лёгкие. 🔥 Полный газ — интим. 💀 Пиздец газ — стыд. 🎬 Делай — действия. Блокировки: Пиздец газ с 50, доминантные/мега с 75."
    elif text_upper in ("/TOP",):
        all_cards = all_player_cards[0] + all_player_cards[1]
        if len(all_cards) >= 5:
            top5 = random.sample(all_cards, 5)
            response = "🏆 ТОП-5 КАРТ:\n" + "\n".join(f"• {c}" for c in top5)
        elif all_cards:
            response = "🏆 КАРТЫ:\n" + "\n".join(f"• {c}" for c in all_cards)
        else:
            response = "🏆 Пока нет карт."
    elif text_upper in ("/PING",):
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
