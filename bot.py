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
user_channels = {} 
active_giveaways = {} 

# Inline-кнопка "Назад"
def get_back_button():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back_to_menu'))
    return markup

# Главное Inline-меню
def get_main_menu_inline():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('👤 Мой профиль', callback_data='my_profile'))
    markup.add(types.InlineKeyboardButton('🤖 Добавить бота в канал', callback_data='add_channel'))
    markup.add(types.InlineKeyboardButton('🎁 Создать розыгрыш', callback_data='create_giveaway'))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_states.pop(message.from_user.id, None)
    # Удаляем нижнюю клавиатуру, если она была
    msg = bot.send_message(message.chat.id, '👋 Привет! Я бот для создания розыгрышей.\n\nВыбери действие:', reply_markup=types.ReplyKeyboardRemove())
    # Отправляем inline-меню
    bot.send_message(message.chat.id, 'Главное меню:', reply_markup=get_main_menu_inline())

@bot.message_handler(content_types=['text', 'forwarded'])
def text_handler(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if isinstance(state, dict):
        # --- ДОБАВЛЕНИЕ БОТА В КАНАЛ ---
        if state.get('step') == 'waiting_for_add_channel':
            if message.forward_from_chat:
                channel_id = message.forward_from_chat.id
                channel_title = message.forward_from_chat.title
            else:
                try:
                    channel_id = int(message.text)
                    channel_title = f"Канал {channel_id}"
                except ValueError:
                    bot.send_message(message.chat.id, 'Это не похоже на ID. Перешли сообщение из канала или напиши число (например, -1001234567890).', reply_markup=get_back_button())
                    return
            
            try:
                test_msg = bot.send_message(channel_id, '✅ Бот успешно добавлен!')
                bot.delete_message(channel_id, test_msg.message_id)
                
                if user_id not in user_channels:
                    user_channels[user_id] = {}
                user_channels[user_id][channel_id] = channel_title
                
                bot.send_message(message.chat.id, f'✅ Канал "{channel_title}" успешно привязан!', reply_markup=get_main_menu_inline())
            except Exception:
                bot.send_message(message.chat.id, '❌ Ошибка. Убедись, что ты добавил меня в администраторы канала и дал право "Публикация сообщений".', reply_markup=get_back_button())
            
            del user_states[user_id]
            return

        # --- ШАГ 1: ТЕКСТ РОЗЫГРЫША ---
        elif state.get('step') == 'waiting_for_giveaway_text':
            state['text'] = message.text
            state['step'] = 'waiting_for_target_count'
            bot.send_message(message.chat.id, 'На сколько участников конкурс завершится? (напиши число)', reply_markup=get_back_button())
            return

        # --- ШАГ 2: КОЛИЧЕСТВО УЧАСТНИКОВ ---
        elif state.get('step') == 'waiting_for_target_count':
            try:
                state['target_count'] = int(message.text)
                state['step'] = 'waiting_for_winners_count'
                bot.send_message(message.chat.id, 'Сколько победителей будет? (напиши число)', reply_markup=get_back_button())
            except ValueError:
                bot.send_message(message.chat.id, 'Пожалуйста, введи число (например, 10).', reply_markup=get_back_button())
            return

        # --- ШАГ 3: КОЛИЧЕСТВО ПОБЕДИТЕЛЕЙ И ПОДТВЕРЖДЕНИЕ ---
        elif state.get('step') == 'waiting_for_winners_count':
            try:
                state['winners_count'] = int(message.text)
                
                preview_text = (
                    f"📢 **Предпросмотр конкурса**\n\n"
                    f"**Текст:** {state['text']}\n"
                    f"**Цель:** {state['target_count']} участников\n"
                    f"**Победителей:** {state['winners_count']}\n\n"
                    f"Вы уверены, что хотите опубликовать конкурс?"
                )
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton('✅ Да, опубликовать', callback_data='confirm_publish'))
                markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back_to_menu'))
                
                bot.send_message(message.chat.id, preview_text, reply_markup=markup, parse_mode='Markdown')
                state['step'] = 'waiting_for_confirm'
            except ValueError:
                bot.send_message(message.chat.id, 'Пожалуйста, введи число (например, 1).', reply_markup=get_back_button())
            return

    bot.send_message(message.chat.id, 'Я не понимаю. Напиши /start, чтобы открыть меню.', reply_markup=get_back_button())

# --- ОБРАБОТКА INLINE-КНОПОК ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    state = user_states.get(user_id)
    
    # --- ГЛАВНОЕ МЕНЮ ---
    if call.data == 'back_to_menu' or call.data == 'main_menu':
        user_states.pop(user_id, None)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, '👋 Главное меню:\nВыбери действие:', reply_markup=get_main_menu_inline())
        bot.answer_callback_query(call.id)
        return

    # --- МОЙ ПРОФИЛЬ ---
    elif call.data == 'my_profile':
        bot.edit_message_text(
            chat_id=call.message.chat.id, message_id=call.message.message_id,
            text=f'👤 **Твой профиль**\n\nИмя: {call.from_user.first_name}\nID: {call.from_user.id}',
            reply_markup=get_back_button(), parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)

    # --- ДОБАВИТЬ КАНАЛ ---
    elif call.data == 'add_channel':
        user_states[user_id] = {'step': 'waiting_for_add_channel'}
        bot.edit_message_text(
            chat_id=call.message.chat.id, message_id=call.message.message_id,
            text='Отправь ID твоего канала (например, -1001234567890) или перешли сюда сообщение из канала.\n\n⚠️ Важно: я должен быть админом в канале!',
            reply_markup=get_back_button()
        )
        bot.answer_callback_query(call.id)

    # --- СОЗДАТЬ РОЗЫГРЫШ ---
    elif call.data == 'create_giveaway':
        if user_id in user_channels and user_channels[user_id]:
            markup = types.InlineKeyboardMarkup()
            for ch_id, ch_title in user_channels[user_id].items():
                markup.add(types.InlineKeyboardButton(f'📢 {ch_title}', callback_data=f'select_ch_{ch_id}'))
            markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back_to_menu'))
            
            bot.edit_message_text(
                chat_id=call.message.chat.id, message_id=call.message.message_id,
                text='В каком канале хотите опубликовать конкурс?',
                reply_markup=markup
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id, message_id=call.message.message_id,
                text='❌ У тебя нет добавленных каналов. Сначала добавь меня в канал.',
                reply_markup=get_back_button()
            )
        bot.answer_callback_query(call.id)

    # --- ВЫБОР КАНАЛА ---
    elif call.data.startswith('select_ch_'):
        channel_id = int(call.data.split('_')[2])
        user_states[user_id] = {'step': 'waiting_for_giveaway_text', 'channel_id': channel_id}
        bot.edit_message_text(
            chat_id=call.message.chat.id, message_id=call.message.message_id,
            text='Какой будет текст вашего розыгрыша? (без видео, фото и т.д.)',
            reply_markup=get_back_button()
        )
        bot.answer_callback_query(call.id)

    # --- ПОДТВЕРЖДЕНИЕ ПУБЛИКАЦИИ ---
    elif call.data == 'confirm_publish':
        if state and state.get('step') == 'waiting_for_confirm':
            channel_id = state['channel_id']
            channel_title = user_channels[user_id].get(channel_id, "Канал")
            text = state['text']
            target = state['target_count']
            winners_count = state['winners_count']
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('✅ Участвовать', callback_data='join_giveaway'))
            
            try:
                sent_msg = bot.send_message(channel_id, f'{text}\n\n🎯 **Цель:** {target} участников\n🏆 **Победителей:** {winners_count}\n👥 **Сейчас:** 0\n\nНажми кнопку ниже, чтобы участвовать!', reply_markup=markup, parse_mode='Markdown')
                
                active_giveaways[sent_msg.message_id] = {
                    'participants': set(), 
                    'target_count': target,
                    'winners_count': winners_count,
                    'chat_id': channel_id, 
                    'creator_id': user_id, 
                    'text': text
                }
                
                finish_markup = types.InlineKeyboardMarkup()
                finish_markup.add(types.InlineKeyboardButton('🏁 Завершить досрочно', callback_data=f'finish_{sent_msg.message_id}'))
                bot.send_message(user_id, f'Твой розыгрыш в канале "{channel_title}" опубликован! Нажми кнопку ниже, чтобы завершить досрочно.', reply_markup=finish_markup)
                
                bot.edit_message_text(
                    chat_id=call.message.chat.id, message_id=call.message.message_id,
                    text='✅ Розыгрыш опубликован!',
                    reply_markup=get_main_menu_inline()
                )
            except Exception:
                bot.edit_message_text(
                    chat_id=call.message.chat.id, message_id=call.message.message_id,
                    text='❌ Ошибка при отправке. Убедись, что бот админ.',
                    reply_markup=get_back_button()
                )
            
            del user_states[user_id]
        bot.answer_callback_query(call.id)

    # --- УЧАСТИЕ С ПРОВЕРКОЙ ПОДПИСКИ ---
    elif call.data == 'join_giveaway':
        msg_id = call.message.message_id
        if msg_id in active_giveaways:
            giveaway = active_giveaways[msg_id]
            
            if user_id in giveaway['participants']:
                bot.answer_callback_query(call.id, "Ты уже участвуешь!", show_alert=True)
                return

            # --- ПРОВЕРКА ПОДПИСКИ НА КАНАЛ ---
            try:
                member = bot.get_chat_member(giveaway['chat_id'], user_id)
                if member.status in ['left', 'kicked']:
                    bot.answer_callback_query(
                        call.id, 
                        "❌ Ты не подписан на канал! Сначала подпишись, потом участвуй.", 
                        show_alert=True
                    )
                    return
            except Exception:
                pass # Если бот не админ, пропускаем проверку

            # Если проверка пройдена, добавляем
            giveaway['participants'].add(user_id)
            bot.answer_callback_query(call.id, "Ты успешно участвуешь! Удачи! 🍀")
            
            count = len(giveaway['participants'])
            target = giveaway['target_count']
            
            if count >= target:
                winners = random.sample(list(giveaway['participants']), min(giveaway['winners_count'], count))
                winners_text = ", ".join([f"[Пользователь](tg://user?id={w})" for w in winners])
                
                bot.edit_message_text(
                    chat_id=giveaway['chat_id'], message_id=msg_id,
                    text=f'{giveaway["text"]}\n\n🏆 **РОЗЫГРЫШ ЗАВЕРШЕН!**\n\n**Победители:**\n{winners_text}\n\nПоздравляем!',
                    parse_mode='Markdown', reply_markup=types.InlineKeyboardMarkup()
                )
                del active_giveaways[msg_id]
                try: bot.send_message(giveaway['creator_id'], f'Твой розыгрыш в канале завершился! Набралось {target} участников.')
                except: pass
            else:
                try:
                    bot.edit_message_text(
                        chat_id=call.message.chat.id, message_id=msg_id,
                        text=f'{giveaway["text"]}\n\n🎯 **Цель:** {target} участников\n🏆 **Победителей:** {giveaway["winners_count"]}\n👥 **Сейчас:** {count}\n\nНажми кнопку ниже, чтобы участвовать!',
                        reply_markup=call.message.reply_markup, parse_mode='Markdown'
                    )
                except: pass
                
    # --- ДОСРОЧНОЕ ЗАВЕРШЕНИЕ ---
    elif call.data.startswith('finish_'):
        msg_id = int(call.data.split('_')[1])
        if msg_id in active_giveaways:
            giveaway = active_giveaways[msg_id]
            if user_id != giveaway['creator_id']:
                bot.answer_callback_query(call.id, "Только создатель может завершить!", show_alert=True)
                return
            participants = list(giveaway['participants'])
            if not participants:
                bot.answer_callback_query(call.id, "Никто не участвовал!", show_alert=True)
                return
                
            winners = random.sample(participants, min(giveaway['winners_count'], len(participants)))
            winners_text = ", ".join([f"[Пользователь](tg://user?id={w})" for w in winners])
            
            try:
                bot.edit_message_text(
                    chat_id=giveaway['chat_id'], message_id=msg_id,
                    text=f'{giveaway["text"]}\n\n🏆 **РОЗЫГРЫШ ЗАВЕРШЕН ДОСРОЧНО!**\n\n**Победители:**\n{winners_text}\n\nПоздравляем!',
                    parse_mode='Markdown', reply_markup=types.InlineKeyboardMarkup()
                )
                bot.answer_callback_query(call.id, "Розыгрыш завершен!")
                bot.delete_message(call.message.chat.id, call.message.message_id)
                bot.send_message(call.message.chat.id, 'Возвращаемся в меню:', reply_markup=get_main_menu_inline())
                del active_giveaways[msg_id]
            except Exception:
                bot.answer_callback_query(call.id, "Ошибка. Возможно, сообщение удалено.")

# Фейковый сервер для Render (чтобы не было ошибок с портами)
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
