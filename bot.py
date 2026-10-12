import telebot                      # библиотека pyTelegramBotAPI
from telebot import types           # типы для кнопок/клавиатур
import random                       # случайные числа
import os                           # чтение env + проверка файлов

TOKEN = os.environ.get("BOT_TOKEN")                 # токен ТОЛЬКО из переменной окружения (не из кода!)
if not TOKEN:                                       # если env не задан
    raise SystemExit("ERROR: не задана переменная окружения BOT_TOKEN")  # падаем сразу с ясной причиной

bot = telebot.TeleBot(TOKEN)         # объект бота (синхронный polling)

DICE_IMG  = "dice.png"               # имя файла кубиков (поменяй, если у тебя другое расширение)
COIN_IMG  = "coin.png"               # имя файла монеты
START_IMG = "coin_dice.png"          # имя файла приветствия

kb = types.InlineKeyboardMarkup(row_width=2)                                  # клавиатура: 2 кнопки в ряд
kb.add(
    types.InlineKeyboardButton("🎲 Кубик",  callback_data="roll"),            # кнопка -> callback "roll"
    types.InlineKeyboardButton("🪙 Монета", callback_data="coin"),            # кнопка -> callback "coin"
)

def send_media(chat_id, filename, caption):         # единая отправка: картинка+подпись, иначе только текст
    try:                                            # защищаемся от битого файла / ошибки загрузки
        if os.path.exists(filename):                # файл на месте?
            with open(filename, "rb") as f:         # открываем в бинарном режиме
                bot.send_photo(chat_id, f, caption=caption)  # шлём фото
            return                                  # успех -> выходим
    except Exception:                               # любая ошибка upload
        pass                                        # игнорируем, уходим в текстовый fallback
    bot.send_message(chat_id, caption)              # запасной вариант: только текст

@bot.message_handler(commands=["start"])            # команда /start
def cmd_start(message):
    name = message.from_user.first_name if message.from_user else "друг"  # имя или заглушка
    send_media(message.chat.id, START_IMG, "Привет, {0}! Жми кнопку или /roll /coin".format(name))
    bot.send_message(message.chat.id, "Выбери действие:", reply_markup=kb)  # сообщение с кнопками

@bot.message_handler(commands=["roll"])             # команда /roll
def cmd_roll(message):
    n = random.randint(1, 6)                        # 1..6 включительно
    send_media(message.chat.id, DICE_IMG, "🎲 Выпало: {0}".format(n))

@bot.message_handler(commands=["coin"])             # команда /coin
def cmd_coin(message):
    side = random.choice(["Орёл", "Решка"])         # случайная сторона
    send_media(message.chat.id, COIN_IMG, "🪙 Выпало: {0}".format(side))

@bot.callback_query_handler(func=lambda c: True)    # любой клик по inline-кнопке
def on_callback(call):
    bot.answer_callback_query(call.id)              # ack Telegram (иначе часы крутятся вечно)
    if call.message is None:                        # edge case: нет исходного сообщения
        return
    cid = call.message.chat.id                      # чат, куда отвечать
    if call.data == "roll":                         # нажали «Кубик»
        send_media(cid, DICE_IMG, "🎲 Выпало: {0}".format(random.randint(1, 6)))
    elif call.data == "coin":                       # нажали «Монета»
        send_media(cid, COIN_IMG, "🪙 Выпало: {0}".format(random.choice(["Орёл", "Решка"])))

print("Bot started...")             # лог в консоль Render (вкладка Logs)
bot.infinity_polling()              # вечный polling на верхнем уровне, без if __name__