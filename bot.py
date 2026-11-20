import telebot
from telebot import types
import random
import os
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

TOKEN = '9132199477:AAERWdgbEEotj2Hx0qcJadx604lGZFv3CqQ'
ADMIN_ID = 8679581943

bot = telebot.TeleBot(TOKEN)
BOT_USERNAME = bot.get_me().username

user_states = {}
user_channels = {}
active_giveaways = {}

def get_back_button():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
    return markup

def get_main_menu_inline():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('👾 Мой профиль', callback_data='my_profile'))
    markup.add(types.InlineKeyboardButton('🔗 Добавить канал', callback_data='add_channel'))
    markup.add(types.InlineKeyboardButton('⚡️ Создать розыгрыш', callback_data='create_giveaway'))
    return markup

def show_channels(chat_id, user_id, message_id=None):
    if user_id in user_channels and user_channels[user_id]:
        markup = types.InlineKeyboardMarkup()
        for ch_id, ch_title in user_channels[user_id].items():
            markup.add(types.InlineKeyboardButton(f'📡 {ch_title}', callback_data=f'select_ch_{ch_id}'))
        markup.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
        
        if message_id:
            try:
                bot.edit_message_text(chat_id=chat_id, message_id=message_id, text='В каком канале хотите опубликовать конкурс?', reply_markup=markup)
            except Exception:
                pass
        else:
            bot.send_message(chat_id, 'В каком канале хотите опубликовать конкурс?', reply_markup=markup)
    else:
        text = '❌ У тебя нет добавленных каналов. Сначала добавь меня в канал.'
        if message_id:
            try:
                bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=get_back_button())
            except Exception:
                pass
        else:
            bot.send_message(chat_id, text, reply_markup=get_back_button())

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user_states.pop(user_id, None)
    welcome_text = (
        "©️ Главное меню:\n\n"
        "❗ Важно, если ты впервые в нашем боте, то не забудь добавить канал 🖊️\n\n"
        "Выбери действие:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=types.ReplyKeyboardRemove())
    bot.send_message(message.chat.id, '⚙️ Меню:', reply_markup=get_main_menu_inline())

@bot.message_handler(commands=['create'])
def cmd_create(message):
    user_id = message.from_user.id
    user_states.pop(user_id, None)
    show_channels(message.chat.id, user_id)
@bot.message_handler(content_types=['text', 'forwarded'])
def text_handler(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if isinstance(state, dict):
        if state.get('step') == 'waiting_for_add_channel':
            if message.forward_from_chat:
                channel_id = message.forward_from_chat.id
                channel_title = message.forward_from_chat.title
            else:
                try:
                    channel_id = int(message.text)
                    channel_title = f"Канал {channel_id}"
                except ValueError:
                    bot.send_message(message.chat.id, '❌ Это не похоже на ID. Перешли сообщение из канала или напиши число.', reply_markup=get_back_button())
                    return
            
            try:
                test_msg = bot.send_message(channel_id, '✅ Бот успешно добавлен!')
                bot.delete_message(channel_id, test_msg.message_id)
                
                if user_id not in user_channels:
                    user_channels[user_id] = {}
                user_channels[user_id][channel_id] = channel_title
                
                bot.send_message(message.chat.id, f'✅ Канал "{channel_title}" успешно привязан!', reply_markup=get_main_menu_inline())
            except Exception as e:
                bot.send_message(message.chat.id, f'❌ Ошибка привязки ({e}). Убедись, что я админ в канале.', reply_markup=get_back_button())
            
            del user_states[user_id]
            return

        elif state.get('step') == 'waiting_for_giveaway_text':
            state['text'] = message.text
            state['step'] = 'waiting_for_required_channels'
            state['required_channels'] = {state['channel_id']}
            
            text = (
                f"➕Добавьте каналы, на которые пользователям нужно будет подписаться для участия в розыгрыше.\n\n"
                f"❗️Подписка на канал, в котором проводится розыгрыш, обязательна и включена по умолчанию.\n\n"
                f"Чтобы добавить канал, нужно:\n"
                f"1. Добавить бота @{BOT_USERNAME} в этот канал как администратора - это нужно, чтобы бот мог проверить подписан ли пользователь на канал.\n"
                f"2. Отправить боту канал в формате @юзернеймканала или переслать сообщение из этого канала.\n\n"
                f"💬 Если Вы хотите чтобы участвовать в розыгрыше можно было без подписок на другие каналы, нажмите кнопку ниже:"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('📢 Без обязательных подписок', callback_data='no_required_subs'))
            markup.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
            
            bot.send_message(message.chat.id, text, reply_markup=markup)
            return

        elif state.get('step') == 'waiting_for_required_channels':
            channel_id = None
            if message.forward_from_chat:
                channel_id = message.forward_from_chat.id
            elif message.text and message.text.startswith('@'):
                try:
                    chat = bot.get_chat(message.text)
                    channel_id = chat.id
                except Exception:
                    bot.send_message(message.chat.id, '❌ Не удалось найти канал по этому юзернейму. Проверьте правильность.')
                    return
            
            if channel_id:
                try:
                    bot_member = bot.get_chat_member(channel_id, bot.get_me().id)
                    if bot_member.status not in ['administrator', 'creator']:
                        bot.send_message(message.chat.id, '❌ Проверьте бота в администрации!')
                        return
                except Exception:
                    bot.send_message(message.chat.id, '❌ Проверьте бота в администрации!')
                    return

                state['required_channels'].add(channel_id)
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton('Продолжить настройку ➡️', callback_data='no_required_subs'))
                markup.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
                
                msg_text = '✅ Канал добавлен!\n\nЕщё каналы? ➕ Отправьте @юзернейм или перешлите пост, либо нажмите кнопку ниже 👇'
                bot.send_message(message.chat.id, msg_text, reply_markup=markup)
            else:
                bot.send_message(message.chat.id, '❌ Отправьте юзернейм канала (@channel) или перешлите сообщение.')
            return

        elif state.get('step') == 'waiting_for_target_count':
            try:
                state['target_count'] = int(message.text)
                state['step'] = 'waiting_for_winners_count'
                bot.send_message(message.chat.id, '🏆 Сколько победителей будет? (напиши число)', reply_markup=get_back_button())
            except ValueError:
                bot.send_message(message.chat.id, '❌ Пожалуйста, введи число (например, 10).', reply_markup=get_back_button())
            return

        elif state.get('step') == 'waiting_for_winners_count':
            try:
                state['winners_count'] = int(message.text)
                extra_channels_count = max(0, len(state.get('required_channels', [])) - 1)
                safe_text = html.escape(state['text'])
                
                preview_text = (
                    f"📢 <b>Предпросмотр конкурса</b>\n\n"
                    f"<b>Текст:</b> {safe_text}\n"
                    f"<b>Цель:</b> {state['target_count']} участников\n"
                    f"<b>Победителей:</b> {state['winners_count']}\n"
                    f"<b>Доп. обязательных каналов:</b> {extra_channels_count}\n\n"
                    f"Вы уверены, что хотите опубликовать конкурс?"
                )
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton('🚀 Да, опубликовать', callback_data='confirm_publish'))
                markup.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
                
                bot.send_message(message.chat.id, preview_text, reply_markup=markup, parse_mode='HTML')
                state['step'] = 'waiting_for_confirm'
            except ValueError:
                bot.send_message(message.chat.id, '❌ Пожалуйста, введи число (например, 1).', reply_markup=get_back_button())
            return

    bot.send_message(message.chat.id, '🤖 Я не понимаю. Напиши /start, чтобы открыть меню.', reply_markup=get_back_button())
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    state = user_states.get(user_id)
    
    if call.data == 'back_to_menu' or call.data == 'main_menu':
        user_states.pop(user_id, None)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(call.message.chat.id, '⚙️ Главное меню:\nВыбери действие:', reply_markup=get_main_menu_inline())
        bot.answer_callback_query(call.id)
        return

    elif call.data == 'my_profile':
        safe_name = html.escape(call.from_user.first_name or "Пользователь")
        bot.edit_message_text(
            chat_id=call.message.chat.id, message_id=call.message.message_id,
            text=f'👾 <b>Твой профиль</b>\n\nИмя: {safe_name}\nID: {call.from_user.id}',
            reply_markup=get_back_button(), parse_mode='HTML'
        )
        bot.answer_callback_query(call.id)

    elif call.data == 'add_channel':
        user_states[user_id] = {'step': 'waiting_for_add_channel'}
        bot.edit_message_text(
            chat_id=call.message.chat.id, message_id=call.message.message_id,
            text='🔗 Отправь ID твоего канала (например, -1001234567890) или перешли сюда сообщение из канала.\n\n⚠️ Важно: я должен быть админом в канале!',
            reply_markup=get_back_button()
        )
        bot.answer_callback_query(call.id)

    elif call.data == 'create_giveaway':
        user_states.pop(user_id, None)
        show_channels(call.message.chat.id, user_id, call.message.message_id)
        bot.answer_callback_query(call.id)

    elif call.data.startswith('select_ch_'):
        channel_id = int(call.data.replace('select_ch_', ''))
        user_states[user_id] = {'step': 'waiting_for_giveaway_text', 'channel_id': channel_id, 'required_channels': {channel_id}}
        bot.edit_message_text(
            chat_id=call.message.chat.id, message_id=call.message.message_id,
            text=(
                f"⚡️ Создание розыгрыша:\n\n"
                f"✉️ Отправьте текст для розыгрыша.\n\n"
                f"Бот полностью бесплатный. Будет приятно, если в посте укажете ссылку: @{BOT_USERNAME}"
            ),
            reply_markup=get_back_button()
        )
        bot.answer_callback_query(call.id)

    elif call.data == 'no_required_subs':
        if state and state.get('step') == 'waiting_for_required_channels':
            state['step'] = 'waiting_for_target_count'
            bot.edit_message_text(
                chat_id=call.message.chat.id, message_id=call.message.message_id,
                text='🎯 На сколько участников конкурс завершится? (напиши число)',
                reply_markup=get_back_button()
            )
        bot.answer_callback_query(call.id)

    elif call.data == 'confirm_publish':
        if state and state.get('step') == 'waiting_for_confirm':
            channel_id = state['channel_id']
            channel_title = user_channels[user_id].get(channel_id, "Канал")
            raw_text = state['text']
            safe_text = html.escape(raw_text)
            target = state['target_count']
            winners_count = state['winners_count']
            required_channels = list(state.get('required_channels', []))
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('🎮 Участвовать (0)', callback_data='join_giveaway'))
            
            post_body = (
                f"{safe_text}\n\n"
                f"🎯 <b>Цель:</b> {target} участников\n"
                f"🏆 <b>Победителей:</b> {winners_count}\n"
                f"👥 <b>Сейчас:</b> 0\n\n"
                f"Нажми кнопку ниже, чтобы участвовать!"
            )
            
            try:
                sent_msg = bot.send_message(channel_id, post_body, reply_markup=markup, parse_mode='HTML')
                
                active_giveaways[sent_msg.message_id] = {
                    'participants': set(),
                    'target_count': target,
                    'winners_count': winners_count,
                    'chat_id': channel_id,
                    'creator_id': user_id,
                    'text': raw_text,
                    'required_channels': required_channels
                }
                
                finish_markup = types.InlineKeyboardMarkup()
                finish_markup.add(types.InlineKeyboardButton('🛑 Завершить досрочно', callback_data=f'finish_{sent_msg.message_id}'))
                bot.send_message(user_id, f'✅ Розыгрыш в канале "{channel_title}" опубликован!', reply_markup=finish_markup)
                
                bot.edit_message_text(
                    chat_id=call.message.chat.id, message_id=call.message.message_id,
                    text='✅ Розыгрыш опубликован!',
                    reply_markup=get_main_menu_inline()
                )
            except Exception as e:
                print(f"Ошибка при отправке: {e}")
                bot.edit_message_text(
                    chat_id=call.message.chat.id, message_id=call.message.message_id,
                    text=f'❌ Ошибка при отправке:\n{e}',
                    reply_markup=get_back_button()
                )
            
            del user_states[user_id]
        bot.answer_callback_query(call.id)
    elif call.data == 'join_giveaway':
        msg_id = call.message.message_id
        if msg_id not in active_giveaways:
            bot.answer_callback_query(call.id, "❌ Этот розыгрыш уже завершен или не найден.", show_alert=True)
            return

        giveaway = active_giveaways[msg_id]
        if user_id in giveaway['participants']:
            bot.answer_callback_query(call.id, "Ты уже участвуешь в этом розыгрыше! 🍀", show_alert=True)
            return

        for req_channel in giveaway.get('required_channels', []):
            try:
                member = bot.get_chat_member(req_channel, user_id)
                if member.status in ['left', 'kicked']:
                    bot.answer_callback_query(call.id, "❌ Ты не подписан на все обязательные каналы! Сначала подпишись.", show_alert=True)
                    return
            except Exception:
                bot.answer_callback_query(call.id, "❌ Ошибка проверки подписки. Убедитесь, что подписаны на все каналы.", show_alert=True)
                return

        giveaway['participants'].add(user_id)
        bot.answer_callback_query(call.id, "✅ Вы участвуете в конкурсе! Удачи! 🍀", show_alert=True)
        
        count = len(giveaway['participants'])
        target = giveaway['target_count']
        safe_text = html.escape(giveaway['text'])
        
        if count >= target:
            winners = random.sample(list(giveaway['participants']), min(giveaway['winners_count'], count))
            winners_text = ", ".join([f'<a href="tg://user?id={w}">Пользователь</a>' for w in winners])
            
            final_post = (
                f"{safe_text}\n\n"
                f"🏆 <b>РОЗЫГРЫШ ЗАВЕРШЕН!</b>\n\n"
                f"<b>Победители:</b>\n{winners_text}\n\n"
                f"Поздравляем!"
            )
            try:
                bot.edit_message_text(
                    chat_id=giveaway['chat_id'], message_id=msg_id,
                    text=final_post, parse_mode='HTML', reply_markup=types.InlineKeyboardMarkup()
                )
            except Exception:
                pass
            
            del active_giveaways[msg_id]
            try:
                bot.send_message(giveaway['creator_id'], f'Твой розыгрыш завершился! Набралось {target} участников.')
            except Exception:
                pass
        else:
            updated_post = (
                f"{safe_text}\n\n"
                f"🎯 <b>Цель:</b> {target} участников\n"
                f"🏆 <b>Победителей:</b> {giveaway['winners_count']}\n"
                f"👥 <b>Сейчас:</b> {count}\n\n"
                f"Нажми кнопку ниже, чтобы участвовать!"
            )
            try:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(f'🎮 Участвовать ({count})', callback_data='join_giveaway'))
                bot.edit_message_text(
                    chat_id=giveaway['chat_id'], message_id=msg_id,
                    text=updated_post, parse_mode='HTML', reply_markup=markup
                )
            except Exception:
                pass

    elif call.data.startswith('finish_'):
        msg_id = int(call.data.replace('finish_', ''))
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
            winners_text = ", ".join([f'<a href="tg://user?id={w}">Пользователь</a>' for w in winners])
            safe_text = html.escape(giveaway['text'])
            
            final_post = (
                f"{safe_text}\n\n"
                f"🏆 <b>РОЗЫГРЫШ ЗАВЕРШЕН ДОСРОЧНО!</b>\n\n"
                f"<b>Победители:</b>\n{winners_text}\n\n"
                f"Поздравляем!"
            )
            
            try:
                bot.edit_message_text(
                    chat_id=giveaway['chat_id'], message_id=msg_id,
                    text=final_post, parse_mode='HTML', reply_markup=types.InlineKeyboardMarkup()
                )
                bot.answer_callback_query(call.id, "Розыгрыш завершен!")
                bot.delete_message(call.message.chat.id, call.message.message_id)
                bot.send_message(call.message.chat.id, '⚙️ Возвращаемся в меню:', reply_markup=get_main_menu_inline())
                del active_giveaways[msg_id]
            except Exception as e:
                bot.answer_callback_query(call.id, f"Ошибка: {e}", show_alert=True)

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
