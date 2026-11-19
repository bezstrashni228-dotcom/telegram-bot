import telebot
from telebot import types
import random
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

TOKEN = '9132199477:AAERWdgbEEotj2Hx0qcJadx604lGZFv3CqQ' 
ADMIN_ID = 8679581943 

bot = telebot.TeleBot(TOKEN)

user_states = {}
active_giveaways = {} 

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('👤 Мой профиль')
    btn2 = types.KeyboardButton('🎲 Рандомайзер')
    btn3 = types.KeyboardButton('🎁 Создать розыгрыш')
    btn4 = types.KeyboardButton('📢 Розыгрыш в канале')
    markup.add(btn1, btn2, btn3, btn4)
    
    if message.from_user.id == ADMIN_ID:
        btn5 = types.KeyboardButton('👑 Админ-панель')
        markup.add(btn5)
        
    bot.send_message(message.chat.id, 'Привет! Выбери действие в меню ниже:', reply_markup=markup)

# Главный обработчик текста
@bot.message_handler(content_types=['text', 'forwarded'])
def text_handler(message):
    user_id = message.from_user.id

    # --- ЕСЛИ МЫ ЖДЕМ ID КАНАЛА (обрабатываем это здесь) ---
    if isinstance(user_states.get(user_id), dict) and user_states[user_id].get('step') == 'waiting_for_channel_id':
        if message.forward_from_chat:
            channel_id = message.forward_from_chat.id
        else:
            try:
                channel_id = int(message.text) 
            except ValueError:
                bot.send_message(message.chat.id, 'Это не похоже на ID канала. Попробуй переслать сообщение из канала.')
                return
                
        user_states[user_id]['channel_id'] = channel_id
        user_states[user_id]['step'] = 'waiting_for_channel_prize'
        bot.send_message(message.chat.id, 'Канал добавлен! Теперь введи название приза.')
        return # <--- Важно! Прерываем выполнение, чтобы не сработали другие кнопки

    # --- ЕСЛИ МЫ ЖДЕМ ПРИЗ ДЛЯ КАНАЛА ---
    elif isinstance(user_states.get(user_id), dict) and user_states[user_id].get('step') == 'waiting_for_channel_prize':
        user_states[user_id]['prize'] = message.text
        user_states[user_id]['step'] = 'waiting_for_channel_count'
        bot.send_message(message.chat.id, 'Сколько победителей будет? (напиши число)')
        return

    # --- ЕСЛИ МЫ ЖДЕМ КОЛИЧЕСТВО ПОБЕДИТЕЛЕЙ ДЛЯ КАНАЛА ---
    elif isinstance(user_states.get(user_id), dict) and user_states[user_id].get('step') == 'waiting_for_channel_count':
        try:
            winner_count = int(message.text)
            prize = user_states[user_id]['prize']
            channel_id = user_states[user_id]['channel_id']
            
            markup = types.InlineKeyboardMarkup()
            btn_join = types.InlineKeyboardButton('✅ Участвовать', callback_data='join_giveaway')
            btn_finish = types.InlineKeyboardButton('🏁 Завершить', callback_data='finish_giveaway')
            markup.add(btn_join)
            markup.add(btn_finish)
            
            try:
                sent_msg = bot.send_message(channel_id, f'🎁 **РОЗЫГРЫШ!**\n\nПриз: {prize}\nПобедителей: {winner_count}\nУчастников: 0\n\nНажми кнопку ниже, чтобы участвовать!', reply_markup=markup, parse_mode='Markdown')
                
                active_giveaways[sent_msg.message_id] = {
                    'participants': set(), 
                    'winner_count': winner_count, 
                    'chat_id': channel_id, 
                    'creator_id': user_id, 
                    'prize': prize
                }
                bot.send_message(message.chat.id, 'Розыгрыш успешно опубликован в канале!')
            except Exception as e:
                bot.send_message(message.chat.id, '❌ Я не могу писать в этот канал.\n\nПожалуйста, добавь меня в администраторы канала и дай право "Публикация сообщений"!')
            
            del user_states[user_id]
        except ValueError:
            bot.send_message(message.chat.id, 'Пожалуйста, введи число (например, 1).')
        return

    # --- РАНДОМАЙЗЕР ---
    if message.text == '🎲 Рандомайзер':
        user_states[user_id] = 'waiting_for_list'
        bot.send_message(message.chat.id, 'Отправь мне список вариантов через запятую.')
    elif user_states.get(user_id) == 'waiting_for_list':
        items = [item.strip() for item in message.text.replace('\n', ',').split(',') if item.strip()]
        if len(items) < 2:
            bot.send_message(message.chat.id, 'Нужно хотя бы два варианта!')
        else:
            winner = random.choice(items)
            bot.send_message(message.chat.id, f'🎲 Мой выбор: **{winner}**!', parse_mode='Markdown')
        del user_states[user_id]

    # --- СОЗДАНИЕ РОЗЫГРЫША (В БОТЕ) ---
    elif message.text == '🎁 Создать розыгрыш':
        user_states[user_id] = {'step': 'waiting_for_prize'}
        bot.send_message(message.chat.id, 'Введи название приза (например, "100 рублей").')

    elif isinstance(user_states.get(user_id), dict) and user_states[user_id].get('step') == 'waiting_for_prize':
        user_states[user_id]['prize'] = message.text
        user_states[user_id]['step'] = 'waiting_for_count'
        bot.send_message(message.chat.id, 'Отлично! Сколько победителей будет? (напиши число, например, 1)')

    elif isinstance(user_states.get(user_id), dict) and user_states[user_id].get('step') == 'waiting_for_count':
        try:
            winner_count = int(message.text)
            prize = user_states[user_id]['prize']
            
            markup = types.InlineKeyboardMarkup()
            btn_join = types.InlineKeyboardButton('✅ Участвовать', callback_data='join_giveaway')
            btn_finish = types.InlineKeyboardButton('🏁 Завершить', callback_data='finish_giveaway')
            markup.add(btn_join)
            markup.add(btn_finish)
            
            sent_msg = bot.send_message(message.chat.id, f'🎁 **РОЗЫГРЫШ!**\n\nПриз: {prize}\nПобедителей: {winner_count}\nУчастников: 0\n\nНажми кнопку ниже, чтобы участвовать!', reply_markup=markup, parse_mode='Markdown')
            
            active_giveaways[sent_msg.message_id] = {
                'participants': set(), 
                'winner_count': winner_count, 
                'chat_id': message.chat.id,
                'creator_id': user_id, 
                'prize': prize
            }
            
            del user_states[user_id]
        except ValueError:
            bot.send_message(message.chat.id, 'Пожалуйста, введи число (например, 1).')

    # --- РОЗЫГРЫШ В КАНАЛЕ (ЗАПУСК) ---
    elif message.text == '📢 Розыгрыш в канале':
        user_states[user_id] = {'step': 'waiting_for_channel_id'}
        bot.send_message(message.chat.id, 'Отправь ID твоего канала (например, -1001234567890) или перешли сюда сообщение из канала.\n\n⚠️ Важно: я должен быть админом в канале с правом публикации!')

    # --- АДМИН-ПАНЕЛЬ ---
    elif message.text == '👑 Админ-панель' and user_id == ADMIN_ID:
        bot.send_message(message.chat.id, 'Тут ты можешь управлять ботом.')

    # --- ОСТАЛЬНЫЕ КНОПКИ ---
    elif message.text == '👤 Мой профиль':
        bot.send_message(message.chat.id, f'Твое имя: {message.from_user.first_name}\nТвой ID: {message.chat.id}')
    else:
        bot.send_message(message.chat.id, 'Я не знаю такой команды. Нажми /start.')

# --- ОБРАБОТКА INLINE-КНОПОК (БЕЗ ИЗМЕНЕНИЙ) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    msg_id = call.message.message_id
    
    if call.data == 'join_giveaway':
        if msg_id in active_giveaways:
            giveaway = active_giveaways[msg_id]
            user_id = call.from_user.id
            
            if user_id in giveaway['participants']:
                bot.answer_callback_query(call.id, "Ты уже участвуешь!", show_alert=True)
            else:
                giveaway['participants'].add(user_id)
                bot.answer_callback_query(call.id, "Ты успешно участвуешь! Удачи! 🍀")
                
                count = len(giveaway['participants'])
                try:
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=msg_id,
                        text=f'🎁 **РОЗЫГРЫШ!**\n\nПриз: {giveaway["prize"]}\nПобедителей: {giveaway["winner_count"]}\nУчастников: {count}\n\nНажми кнопку ниже, чтобы участвовать!',
                        reply_markup=call.message.reply_markup,
                        parse_mode='Markdown'
                    )
                except:
                    pass

    elif call.data == 'finish_giveaway':
        if msg_id in active_giveaways:
            giveaway = active_giveaways[msg_id]
            
            if call.from_user.id != giveaway['creator_id']:
                bot.answer_callback_query(call.id, "Только создатель розыгрыша может его завершить!", show_alert=True)
                return

            participants = list(giveaway['participants'])
            
            if not participants:
                bot.answer_callback_query(call.id, "Никто не участвовал в розыгрыше!", show_alert=True)
                return
                
            winner_count = min(giveaway['winner_count'], len(participants))
            winners = random.sample(participants, winner_count)
            
            winners_text = ", ".join([f"[Пользователь](tg://user?id={w})" for w in winners])
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=msg_id,
                text=f'🎁 **РОЗЫГРЫШ ЗАВЕРШЕН!**\n\nПриз: {giveaway["prize"]}\n\n🏆 **Победители:**\n{winners_text}\n\nПоздравляем!',
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup()
            )
            
            del active_giveaways[msg_id]

# Фейковый сервер для Render
def run_dummy_server():
    class DummyHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running")
        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

print("Бот запущен!")
bot.infinity_polling()
