import telebot
from telebot import types
import random
import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

TOKEN = '9132199477:AAERWdgbEEotj2Hx0qcJadx604lGZFv3CqQ' 
ADMIN_ID = 8679581943 
BOT_USERNAME = 'xoreygram_bot' 

bot = telebot.TeleBot(TOKEN)

user_states = {}
active_giveaways = {} 

# --- ФАЙЛ ДЛЯ СОХРАНЕНИЯ КАНАЛОВ ---
CHANNELS_FILE = 'channels.json'

def load_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_channels(data):
    with open(CHANNELS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

user_channels = load_channels()

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
    if str(user_id) in user_channels and user_channels[str(user_id)]:
        markup = types.InlineKeyboardMarkup()
        for ch_id, ch_title in user_channels[str(user_id)].items():
            markup.add(types.InlineKeyboardButton(f'📡 {ch_title}', callback_data=f'select_ch_{ch_id}'))
        markup.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
        
        if message_id:
            try: bot.edit_message_text(chat_id=chat_id, message_id=message_id, text='В каком канале хотите опубликовать конкурс?', reply_markup=markup)
            except: pass
        else:
            bot.send_message(chat_id, 'В каком канале хотите опубликовать конкурс?', reply_markup=markup)
    else:
        text = '❌ У тебя нет добавленных каналов. Сначала добавь меня в канал.'
        if message_id:
            try: bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=get_back_button())
            except: pass
        else:
            bot.send_message(chat_id, text, reply_markup=get_back_button())

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    if len(message.text.split()) > 1 and message.text.split()[1].startswith('join_'):
        try:
            msg_id = int(message.text.split()[1].split('_')[1])
        except (ValueError, IndexError):
            bot.send_message(message.chat.id, "❌ Неверная ссылка.")
            return

        if msg_id in active_giveaways:
            giveaway = active_giveaways[msg_id]
            
            if user_id in giveaway['participants']:
                bot.send_message(message.chat.id, "Ты уже участвуешь в этом розыгрыше! 🍀")
                return

            all_subscribed = True
            for req_channel in giveaway.get('required_channels', []):
                try:
                    member = bot.get_chat_member(req_channel, user_id)
                    if member.status in ['left', 'kicked']:
                        all_subscribed = False
                        break
                except Exception:
                    all_subscribed = False
                    break
            
            if not all_subscribed:
                bot.send_message(message.chat.id, "❌ Ты не подписан на все обязательные каналы! Сначала подпишись, потом участвуй.")
                return

            giveaway['participants'].add(user_id)
            bot.send_message(message.chat.id, "✅ Вы участвуете в конкурсе! Удачи! 🍀")
            
            count = len(giveaway['participants'])
            target = giveaway['target_count']
            
            if count >= target:
                winners = random.sample(list(giveaway['participants']), min(giveaway['winners_count'], count))
                winners_text = ", ".join([f"[Пользователь](tg://user?id={w})" for w in winners])
                
                try:
                    bot.edit_message_text(
                        chat_id=giveaway['chat_id'], message_id=msg_id,
                        text=f'{giveaway["text"]}\n\n🏆 **РОЗЫГРЫШ ЗАВЕРШЕН!**\n\n**Победители:**\n{winners_text}\n\nПоздравляем!',
                        parse_mode='Markdown', reply_markup=types.InlineKeyboardMarkup()
                    )
                except: pass
                
                del active_giveaways[msg_id]
                try: bot.send_message(giveaway['creator_id'], f'Твой розыгрыш завершился! Набралось {target} участников.')
                except: pass
            else:
                try:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton('🎮 Участвовать', url=f'https://t.me/{BOT_USERNAME}?start=join_{msg_id}'))
                    
                    bot.edit_message_text(
                        chat_id=giveaway['chat_id'], message_id=msg_id,
                        text=f'{giveaway["text"]}\n\n🎯 **Цель:** {target} участников\n🏆 **Победителей:** {giveaway["winners_count"]}\n👥 **Сейчас:** {count}\n\nНажми кнопку ниже, чтобы участвовать!',
                        parse_mode='Markdown', reply_markup=markup
                    )
                except: pass
        else:
            bot.send_message(message.chat.id, "❌ Этот розыгрыш уже завершен или не найден.")
        return

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
        # --- ДОБАВЛЕНИЕ ОСНОВНОГО КАНАЛА ---
        if state.get('step') == 'waiting_for_add_channel':
            channel_id = None
            channel_title = None
            
            if message.forward_from_chat:
                channel_id = message.forward_from_chat.id
                channel_title = message.forward_from_chat.title
            elif message.text.startswith('@'):
                try:
                    chat = bot.get_chat(message.text)
                    channel_id = chat.id
                    channel_title = chat.title
                except Exception:
                    bot.send_message(message.chat.id, '❌ Не удалось найти канал по этому юзернейму.')
                    return
            else:
                try:
                    channel_id = int(message.text)
                    channel_title = f"Канал {channel_id}"
                except ValueError:
                    bot.send_message(message.chat.id, '❌ Отправь @юзернейм, ID или перешли сообщение из канала.', reply_markup=get_back_button())
                    return
            
            try:
                test_msg = bot.send_message(channel_id, '✅ Бот успешно добавлен!')
                bot.delete_message(channel_id, test_msg.message_id)
                
                if str(user_id) not in user_channels:
                    user_channels[str(user_id)] = {}
                user_channels[str(user_id)][str(channel_id)] = channel_title
                save_channels(user_channels) # Сохраняем в файл
                
                bot.send_message(message.chat.id, f'✅ Канал "{channel_title}" успешно привязан!', reply_markup=get_main_menu_inline())
            except Exception:
                bot.send_message(message.chat.id, '❌ Ошибка. Убедись, что ты добавил меня в администраторы канала.', reply_markup=get_back_button())
            
            del user_states[user_id]
            return

        # --- ВВОД ТЕКСТА РОЗЫГРЫША ---
        elif state.get('step') == 'waiting_for_giveaway_text':
            state['text'] = message.text
            state['step'] = 'waiting_for_required_channels'
            
            text = (
                "➕ **Добавьте каналы, на которые пользователям нужно будет подписаться для участия.**\n\n"
                "❗️ Подписка на канал, в котором проводится розыгрыш, обязательна.\n\n"
                "1. Добавьте @xoreygram_bot в канал как администратора.\n"
                "2. Отправьте @юзернейм канала или перешлите сообщение.\n\n"
                "💬 Или нажмите кнопку ниже, чтобы пропустить:"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('📢 Пропустить подписки', callback_data='no_required_subs'))
            markup.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
            
            bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
            return

        # --- ДОБАВЛЕНИЕ ОБЯЗАТЕЛЬНЫХ КАНАЛОВ ---
        elif state.get('step') == 'waiting_for_required_channels':
            channel_id = None
            if message.forward_from_chat:
                channel_id = message.forward_from_chat.id
            elif message.text.startswith('@'):
                try:
                    chat = bot.get_chat(message.text)
                    channel_id = chat.id
                except Exception:
                    bot.send_message(message.chat.id, '❌ Не удалось найти канал.')
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
                bot.send_message(message.chat.id, '✅ Канал добавлен! Можете добавить еще или нажать кнопку ниже.')
            else:
                bot.send_message(message.chat.id, '❌ Отправьте @юзернейм канала или перешлите сообщение.')
            return

        # --- ЦЕЛЬ ---
        elif state.get('step') == 'waiting_for_target_count':
            try:
                state['target_count'] = int(message.text)
                state['step'] = 'waiting_for_winners_count'
                bot.send_message(message.chat.id, '🏆 Сколько победителей будет? (напиши число)', reply_markup=get_back_button())
            except ValueError:
                bot.send_message(message.chat.id, '❌ Пожалуйста, введи число (например, 10).', reply_markup=get_back_button())
            return

        # --- ПОБЕДИТЕЛИ ---
        elif state.get('step') == 'waiting_for_winners_count':
            try:
                state['winners_count'] = int(message.text)
                
                preview_text = (
                    f"📢 **Предпросмотр конкурса**\n\n"
                    f"**Текст:** {state['text']}\n"
                    f"**Цель:** {state['target_count']} участников\n"
                    f"**Победителей:** {state['winners_count']}\n"
                    f"**Обязательных каналов:** {len(state.get('required_channels', []))}\n\n"
                    f"Вы уверены, что хотите опубликовать конкурс?"
                )
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton('🚀 Да, опубликовать', callback_data='confirm_publish'))
                markup.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
                
                bot.send_message(message.chat.id, preview_text, reply_markup=markup, parse_mode='Markdown')
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
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, '⚙️ Главное меню:\nВыбери действие:', reply_markup=get_main_menu_inline())
        bot.answer_callback_query(call.id)
        return

    elif call.data == 'my_profile':
        bot.edit_message_text(
            chat_id=call.message.chat.id, message_id=call.message.message_id,
            text=f'👾 **Твой профиль**\n\nИмя: {call.from_user.first_name}\nID: {call.from_user.id}',
            reply_markup=get_back_button(), parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)

    elif call.data == 'add_channel':
        user_states[user_id] = {'step': 'waiting_for_add_channel'}
        bot.edit_message_text(
            chat_id=call.message.chat.id, message_id=call.message.message_id,
            text='🔗 Отправь @юзернейм канала, ID или перешли сообщение из канала.\n\n⚠️ Важно: я должен быть админом!',
            reply_markup=get_back_button()
        )
        bot.answer_callback_query(call.id)

    elif call.data == 'create_giveaway':
        user_states.pop(user_id, None)
        show_channels(call.message.chat.id, user_id, call.message.message_id)
        bot.answer_callback_query(call.id)

    elif call.data.startswith('select_ch_'):
        channel_id = int(call.data.split('_')[2])
        user_states[user_id] = {'step': 'waiting_for_giveaway_text', 'channel_id': channel_id, 'required_channels': set()}
        bot.edit_message_text(
            chat_id=call.message.chat.id, message_id=call.message.message_id,
            text=(
                "⚡️ Создание розыгрыша:\n\n"
                "✉️ Отправьте текст для розыгрыша.\n\n"
                "Бот полностью бесплатный. Будет приятно, если в посте укажете ссылку: @xoreygram_bot"
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
            channel_id = int(state['channel_id'])
            channel_title = user_channels[str(user_id)].get(str(channel_id), "Канал")
            text = state['text']
            target = state['target_count']
            winners_count = state['winners_count']
            required_channels = list(state.get('required_channels', []))
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('🎮 Участвовать', url=f'https://t.me/{BOT_USERNAME}?start=join_pending'))
            
            try:
                sent_msg = bot.send_message(channel_id, f'{text}\n\n🎯 **Цель:** {target} участников\n🏆 **Победителей:** {winners_count}\n👥 **Сейчас:** 0\n\nНажми кнопку ниже, чтобы участвовать!', reply_markup=markup, parse_mode='Markdown')
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton('🎮 Участвовать', url=f'https://t.me/{BOT_USERNAME}?start=join_{sent_msg.message_id}'))
                bot.edit_message_reply_markup(channel_id, sent_msg.message_id, reply_markup=markup)
                
                active_giveaways[sent_msg.message_id] = {
                    'participants': set(), 
                    'target_count': target,
                    'winners_count': winners_count,
                    'chat_id': channel_id, 
                    'creator_id': user_id, 
                    'text': text,
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
            except Exception:
                bot.edit_message_text(
                    chat_id=call.message.chat.id, message_id=call.message.message_id,
                    text='❌ Ошибка при отправке. Убедись, что бот админ.',
                    reply_markup=get_back_button()
                )
            
            del user_states[user_id]
        bot.answer_callback_query(call.id)

    elif call.data == 'join_giveaway':
        bot.answer_callback_query(call.id, "Пожалуйста, нажмите на кнопку 'Участвовать' в сообщении канала, чтобы перейти в бота.", show_alert=True)

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
                bot.send_message(call.message.chat.id, '⚙️ Возвращаемся в меню:', reply_markup=get_main_menu_inline())
                del active_giveaways[msg_id]
            except Exception:
                bot.answer_callback_query(call.id, "Ошибка. Возможно, сообщение удалено.")

def run_dummy_server():
    class DummyHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b"Bot is running")
        def do_HEAD(self):
            self.send_response(20)
