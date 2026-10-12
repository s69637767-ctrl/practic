import telebot                      # pyTelegramBotAPI
from telebot import types           # типы: Update, клавиатуры
import random                       # случайные числа
import os                           # env-переменные + проверка файлов
import json                         # разбор тела POST-запроса от Telegram
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # мини-веб-сервер (stdlib, без flask)

TOKEN = os.environ.get("BOT_TOKEN")                 # токен ТОЛЬКО из env (секрет не коммитим)
if not TOKEN:                                       # если env не задан
    raise SystemExit("ERROR: не задана BOT_TOKEN")  # падаем сразу с ясной причиной

bot = telebot.TeleBot(TOKEN)         # объект бота

DICE_IMG  = "dice.png"               # файл кубиков (поменяй расширение, если нужно)
COIN_IMG  = "coin.png"               # файл монеты
START_IMG = "coin_dice.png"          # файл приветствия

kb = types.InlineKeyboardMarkup(row_width=2)                                  # 2 кнопки в ряд
kb.add(
    types.InlineKeyboardButton("🎲 Кубик",  callback_data="roll"),            # клик -> "roll"
    types.InlineKeyboardButton("🪙 Монета", callback_data="coin"),            # клик -> "coin"
)

def send_media(chat_id, filename, caption):         # картинка+подпись, иначе только текст
    try:                                            # защищаемся от битого/отсутствующего файла
        if os.path.exists(filename):                # файл на месте?
            with open(filename, "rb") as f:         # читаем в бинарном режиме
                bot.send_photo(chat_id, f, caption=caption)  # шлём фото
            return                                  # успех -> выход
    except Exception:                               # любая ошибка upload
        pass                                        # уходим в текстовый fallback
    bot.send_message(chat_id, caption)              # запасной вариант: только текст

@bot.message_handler(commands=["start"])            # /start
def cmd_start(message):
    name = message.from_user.first_name if message.from_user else "друг"  # имя или заглушка
    send_media(message.chat.id, START_IMG, "Привет, {0}! Жми кнопку или /roll /coin".format(name))
    bot.send_message(message.chat.id, "Выбери действие:", reply_markup=kb)  # сообщение с кнопками

@bot.message_handler(commands=["roll"])             # /roll
def cmd_roll(message):
    n = random.randint(1, 6)                        # 1..6 включительно
    send_media(message.chat.id, DICE_IMG, "🎲 Выпало: {0}".format(n))

@bot.message_handler(commands=["coin"])             # /coin
def cmd_coin(message):
    side = random.choice(["Орёл", "Решка"])         # случайная сторона
    send_media(message.chat.id, COIN_IMG, "🪙 Выпало: {0}".format(side))

@bot.callback_query_handler(func=lambda c: True)    # любой клик по inline-кнопке
def on_callback(call):
    bot.answer_callback_query(call.id)              # ack Telegram (иначе часы крутятся вечно)
    if call.message is None:                        # edge case: нет исходного сообщения
        return
    cid = call.message.chat.id                      # чат для ответа
    if call.data == "roll":                         # нажали «Кубик»
        send_media(cid, DICE_IMG, "🎲 Выпало: {0}".format(random.randint(1, 6)))
    elif call.data == "coin":                       # нажали «Монета»
        send_media(cid, COIN_IMG, "🪙 Выпало: {0}".format(random.choice(["Орёл", "Решка"])))

# ---------- webhook-обвязка (заменяет polling) ----------
PORT   = int(os.environ.get("PORT", 10000))         # порт выдаёт Render (обычно 10000)
W_URL  = os.environ.get("WEBHOOK_URL")              # публичный URL вида https://practic.onrender.com/webhook
W_SEC  = os.environ.get("WEBHOOK_SECRET")           # секрет против поддельных POST (slug угадуем!)

if W_URL:                                           # если URL задан -> регистрируем webhook у Telegram
    bot.set_webhook(url=W_URL, secret_token=W_SEC or None)  # Telegram начнёт слать POST на этот URL

class Handler(BaseHTTPRequestHandler):              # обработчик HTTP-запросов
    def log_message(self, fmt, *args):              # глушим спам access-логов в stdout
        pass                                        # (Render и так пишет свои логи)

    def do_GET(self):                               # GET = health-check / проверка в браузере
        self.send_response(200)                     # всегда 200, чтобы Render считал сервис живым
        self.end_headers()                          # завершаем заголовки
        self.wfile.write(b"ok")                     # тело-заглушка

    def do_POST(self):                              # POST = апдейты от Telegram
        if self.path != "/webhook":                 # принимаем только на /webhook
            self.send_response(404); self.end_headers(); return  # остальное режем
        if W_SEC and self.headers.get("X-Telegram-Bot-Api-Secret-Token") != W_SEC:  # проверка секрета
            self.send_response(401); self.end_headers(); return  # чужие запросы отбиваем
        length = int(self.headers.get("Content-Length", 0))      # сколько байт тела
        raw    = self.rfile.read(length)            # читаем тело запроса
        try:                                        # защищаем сервер от падения внутри хендлера
            update = types.Update.de_json(json.loads(raw))       # парсим JSON в объект Update
            bot.process_new_updates([update])     # прогоняем через наши @...handler'ы
        except Exception as e:                      # любая ошибка обработки апдейта
            print("WEBHOOK ERROR:", repr(e))       # пишем в Render-логи для отладки
        self.send_response(200)                     # отвечаем 200, чтобы Telegram не ретраил бесконечно
        self.end_headers()                          # завершаем заголовки

print("Bot started, listening on", PORT)           # лог о старте (видно в Render Logs)
ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()  # веб-сервер в главном потоке, хост 0.0.0.0 обязателен для Render