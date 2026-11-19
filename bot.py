import telebot
from telebot import types

TOKEN = '9132199477:AAHWEDC5PMJlK2NGF7g8ct2GizRFvx31SL8'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('👤 Мой профиль')
    btn2 = types.KeyboardButton('⚙️ Настройки')
    btn3 = types.KeyboardButton('⭐ Купить звезды')
    markup.add(btn1, btn2, btn3)
    bot.send_message(message.chat.id, 'Привет! Выбери действие в меню ниже:', reply_markup=markup)

@bot.message_handler(content_types=['text'])
def text_handler(message):
    if message.text == '👤 Мой профиль':
        bot.send_message(message.chat.id, f'Твое имя: {message.from_user.first_name}\nТвой ID: {message.chat.id}')
    elif message.text == '⚙️ Настройки':
        bot.send_message(message.chat.id, 'Тут будут настройки твоего аккаунта.')
    elif message.text == '⭐ Купить звезды':
        bot.send_message(message.chat.id, 'Обратитесь к @xorey_big')
    else:
        bot.send_message(message.chat.id, 'Я не знаю такой команды. Нажми /start, чтобы открыть меню.')

print("Бот запущен!")
bot.infinity_polling()
