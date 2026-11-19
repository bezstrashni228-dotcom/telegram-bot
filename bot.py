import telebot
from telebot import types
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

TOKEN = '9132199477:AAF2OR95y3cE4K0vBn0KMx0KmtkIsHO_EYE' 
ADMIN_ID = 8679581943 

bot = telebot.TeleBot(TOKEN)

# Обработка команды /start
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('👤 Мой профиль')
    btn2 = types.KeyboardButton('⚙️ Настройки')
    btn3 = types.KeyboardButton('⭐ Купить звезды')
    markup.add(btn1, btn2, btn3)
    
    # Если пишет админ, добавляем кнопку
    if message.from_user.id == ADMIN_ID:
        btn4 = types.KeyboardButton('👑 Админ-панель')
        markup.add(btn4)
        bot.send_message(message.chat.id, 'Привет, Босс! Выбери действие:', reply_markup=markup)
    else:
        bot.send_message(message.chat.id, 'Привет! Выбери действие в меню ниже:', reply_markup=markup)

# Обработка кнопок
@bot.message_handler(content_types=['text'])
def text_handler(message):
    if message.text == '👤 Мой профиль':
        bot.send_message(message.chat.id, f'Твое имя: {message.from_user.first_name}\nТвой ID: {message.chat.id}')
    elif message.text == '⚙️ Настройки':
        bot.send_message(message.chat.id, 'Тут будут настройки твоего аккаунта.')
    elif message.text == '⭐ Купить звезды':
        bot.send_message(message.chat.id, 'Обратитесь к @xorey_big')
    elif message.text == '👑 Админ-панель' and message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, f'Добро пожаловать в админку!\nТвой ID: {message.from_user.id}\nВсего пользователей: [пока не считаем]')
    else:
        bot.send_message(message.chat.id, 'Я не знаю такой команды. Нажми /start, чтобы открыть меню.')

# Фейковый веб-сервер для Render
def run_dummy_server():
    class DummyHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running")
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

print("Бот запущен!")
bot.infinity_polling()
