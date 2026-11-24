import telebot
from telebot import types
import random, os, html, json, threading
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = '9132199477:AAG3XZwM91wOe3mvgv6yNGRtAGRfJc67S1o'
ADMIN_ID = 8679581943
DATA_FILE = 'bot_data.json'
REF_REWARD = 1
MIN_WITHDRAW = 15

bot = telebot.TeleBot(TOKEN)
try:
    BOT_USERNAME = bot.get_me().username.strip()
except Exception:
    BOT_USERNAME = 'xoreygram_bot'

BASE_TG_URL = "https://t.me" + "/"
TZ_MSK = timezone(timedelta(hours=3))

user_states = {}
user_channels = {}
active_giveaways = {}
ADMIN_ID = 6607095023
all_users = set()
finished_giveaways = {}
pending_captchas = {}
referrals = {}
user_balances = {}

def get_now_str():
    return datetime.now(TZ_MSK).strftime("%d.%m.%Y в %H:%M")

def make_join_button(btn_text, btn_color, count, url):
    prefixes = {'blue': '🔵 ', 'red': '🔴 ', 'green': '🟢 ', 'default': ''}
    styles = {'blue': 'primary', 'red': 'danger', 'green': 'success'}
    label = f"{prefixes.get(btn_color, '')}{btn_text} ({count})"
    style_val = styles.get(btn_color)
    if style_val:
        try:
            return types.InlineKeyboardButton(label, url=url, style=style_val)
        except TypeError:
            pass
    return types.InlineKeyboardButton(label, url=url)

def load_data():
    global user_channels, active_giveaways, finished_giveaways, referrals, user_balances
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for uid, chs in data.get('user_channels', {}).items():
                    user_channels[int(uid)] = {int(cid): t for cid, t in chs.items()}
                for mid, gw in data.get('active_giveaways', {}).items():
                    gw['participants'] = set(gw.get('participants', []))
                    active_giveaways[int(mid)] = gw
                    global all_users
                all_users = set(data.get('all_users', []))
                for mid, fgw in data.get('finished_giveaways', {}).items():
                    finished_giveaways[int(mid)] = fgw
                for uid, refs in data.get('referrals', {}).items():
                    referrals[int(uid)] = set(refs)
                for uid, bal in data.get('user_balances', {}).items():
                    user_balances[int(uid)] = int(bal)
        except Exception as e:
            print(f"Ошибка загрузки: {e}")
def save_data():
     try:
        gw_save = {}
        for mid, gw in active_giveaways.items():
            c = gw.copy()
            c['participants'] = list(gw['participants'])
            gw_save[str(mid)] = c
        ch_save = {str(u): {str(c): t for c, t in chs.items()} for u, chs in user_channels.items()}
        fgw_save = {str(m): f for m, f in finished_giveaways.items()}
        ref_save = {str(u): list(r) for u, r in referrals.items()}
        bal_save = {str(u): b for u, b in user_balances.items()}
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({'user_channels': ch_save, 'active_giveaways': gw_save, 'finished_giveaways': fgw_save, 'referrals': ref_save, 'user_balances': bal_save, 'all_users': list(all_users)}, f, ensure_ascii=False)
     except Exception as e:
        print(f"Ошибка сохранения: {e}")

load_data()

def get_back_button():
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
    return m

def get_bottom_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton('⚡️ Создать розыгрыш'), types.KeyboardButton('📡 Мои каналы'))
    kb.add(types.KeyboardButton('💥Реферальная система'))
    return kb

def get_main_menu_inline(user_id):
    m = types.InlineKeyboardMarkup()
    if user_id in user_channels and user_channels[user_id]:
        for ch_id, ch_title in user_channels[user_id].items():
            m.add(types.InlineKeyboardButton(f'📡 {ch_title}', callback_data=f'select_ch_{ch_id}'))
    m.add(types.InlineKeyboardButton('🔗 Добавить канал', callback_data='add_channel'))
    return m

def get_my_channels_markup(user_id):
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton('➕ Добавление новых каналов', callback_data='add_channel'))
    if user_id in user_channels and user_channels[user_id]:
        for ch_id, ch_title in user_channels[user_id].items():
            m.add(types.InlineKeyboardButton(f'📡 {ch_title}', callback_data=f'select_ch_{ch_id}'))
    m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
    return m

def get_welcome_text():
    return "👋 Привет, вот доступные тебе команды\n<blockquote>🎁 /create — создание розыгрыша\n📡 /mychannels — мои каналы\n💥 /ref — реферальная система</blockquote>\n❗️ <i>Важно: если ты впервые в нашем боте, не забудь сначала добавить канал.</i>"
   
def ask_required_channels_step(chat_id):
    txt = f"➕Добавьте каналы для обязательной подписки (основной канал уже включен).\n\n1. Добавьте @{BOT_USERNAME} в админы канала.\n2. Отправьте @юзернейм или перешлите пост.\n\n💬 Или нажмите кнопку ниже:"
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton('📢 Без обязательных подписок', callback_data='no_required_subs'))
    mk.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
    bot.send_message(chat_id, txt, reply_markup=mk)

def show_channels(chat_id, user_id, message_id=None):
    if user_id in user_channels and user_channels[user_id]:
        m = types.InlineKeyboardMarkup()
        for ch_id, ch_title in user_channels[user_id].items():
            m.add(types.InlineKeyboardButton(f'📡 {ch_title}', callback_data=f'select_ch_{ch_id}'))
        m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
        if message_id:
            try:
                bot.edit_message_text(chat_id=chat_id, message_id=message_id, text='В каком канале хотите опубликовать конкурс?', reply_markup=m)
            except Exception:
                pass
        else:
            bot.send_message(chat_id, 'В каком канале хотите опубликовать конкурс?', reply_markup=m)
    else:
        txt = '❌ У тебя нет добавленных каналов. Сначала добавь меня в канал.'
        if message_id:
            try:
                bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=txt, reply_markup=get_back_button())
            except Exception:
                pass
        else:
            bot.send_message(chat_id, txt, reply_markup=get_back_button())
            
def publish_results(giveaway, winners, is_auto=False):
    e_party = '🎉'
    e_medal = '🏅'
    win_lines = []
    for i, w in enumerate(winners, 1):
        try:
            u = bot.get_chat(w)
            uname = f"@{u.username}" if u.username else f'<a href="tg://user?id={w}">{html.escape(u.first_name or "Победитель")}</a>'
        except Exception:
            uname = f'<a href="tg://user?id={w}">Победитель {w}</a>'
        win_lines.append(f"Место: {i} | ю-з: {uname}")
    winners_block = "<blockquote>" + ("\n".join(win_lines) if win_lines else "Нет участников") + "</blockquote>"
    res_text = f"{e_party}<b>Результаты розыгрыша:</b>\n\n{e_medal} <b>Победители:</b>\n{winners_block}"
    try:
        bot.send_message(giveaway['chat_id'], res_text, parse_mode='HTML')
    except Exception as e:
        print(f"Ошибка отправки итогов: {e}")

def send_captcha_challenge(chat_id, user_id, msg_id):
    a = random.randint(3, 19)
    b = random.randint(2, 15)
    ans = a + b
    pending_captchas[user_id] = {'msg_id': msg_id, 'ans': ans}
    options = {ans}
    while len(options) < 4:
        options.add(ans + random.choice([-5, -4, -3, -2, -1, 1, 2, 3, 4, 5]))
    opts = list(options)
    random.shuffle(opts)
    random.shuffle(opts)
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("🔄 Проверить подписку", url=f"{BASE_TG_URL}{BOT_USERNAME}/verify?startapp=join_{msg_id}"))
    bot.send_message(chat_id, f"🤖 <b>Проверка на бота!</b>\n\nРешите пример, чтобы участвовать:\n<b>{a} + {b} = ?</b>", parse_mode='HTML', reply_markup=mk)

def get_unsubscribed_markup(channels, msg_id):
    mk = types.InlineKeyboardMarkup()
    for idx, ch_id in enumerate(channels, 1):
        try:
            chat = bot.get_chat(ch_id)
            title = chat.title or f"Канал {idx}"
            url = f"{BASE_TG_URL}{chat.username}" if chat.username else (chat.invite_link or bot.export_chat_invite_link(ch_id))
            if url:
                mk.add(types.InlineKeyboardButton(f"📢 Подписаться: {title}", url=url))
        except Exception:
            pass
    mk.add(types.InlineKeyboardButton("🔄 Проверить подписку", url=f"{BASE_TG_URL}{BOT_USERNAME}?start=join_{msg_id}"))
    return mk
    
def register_participant(chat_id, user_id, msg_id):
    if msg_id not in active_giveaways:
        bot.send_message(chat_id, "❌ Этот розыгрыш уже завершен или не найден.")
        return
    gw = active_giveaways[msg_id]
    if user_id in gw['participants']:
        bot.send_message(chat_id, "Ты уже участвуешь в этом розыгрыше! 🍀")
        return
    gw['participants'].add(user_id)
    save_data()
    bot.send_message(chat_id, "✅ Вы участвуете в розыгрыше! Удачи! 🍀")
    cnt = len(gw['participants'])
    target = gw['target_count']
    if cnt >= target:
        winners = random.sample(list(gw['participants']), min(gw['winners_count'], cnt))
        finished_giveaways[msg_id] = {'text': gw['text'], 'winners': winners, 'total_participants': cnt, 'start_time': gw.get('start_time', 'Неизвестно'), 'end_time': get_now_str()}
        res_url = f"{BASE_TG_URL}{BOT_USERNAME}?start=results_{msg_id}"
        fm = types.InlineKeyboardMarkup()
        fm.add(types.InlineKeyboardButton('📊 Проверить результаты', url=res_url))
        try:
            bot.edit_message_reply_markup(chat_id=gw['chat_id'], message_id=msg_id, reply_markup=fm)
        except Exception:
            pass
        publish_results(gw, winners, is_auto=True)
        del active_giveaways[msg_id]
        save_data()
        try:
            bot.send_message(gw['creator_id'], f'Твой розыгрыш завершился! Набралось {target} участников.')
        except Exception:
            pass
    else:
        try:
            j_url = f"{BASE_TG_URL}{BOT_USERNAME}?start=join_{msg_id}"
            mk = types.InlineKeyboardMarkup()
            mk.add(make_join_button(gw.get('btn_text', '🎮 Участвовать'), gw.get('btn_color', 'default'), cnt, j_url))
            bot.edit_message_reply_markup(chat_id=gw['chat_id'], message_id=msg_id, reply_markup=mk)
        except Exception:
            pass

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id not in all_users:
        all_users.add(user_id)
        save_data()
    parts = message.text.split()
    if len(parts) > 1 and parts[-1].startswith('ref_'):
        try:
            inviter_id = int(parts[-1].replace('ref_', ''))
            if inviter_id != user_id and not any(user_id in r for r in referrals.values()):
                referrals.setdefault(inviter_id, set()).add(user_id)
                user_balances[inviter_id] = user_balances.get(inviter_id, 0) + REF_REWARD
                save_data()
                try:
                    bot.send_message(inviter_id, f"🎉 <b>По твоей реферальной ссылке перешёл новый друг!</b>\n\n💎 Начислено: <b>+{REF_REWARD} ⭐</b>\n💰 Твой баланс: <b>{user_balances[inviter_id]} ⭐</b>", parse_mode='HTML')
                except Exception:
                    pass
        except Exception:
            pass

    if len(parts) > 1 and parts[-1].startswith('results_'):
        try:
            msg_id = int(parts[-1].replace('results_', ''))
        except Exception:
            bot.send_message(message.chat.id, "❌ Неверная ссылка на результаты.")
            return
        if msg_id in finished_giveaways:
            res = finished_giveaways[msg_id]
            w_list = [f"• <a href='tg://user?id={w}'>Победитель</a> (ID: <code>{w}</code>)" for w in res.get('winners', [])]
            w_block = "\n".join(w_list) if w_list else "Не определены"
            safe_t = html.escape(res.get('text') or 'Медиа-розыгрыш')
            info = f"📊 <b>Результаты розыгрыша</b>\n\n📝 <b>Конкурс:</b> {safe_t}\n\n🏆 <b>Победители:</b>\n{w_block}\n\n👥 <b>Всего участников:</b> {res.get('total_participants', 0)}\n🕒 <b>Начало:</b> {res.get('start_time', 'Неизвестно')}\n🏁 <b>Завершение:</b> {res.get('end_time', 'Неизвестно')}"
            bot.send_message(message.chat.id, info, parse_mode='HTML', reply_markup=get_back_button())
        else:
            bot.send_message(message.chat.id, "❌ Результаты этого розыгрыша не найдены или он ещё не завершён.")
        return

    if len(parts) > 1 and parts[-1].startswith('join_'):
        try:
            msg_id = int(parts[-1].replace('join_', ''))
        except Exception:
            bot.send_message(message.chat.id, "❌ Неверная ссылка.")
            return
        if msg_id in active_giveaways:
            gw = active_giveaways[msg_id]
            if user_id in gw['participants']:
                bot.send_message(message.chat.id, "Ты уже участвуешь в этом розыгрыше! 🍀")
                return
            channels_to_check = list(set(gw.get('required_channels', []) + [gw['chat_id']]))
            not_sub = [c for c in channels_to_check if _not_subscribed(c, user_id)]
            if not_sub:
                bot.send_message(message.chat.id, "❌ Для участия в розыгрыше необходимо подписаться на канал(ы) ниже:", reply_markup=get_unsubscribed_markup(not_sub, msg_id))
                return
            if gw.get('use_captcha', False):
                mk = types.InlineKeyboardMarkup()
                mk.add(types.InlineKeyboardButton("🤖 Подтвердить участие", web_app=types.WebAppInfo(url=f"https://telegram-bot-1-1t48.onrender.com/?msg_id={msg_id}&uid={user_id}")))
                bot.send_message(message.chat.id, "🛡️ Для защиты от ботов нажмите кнопку ниже и проведите ползунок:", reply_markup=mk)
            else:
                register_participant(message.chat.id, user_id, msg_id)
        else:
            bot.send_message(message.chat.id, "❌ Этот розыгрыш уже завершен или не найден.")
        return

    user_states.pop(user_id, None)
    bot.send_message(message.chat.id, get_welcome_text(), parse_mode='HTML', reply_markup=get_bottom_keyboard())
    bot.send_message(message.chat.id, '📡 Выберите канал для розыгрыша:', reply_markup=get_main_menu_inline(user_id))
def _not_subscribed(ch_id, user_id):
    try:
        return bot.get_chat_member(ch_id, user_id).status in ['left', 'kicked']
    except Exception:
        return True

@bot.message_handler(commands=['create'])
def cmd_create(message):
    user_id = message.from_user.id
    user_states[user_id] = {'step': 'waiting_for_captcha_choice'}
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton('⛔Нет', callback_data='cap_choice_no'), types.InlineKeyboardButton('➕Да', callback_data='cap_choice_yes'))
    mk.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
    bot.send_message(message.chat.id, '🤖Розыгрыш с капчой?', reply_markup=mk)

@bot.message_handler(commands=['mychannels'])
def cmd_mychannels(message):
    user_id = message.from_user.id
    user_states.pop(user_id, None)
    txt = '📡 <b>Ваши привязанные каналы:</b>\n\nНажмите на канал, чтобы запустить в нём розыгрыш, или добавьте новый:'
    bot.send_message(message.chat.id, txt, parse_mode='HTML', reply_markup=get_my_channels_markup(user_id))

@bot.message_handler(commands=['ref'])
def cmd_ref(message):
    user_id = message.from_user.id
    user_states.pop(user_id, None)
    ref_count = len(referrals.get(user_id, set()))
    bal = user_balances.get(user_id, 0)
    ref_link = f"{BASE_TG_URL}{BOT_USERNAME}?start=ref_{user_id}"
    txt = f"💥 <b>Реферальная система</b> 💥\n\n🎁 Приглашай друзей по своей уникальной ссылке и получай <b>+{REF_REWARD} ⭐</b> за каждого нового пользователя!\n\n🔗 <b>Твоя реферальная ссылка:</b>\n<code>{ref_link}</code>\n\n👥 <b>Приглашено друзей:</b> {ref_count}\n💎 <b>Доступно к выводу:</b> {bal} ⭐ <i>(вывод от {MIN_WITHDRAW} ⭐)</i>"
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton('💰 Баланс', callback_data='ref_balance'), types.InlineKeyboardButton('💸 Вывод', callback_data='ref_withdraw'))
    mk.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
    bot.send_message(message.chat.id, txt, parse_mode='HTML', reply_markup=mk)

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    total_all = len(all_users | set(user_channels.keys()) | set(referrals.keys()))
    total_active_part = sum(len(g.get('participants', [])) for g in active_giveaways.values())
    bot.send_message(
        message.chat.id,
        f"👑 <b>Админ-панель статистики</b>\n\n"
        f"👥 Пользователей за всё время: <b>{total_all}</b>\n"
        f"📢 Привязано каналов: <b>{sum(len(v) for v in user_channels.values())}</b>\n"
        f"🎁 Активных розыгрышей: <b>{len(active_giveaways)}</b>\n"
        f"✅ Завершённых розыгрышей: <b>{len(finished_giveaways)}</b>\n"
        f"🎟 Участников в активных розыгрышах: <b>{total_active_part}</b>",
        parse_mode='HTML'
    )
@bot.message_handler(content_types=['text', 'photo', 'video', 'forwarded'])
def text_handler(message):
    user_id = message.from_user.id
    if message.text:
        cmd_txt = message.text.strip().lower()
        if cmd_txt in ['⚡️ создать розыгрыш', 'создать розыгрыш', '/create']:
            cmd_create(message)
            return
        if cmd_txt in ['📡 мои каналы', 'мои каналы', '/mychannels']:
            cmd_mychannels(message)
            return
        if cmd_txt in ['💥реферальная система', '💥 реферальная система', 'реферальная система', '/ref']:
            cmd_ref(message)
            return
    state = user_states.get(user_id)
    if isinstance(state, dict):
        step = state.get('step')
        if step == 'waiting_for_add_channel':
            ch_id, ch_title = None, None
            if message.forward_from_chat:
                ch_id, ch_title = message.forward_from_chat.id, message.forward_from_chat.title
            elif message.text:
                t_in = message.text.strip()
                if not t_in.startswith('@'): t_in = '@' + t_in
                try:
                    chat = bot.get_chat(t_in)
                    ch_id, ch_title = chat.id, chat.title
                except Exception as e:
                    bot.send_message(message.chat.id, f'❌ Не удалось найти канал.\nОшибка: {e}')
                    return
            else:
                bot.send_message(message.chat.id, '❌ Отправь @юзернейм канала или перешли сообщение из канала.')
                return
            try:
                if bot.get_chat_member(ch_id, bot.get_me().id).status not in ['administrator', 'creator']:
                    bot.send_message(message.chat.id, '❌ Бот не является администратором в этом канале!')
                    return
                if bot.get_chat_member(ch_id, user_id).status not in ['administrator', 'creator']:
                    bot.send_message(message.chat.id, '❌ Вы не администратор этого канала!')
                    return
                user_channels.setdefault(user_id, {})[ch_id] = ch_title
                save_data()
                bot.send_message(message.chat.id, f'✅ Канал "{ch_title}" успешно привязан!', reply_markup=get_main_menu_inline(user_id))
            except Exception as e:
                bot.send_message(message.chat.id, f'❌ Ошибка привязки ({e}).', reply_markup=get_back_button())
            del user_states[user_id]
            return

        elif step == 'waiting_for_giveaway_text':
            if message.content_type == 'photo':
                state['media_type'], state['media_id'], state['text'] = 'photo', message.photo[-1].file_id, message.caption or ''
            elif message.content_type == 'video':
                state['media_type'], state['media_id'], state['text'] = 'video', message.video.file_id, message.caption or ''
            elif message.content_type == 'text':
                state['media_type'], state['media_id'], state['text'] = 'text', None, message.text
            else:
                bot.send_message(message.chat.id, '❌ Отправьте текст, фото или видео.')
                return
            state['step'] = 'waiting_for_btn_text'
            state['required_channels'] = {state['channel_id']}
            mk = types.InlineKeyboardMarkup()
            mk.add(types.InlineKeyboardButton('🎁Участвую!', callback_data='btn_tpl_1'))
            mk.add(types.InlineKeyboardButton('💎Принять участие', callback_data='btn_tpl_2'))
            mk.add(types.InlineKeyboardButton('Я в деле💪', callback_data='btn_tpl_3'))
            mk.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
            bot.send_message(message.chat.id, 'Хорошо, отправьте текст который будет отображаться на кнопке', reply_markup=mk)
            return

        elif step == 'waiting_for_btn_text' and message.text:
            state['btn_text'] = message.text.strip()
            state['step'] = 'waiting_for_btn_color'
            mk = types.InlineKeyboardMarkup()
            mk.add(types.InlineKeyboardButton('Синяя', callback_data='btn_col_blue'), types.InlineKeyboardButton('Красная', callback_data='btn_col_red'))
            mk.add(types.InlineKeyboardButton('Зелёная', callback_data='btn_col_green'), types.InlineKeyboardButton('Обычная', callback_data='btn_col_default'))
            mk.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
            bot.send_message(message.chat.id, 'Какого цвета будет кнопка?', reply_markup=mk)
            return

        elif step == 'waiting_for_required_channels':
            ch_id = message.forward_from_chat.id if message.forward_from_chat else None
            if not ch_id and message.text:
                t_in = message.text.strip()
                if not t_in.startswith('@'): t_in = '@' + t_in
                try:
                    ch_id = bot.get_chat(t_in).id
                except Exception:
                    bot.send_message(message.chat.id, '❌ Не удалось найти канал.')
                    return
            if not ch_id:
                bot.send_message(message.chat.id, '❌ Отправьте @юзернейм или перешлите пост из канала.')
                return
            try:
                if bot.get_chat_member(ch_id, bot.get_me().id).status not in ['administrator', 'creator']:
                    bot.send_message(message.chat.id, '❌ Проверьте бота в администрации!')
                    return 
                state['required_channels'].add(ch_id)
                mk = types.InlineKeyboardMarkup()
                mk.add(types.InlineKeyboardButton('Продолжить настройку ➡️', callback_data='no_required_subs'))
                mk.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
                bot.send_message(message.chat.id, '✅ Канал добавлен! Ещё каналы или продолжить?', reply_markup=mk)
            except Exception:
                bot.send_message(message.chat.id, '❌ Ошибка проверки прав.')
            return

        elif step == 'waiting_for_target_count' and message.text:
            try:
                state['target_count'] = int(message.text)
                state['step'] = 'waiting_for_winners_count'
                bot.send_message(message.chat.id, '🏆 Сколько победителей будет? (напиши число)', reply_markup=get_back_button())
            except ValueError:
                bot.send_message(message.chat.id, '❌ Введи число (например, 10).', reply_markup=get_back_button())
            return

        elif step == 'waiting_for_winners_count' and message.text:
            try:
                state['winners_count'] = int(message.text)
                extra = max(0, len(state.get('required_channels', [])) - 1)
                cap_str = 'Да' if state.get('use_captcha') else 'Нет'
                m_map = {'photo': '🖼 Фото', 'video': '🎬 Видео', 'text': '📝 Только текст'}
                m_str = m_map.get(state.get('media_type', 'text'), '📝 Только текст')
                prev_txt = html.escape(state['text']) if state['text'] else '<i>(без текста)</i>'
                prev = f"📢 <b>Предпросмотр конкурса</b>\n\n<b>Формат:</b> {m_str}\n<b>Текст:</b> {prev_txt}\n<b>Кнопка:</b> {html.escape(state.get('btn_text', '🎮 Участвовать'))}\n<b>Капча:</b> {cap_str}\n<b>Цель:</b> {state['target_count']} участников\n<b>Победителей:</b> {state['winners_count']}\n<b>Доп. каналов:</b> {extra}\n\nОпубликовать конкурс?"
                mk = types.InlineKeyboardMarkup()
                mk.add(types.InlineKeyboardButton('🚀 Да, опубликовать', callback_data='confirm_publish'))
                mk.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
                bot.send_message(message.chat.id, prev, reply_markup=mk, parse_mode='HTML')
                state['step'] = 'waiting_for_confirm'
            except ValueError:
                bot.send_message(message.chat.id, '❌ Введи число (например, 1).', reply_markup=get_back_button())
            return

    bot.send_message(message.chat.id, '🤖 Я не понимаю. Напиши /start, чтобы открыть меню.', reply_markup=get_back_button())
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    state = user_states.get(user_id)

    if call.data in ['back_to_menu', 'main_menu']:
        user_states.pop(user_id, None)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(call.message.chat.id, get_welcome_text(), parse_mode='HTML', reply_markup=get_main_menu_inline(user_id))
        bot.answer_callback_query(call.id)
        return

    elif call.data == 'ref_menu_back':
        ref_count = len(referrals.get(user_id, set()))
        bal = user_balances.get(user_id, 0)
        ref_link = f"{BASE_TG_URL}{BOT_USERNAME}?start=ref_{user_id}"
        txt = f"💥 <b>Реферальная система</b> 💥\n\n🎁 Приглашай друзей по своей уникальной ссылке и получай <b>+{REF_REWARD} ⭐</b> за каждого нового пользователя!\n\n🔗 <b>Твоя реферальная ссылка:</b>\n<code>{ref_link}</code>\n\n👥 <b>Приглашено друзей:</b> {ref_count}\n💎 <b>Доступно к выводу:</b> {bal} ⭐ <i>(вывод от {MIN_WITHDRAW} ⭐)</i>"
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton('💰 Баланс', callback_data='ref_balance'), types.InlineKeyboardButton('💸 Вывод', callback_data='ref_withdraw'))
        mk.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=txt, parse_mode='HTML', reply_markup=mk)
        bot.answer_callback_query(call.id)
        return

    elif call.data == 'ref_balance':
        bal = user_balances.get(user_id, 0)
        ref_count = len(referrals.get(user_id, set()))
        need = max(0, MIN_WITHDRAW - bal)
        status_line = f"🚀 До минимального вывода не хватает: <b>{need} ⭐</b>" if need > 0 else "🎉 <b>Порог достигнут! Можешь оформить вывод прямо сейчас!</b>"
        txt = f"💰 <b>Твой реферальный баланс</b> 💰\n\n✨ <b>Текущий баланс:</b> <b>{bal} ⭐</b>\n👥 <b>Всего приглашено:</b> {ref_count} чел.\n🔥 <b>Награда за друга:</b> +{REF_REWARD} ⭐\n\n{status_line}"
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton('💸 Вывод', callback_data='ref_withdraw'))
        mk.add(types.InlineKeyboardButton('◀️ Назад к рефералке', callback_data='ref_menu_back'))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=txt, parse_mode='HTML', reply_markup=mk)
        bot.answer_callback_query(call.id)
        return

    elif call.data == 'ref_withdraw':
        bal = user_balances.get(user_id, 0)
        if bal < MIN_WITHDRAW:
            bot.answer_callback_query(call.id, f"❌ Недостаточно звёзд! Минимум для вывода: {MIN_WITHDRAW} ⭐ (у тебя {bal} ⭐)", show_alert=True)
            return
        user_balances[user_id] = 0
        save_data()
        uname = f"@{call.from_user.username}" if call.from_user.username else "нет юзернейма"
        safe_name = html.escape(call.from_user.first_name or "Пользователь")
        admin_txt = f"🚨 <b>НОВАЯ ЗАЯВКА НА ВЫВОД ЗВЁЗД!</b> 🚨\n\n👤 <b>Пользователь:</b> <a href='tg://user?id={user_id}'>{safe_name}</a> ({uname})\n🆔 <b>ID:</b> <code>{user_id}</code>\n⭐ <b>Сумма к выводу:</b> <b>{bal} ⭐</b>\n🕒 <b>Время заявки:</b> {get_now_str()}"
        adm_mk = types.InlineKeyboardMarkup()
        adm_mk.add(types.InlineKeyboardButton('✅ Выплачено', callback_data=f'paid_ref_{user_id}_{bal}'))
        try:
            bot.send_message(ADMIN_ID, admin_txt, parse_mode='HTML', reply_markup=adm_mk)
        except Exception as e:
            print(f"Ошибка отправки заявки админу: {e}")
        user_txt = f"✅ <b>Заявка на вывод {bal} ⭐ успешно отправлена!</b>\n\n⏳ Администратор получил уведомление и скоро переведёт звёзды на твой аккаунт."
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton('◀️ Назад к рефералке', callback_data='ref_menu_back'))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=user_txt, parse_mode='HTML', reply_markup=mk)
        bot.answer_callback_query(call.id, "Заявка отправлена! 🎉")
        return

    elif call.data.startswith('paid_ref_'):
        if user_id == ADMIN_ID:
            parts = call.data.split('_')
            target_uid, amount = int(parts[-2]), int(parts[-1])
            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.html_text + "\n\n✅ <b>СТАТУС: ВЫПЛАЧЕНО</b>", parse_mode='HTML')
            except Exception:
                pass
            try:
                bot.send_message(target_uid, f"🎉 <b>Твоя заявка на вывод {amount} ⭐ выполнена!</b> Спасибо за приглашение друзей! ✨", parse_mode='HTML')
            except Exception:
                pass
            bot.answer_callback_query(call.id, "Отмечено как выплаченное!")
        return

    elif call.data in ['cap_choice_yes', 'cap_choice_no']:
        use_cap = (call.data == 'cap_choice_yes')
        user_states[user_id] = {'step': 'waiting_for_select_ch', 'use_captcha': use_cap}
        show_channels(call.message.chat.id, user_id, call.message.message_id)
        bot.answer_callback_query(call.id)
        return

    elif call.data.startswith('cap_'):
        parts = call.data.split('_')
        if len(parts) == 3:
            msg_id, chosen = int(parts[-2]), int(parts[-1])
            cap = pending_captchas.get(user_id)
            if not cap or cap['msg_id'] != msg_id:
                bot.answer_callback_query(call.id, "Капча устарела. Нажмите «Участвовать» в канале заново.", show_alert=True)
                return
            if chosen == cap['ans']:
                pending_captchas.pop(user_id, None)
                try:
                    bot.delete_message(call.message.chat.id, call.message.message_id)
                except Exception:
                    pass
                register_participant(call.message.chat.id, user_id, msg_id)
                bot.answer_callback_query(call.id, "Верно! ✅")
            else:
                bot.answer_callback_query(call.id, "❌ Неверно! Попробуйте новый пример.", show_alert=True)
                try:
                    bot.delete_message(call.message.chat.id, call.message.message_id)
                except Exception:
                    pass
                send_captcha_challenge(call.message.chat.id, user_id, msg_id)
        return
    elif call.data == 'add_channel':
        user_states[user_id] = {'step': 'waiting_for_add_channel'}
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='🔗 Отправь @юзернейм канала или перешли сюда пост из канала.\n\n⚠️ Я и ты должны быть админами в канале!', reply_markup=get_back_button())
        bot.answer_callback_query(call.id)

    elif call.data.startswith('select_ch_'):
        ch_id = int(call.data.replace('select_ch_', ''))
        use_cap = state.get('use_captcha', False) if isinstance(state, dict) else False
        user_states[user_id] = {'step': 'waiting_for_giveaway_text', 'channel_id': ch_id, 'required_channels': {ch_id}, 'use_captcha': use_cap}
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"⚡️ Создание розыгрыша:\n\n✉️ Отправьте текст (или фото/видео с текстом) для розыгрыша.\n\nБудет приятно, если укажете ссылку: @{BOT_USERNAME}", reply_markup=get_back_button())
        bot.answer_callback_query(call.id)

    elif call.data.startswith('btn_tpl_'):
        if state and state.get('step') == 'waiting_for_btn_text':
            tpl_map = {'btn_tpl_1': '🎁Участвую!', 'btn_tpl_2': '💎Принять участие', 'btn_tpl_3': 'Я в деле💪'}
            state['btn_text'] = tpl_map.get(call.data, '🎁Участвую!')
            state['step'] = 'waiting_for_btn_color'
            mk = types.InlineKeyboardMarkup()
            mk.add(types.InlineKeyboardButton('Синяя', callback_data='btn_col_blue'), types.InlineKeyboardButton('Красная', callback_data='btn_col_red'))
            mk.add(types.InlineKeyboardButton('Зелёная', callback_data='btn_col_green'), types.InlineKeyboardButton('Обычная', callback_data='btn_col_default'))
            mk.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Какого цвета будет кнопка?', reply_markup=mk)
        bot.answer_callback_query(call.id)

    elif call.data.startswith('btn_col_'):
        if state and state.get('step') == 'waiting_for_btn_color':
            state['btn_color'] = call.data.replace('btn_col_', '')
            state['step'] = 'waiting_for_required_channels'
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            ask_required_channels_step(call.message.chat.id)
        bot.answer_callback_query(call.id)

    elif call.data == 'no_required_subs':
        if state and state.get('step') == 'waiting_for_required_channels':
            state['step'] = 'waiting_for_target_count'
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='🎯 На сколько участников конкурс завершится? (напиши число)', reply_markup=get_back_button())
        bot.answer_callback_query(call.id)

    elif call.data == 'confirm_publish':
        if state and state.get('step') == 'waiting_for_confirm':
            ch_id = state['channel_id']
            ch_title = user_channels.get(user_id, {}).get(ch_id, "Канал")
            raw_t = state.get('text', '')
            m_type = state.get('media_type', 'text')
            m_id = state.get('media_id')
            target = state['target_count']
            w_cnt = state['winners_count']
            req_chs = list(state.get('required_channels', []))
            b_text = state.get('btn_text', '🎮 Участвовать')
            b_color = state.get('btn_color', 'default')
            use_cap = state.get('use_captcha', False)
            
            p_url = f"{BASE_TG_URL}{BOT_USERNAME}?start=join_pending"
            mk = types.InlineKeyboardMarkup()
            mk.add(make_join_button(b_text, b_color, 0, p_url))
            safe_body = html.escape(raw_t) if raw_t else None
            
            try:
                if m_type == 'photo' and m_id:
                    sent = bot.send_photo(ch_id, m_id, caption=safe_body, reply_markup=mk, parse_mode='HTML')
                elif m_type == 'video' and m_id:
                    sent = bot.send_video(ch_id, m_id, caption=safe_body, reply_markup=mk, parse_mode='HTML')
                else:
                    sent = bot.send_message(ch_id, safe_body or '🎁 Розыгрыш!', reply_markup=mk, parse_mode='HTML')

                try:
                    r_url = f"{BASE_TG_URL}{BOT_USERNAME}/verify?startapp=join_{sent.message_id}"
                    n_mk = types.InlineKeyboardMarkup()
                    n_mk.add(make_join_button(b_text, b_color, 0, r_url))
                    bot.edit_message_reply_markup(ch_id, sent.message_id, reply_markup=n_mk)
                except Exception as e_err:
                    print(f"Предупреждение кнопки: {e_err}")
                
                active_giveaways[sent.message_id] = {'participants': set(), 'target_count': target, 'winners_count': w_cnt, 'chat_id': ch_id, 'creator_id': user_id, 'text': raw_t, 'media_type': m_type, 'media_id': m_id, 'required_channels': req_chs, 'start_time': get_now_str(), 'btn_text': b_text, 'btn_color': b_color, 'use_captcha': use_cap}
                save_data()
                
                f_mk = types.InlineKeyboardMarkup()
                f_mk.add(types.InlineKeyboardButton('🛑 Завершить досрочно', callback_data=f'finish_{sent.message_id}'))
                bot.send_message(user_id, f'✅ Розыгрыш в канале "{ch_title}" опубликован!', reply_markup=f_mk)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='✅ Розыгрыш опубликован!', reply_markup=get_main_menu_inline(user_id))
            except Exception as e:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f'❌ Ошибка:\n{e}\n\n🔗 Ссылка: [{p_url}]', reply_markup=get_back_button())
            user_states.pop(user_id, None)
        bot.answer_callback_query(call.id)

    elif call.data.startswith('finish_'):
        msg_id = int(call.data.replace('finish_', ''))
        if msg_id in active_giveaways:
            gw = active_giveaways[msg_id]
            if user_id != gw['creator_id']:
                bot.answer_callback_query(call.id, "Только создатель может завершить!", show_alert=True)
                return
            parts = list(gw['participants'])
            if not parts:
                bot.answer_callback_query(call.id, "Никто не участвовал!", show_alert=True)
                return
            winners = random.sample(parts, min(gw['winners_count'], len(parts)))
            finished_giveaways[msg_id] = {'text': gw['text'], 'winners': winners, 'total_participants': len(parts), 'start_time': gw.get('start_time', 'Неизвестно'), 'end_time': get_now_str()}
            res_url = f"{BASE_TG_URL}{BOT_USERNAME}?start=results_{msg_id}"
            fm = types.InlineKeyboardMarkup()
            fm.add(types.InlineKeyboardButton('📊 Проверить результаты', url=res_url))
            try:
                bot.edit_message_reply_markup(chat_id=gw['chat_id'], message_id=msg_id, reply_markup=fm)
                bot.answer_callback_query(call.id, "Розыгрыш завершен!")
                publish_results(gw, winners, is_auto=False)
                try:
                    bot.delete_message(call.message.chat.id, call.message.message_id)
                except Exception:
                    pass
                bot.send_message(call.message.chat.id, '⚙️ Возвращаемся в меню:', reply_markup=get_main_menu_inline(user_id))
                del active_giveaways[msg_id]
                save_data()
            except Exception:
                bot.answer_callback_query(call.id, "Ошибка. Возможно, сообщение удалено.")
WEBAPP_HTML = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
*{box-sizing:border-box;-webkit-user-select:none;user-select:none}
body{margin:0;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;background:#17212b;color:#fff;font-family:-apple-system,sans-serif;text-align:center;padding:20px;overflow:hidden;touch-action:none}
.card{background:#232e3c;padding:28px 20px;border-radius:18px;width:100%;max-width:340px;box-shadow:0 8px 24px rgba(0,0,0,.3)}
h2{margin:0 0 8px;font-size:20px}p{margin:0 0 24px;color:#8e9ba8;font-size:14px}
.track{position:relative;height:56px;background:#17212b;border-radius:28px;overflow:hidden;border:1px solid #2f3e4e;touch-action:none}
.fill{position:absolute;left:0;top:0;bottom:0;width:0;background:linear-gradient(90deg,#2ea6ff,#007aff);border-radius:28px;pointer-events:none}
.txt{position:relative;z-index:1;line-height:56px;font-size:14px;color:#8e9ba8;pointer-events:none}
.knob{position:absolute;left:4px;top:4px;width:48px;height:48px;background:#fff;border-radius:50%;z-index:2;display:flex;align-items:center;justify-content:center;color:#007aff;font-weight:bold;font-size:22px;cursor:grab;box-shadow:0 2px 8px rgba(0,0,0,.4);touch-action:none}
</style></head><body><div class="card"><h2>🤖 Проверка на робота</h2><p id="st">Проведите ползунок вправо, чтобы подтвердить участие</p>
<div class="track" id="tr"><div class="fill" id="fl"></div><div class="txt" id="tx">Проведите вправо ➡️</div><div class="knob" id="kb">❯</div></div></div>
<script>
const tg=window.Telegram.WebApp;tg.ready();tg.expand();
const kb=document.getElementById('kb'),tr=document.getElementById('tr'),fl=document.getElementById('fl'),tx=document.getElementById('tx'),st=document.getElementById('st');
let drag=false,startX=0,done=false;
kb.onpointerdown=(e)=>{if(done)return;drag=true;startX=e.clientX;kb.setPointerCapture(e.pointerId)};
kb.onpointermove=(e)=>{if(!drag||done)return;const max=tr.offsetWidth-56;let dx=Math.max(0,Math.min(e.clientX-startX,max));kb.style.left=(4+dx)+'px';fl.style.width=(dx+52)+'px';
if(dx>=max-5){done=true;drag=false;tx.innerText='Проверяем...';kb.innerText='✓';
const p=new URLSearchParams(location.search);
const uid=p.get('uid')||(tg.initDataUnsafe&&tg.initDataUnsafe.user?tg.initDataUnsafe.user.id:'');
const rawMid=p.get('msg_id')||p.get('tgWebAppStartParam')||(tg.initDataUnsafe&&tg.initDataUnsafe.start_param)||'';
const mid=String(rawMid).replace('join_','');
fetch('/verify?uid='+encodeURIComponent(uid)+'&msg_id='+encodeURIComponent(mid))
.then(r=>r.text()).then(()=>{st.innerText='Готово!';setTimeout(()=>tg.close(),300)}).catch(()=>tg.close())}};
kb.onpointerup=()=>{if(!done){drag=false;kb.style.left='4px';fl.style.width='0'}};
kb.onpointercancel=()=>{if(!done){drag=false;kb.style.left='4px';fl.style.width='0'}};
</script></body></html>"""

def process_webapp_join(user_id_raw, msg_id_raw):
    if not user_id_raw or not msg_id_raw:
        return
    try:
        user_id = int(user_id_raw)
        msg_id = int(msg_id_raw)
    except Exception:
        return
    if msg_id not in active_giveaways:
        try:
            bot.send_message(user_id, "❌ Этот розыгрыш уже завершен или не найден.")
        except Exception:
            pass
        return
    gw = active_giveaways[msg_id]
    if user_id in gw['participants']:
        try:
            bot.send_message(user_id, "Ты уже участвуешь в этом розыгрыше! 🍀")
        except Exception:
            pass
        return
    register_participant(user_id, user_id, msg_id)
    
def run_dummy_server():
    class DummyHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith('/verify'):
                from urllib.parse import urlparse, parse_qs
                qs = parse_qs(urlparse(self.path).query)
                uid = next(iter(qs.get('uid', ())), None)
                mid = next(iter(qs.get('msg_id', ())), None)
                threading.Thread(target=process_webapp_join, args=(uid, mid), daemon=True).start()
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'ok')
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(WEBAPP_HTML.encode('utf-8'))
        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()
    server = HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), DummyHandler)
    server.serve_forever()
threading.Thread(target=run_dummy_server, daemon=True).start()
print(f"Бот запущен! Юзернейм: {BOT_USERNAME}")
bot.infinity_polling()
