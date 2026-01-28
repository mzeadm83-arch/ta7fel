# -*- coding: utf-8 -*-
import telebot
from telebot import types
import threading
import time
import json
import os
import logging
import datetime
import requests
import signal
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SupremeBot")

BOT_TOKEN = "8473744460:AAG446DP9xYIFs7z4lKCzzxgncOZuo7FpHY"
ADMIN_IDS = [1038191613, 7109774106, 7631371895]
MODERATORS = []
bot = telebot.TeleBot(BOT_TOKEN)
DB_FILE = "master_database.json"
LIBRARY_DIR = "library_files"

# إنشاء مجلد المكتبة
if not os.path.exists(LIBRARY_DIR):
    os.makedirs(LIBRARY_DIR)
    logger.info(f"✅ تم إنشاء مجلد المكتبة: {LIBRARY_DIR}")

user_bots = {}
user_state = {}
user_settings = {}
active_users = {}
banned_users = []
running_threads = {}
temp_storage = {}

def cleanup_dead_threads():
    try:
        dead = [t for t, s in running_threads.items() if not s]
        for t in dead:
            del running_threads[t]
        threading.Timer(1800, cleanup_dead_threads).start()
    except:
        threading.Timer(1800, cleanup_dead_threads).start()

def restart_bot():
    save_database()
    os.execv(sys.executable, ['python'] + sys.argv)

def schedule_restart():
    threading.Timer(43200, restart_bot).start()

signal.signal(signal.SIGINT, lambda s, f: (save_database(), sys.exit(0)))
signal.signal(signal.SIGTERM, lambda s, f: (save_database(), sys.exit(0)))

def init_user(user_id):
    if user_id not in user_bots:
        user_bots[user_id] = []
    if user_id not in user_state:
        user_state[user_id] = {"action": "none", "bot_index": None}
    if user_id not in user_settings:
        user_settings[user_id] = {"delay": 1}
    if user_id not in temp_storage:
        temp_storage[user_id] = {}

def save_database():
    try:
        active_tasks = {}
        for tid, running in running_threads.items():
            if running:
                uid, idx = tid.split("_")
                uid, idx = int(uid), int(idx)
                if uid in user_bots and idx < len(user_bots[uid]):
                    active_tasks[tid] = {"user_id": uid, "bot_index": idx}
        
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "user_bots": user_bots,
                "user_settings": user_settings,
                "banned_users": banned_users,
                "active_users": active_users,
                "active_tasks": active_tasks,
                "moderators": MODERATORS
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Save error: {e}")

def load_database():
    global user_bots, user_settings, banned_users, active_users, MODERATORS
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                user_bots = {int(k): v for k, v in data.get("user_bots", {}).items()}
                user_settings = {int(k): v for k, v in data.get("user_settings", {}).items()}
                banned_users = data.get("banned_users", [])
                active_users = {int(k): v for k, v in data.get("active_users", {}).items()}
                MODERATORS = data.get("moderators", [])
                
                for tid, info in data.get("active_tasks", {}).items():
                    uid, idx = info["user_id"], info["bot_index"]
                    if uid in user_bots and idx < len(user_bots[uid]):
                        running_threads[tid] = True
                        threading.Thread(
                            target=attack_worker,
                            args=(user_bots[uid][idx], user_settings.get(uid, {}).get("delay", 1), uid, tid),
                            daemon=True
                        ).start()
        except Exception as e:
            logger.error(f"Load error: {e}")

def is_admin(uid):
    return uid in ADMIN_IDS or uid in MODERATORS

def get_library_files():
    try:
        files = [f for f in os.listdir(LIBRARY_DIR) if f.endswith('.txt')]
        return sorted(files)
    except:
        return []

def count_messages_in_file(filename):
    try:
        filepath = os.path.join(LIBRARY_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f if l.strip()]
            return len(lines)
    except:
        return 0

def attack_worker(bot_data, delay, chat_id, task_id):
    try:
        worker = telebot.TeleBot(bot_data["token"])
        target, msgs, repeat = bot_data["target"], bot_data["messages"], bot_data["repeat"]
        
        if repeat == float('inf'):
            while running_threads.get(task_id, False):
                for msg in msgs:
                    if not running_threads.get(task_id, False):
                        break
                    try:
                        worker.send_message(target, msg)
                        time.sleep(delay)
                    except telebot.apihelper.ApiTelegramException as e:
                        if e.error_code == 429:
                            time.sleep(e.result_json['parameters']['retry_after'] + 1)
                        else:
                            time.sleep(0.5)
                    except:
                        time.sleep(1)
        else:
            for _ in range(repeat):
                if not running_threads.get(task_id, False):
                    break
                for msg in msgs:
                    if not running_threads.get(task_id, False):
                        break
                    try:
                        worker.send_message(target, msg)
                        time.sleep(delay)
                    except telebot.apihelper.ApiTelegramException as e:
                        if e.error_code == 429:
                            time.sleep(e.result_json['parameters']['retry_after'] + 1)
                    except:
                        time.sleep(1)
    except Exception as e:
        logger.error(f"Worker error: {e}")
    finally:
        running_threads[task_id] = False
        logger.info(f"🛑 {task_id} stopped completely")

def main_keyboard(uid):
    init_user(uid)
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton("🤖 جميع البوتات", callback_data="menu_bulk"))
    m.add(types.InlineKeyboardButton("➕ إضافة بوت", callback_data="add_bot"))
    m.add(types.InlineKeyboardButton("📖 الإرشادات", callback_data="instructions"))
    m.add(types.InlineKeyboardButton("⚡️ ضبط السرعة", callback_data="set_speed"))
    
    if user_bots.get(uid):
        m.add(types.InlineKeyboardButton("━━━━━ بوتاتك ━━━━━", callback_data="sep"))
        for i, b in enumerate(user_bots[uid]):
            m.add(types.InlineKeyboardButton(f"🤖 {b['name']}", callback_data=f"bot_{i}"))
    
    if is_admin(uid):
        m.add(types.InlineKeyboardButton("🛠 لوحة الإدارة", callback_data="admin"))
    
    return m

def bulk_keyboard(uid):
    running = any(running_threads.get(f"{uid}_{i}") for i in range(len(user_bots.get(uid, []))))
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton("⏹️ إيقاف الكل" if running else "▶️ تشغيل الكل", 
                                     callback_data="bulk_stop" if running else "bulk_start"))
    m.add(types.InlineKeyboardButton("📝 رسائل للكل", callback_data="bulk_write"))
    m.add(types.InlineKeyboardButton("📂 ملف txt للكل", callback_data="bulk_file"))
    m.add(types.InlineKeyboardButton("🎁 تساكر جاهزة", callback_data="bulk_library"))
    m.add(types.InlineKeyboardButton("🗂 جروب للكل", callback_data="bulk_target"))
    m.add(types.InlineKeyboardButton("⬅️ القائمة الرئيسية", callback_data="main"))
    return m

def single_keyboard(uid, idx):
    running = running_threads.get(f"{uid}_{idx}", False)
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton("⏹️ إيقاف" if running else "▶️ تشغيل",
                                     callback_data="single_stop" if running else "single_start"))
    m.add(types.InlineKeyboardButton("📝 رسائل", callback_data="single_write"))
    m.add(types.InlineKeyboardButton("📂 ملف txt", callback_data="single_file"))
    m.add(types.InlineKeyboardButton("🎁 تساكر جاهزة", callback_data="single_library"))
    m.add(types.InlineKeyboardButton("🗂 جروب", callback_data="single_target"))
    m.add(types.InlineKeyboardButton("🗑 حذف", callback_data="single_delete"))
    m.add(types.InlineKeyboardButton("⬅️ الرئيسية", callback_data="main"))
    return m

def library_keyboard(prefix="lib"):
    m = types.InlineKeyboardMarkup(row_width=2)
    files = get_library_files()
    
    if not files:
        m.add(types.InlineKeyboardButton("❌ لا توجد ملفات", callback_data="none"))
    else:
        for file in files:
            msg_count = count_messages_in_file(file)
            file_name = file.replace('.txt', '')
            m.add(types.InlineKeyboardButton(
                f"🎁 {file_name} ({msg_count} رسالة)",
                callback_data=f"{prefix}_{file_name}"
            ))
    
    m.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="main"))
    return m

def admin_keyboard(uid):
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton("📊 الجلسات", callback_data="admin_sessions"))
    m.add(types.InlineKeyboardButton("👥 المستخدمين", callback_data="admin_users"))
    m.add(types.InlineKeyboardButton("📢 الإذاعة", callback_data="admin_broadcast"))
    
    if uid in ADMIN_IDS:
        m.add(types.InlineKeyboardButton("👨‍💼 إضافة مشرف", callback_data="admin_addmod"))
        m.add(types.InlineKeyboardButton("❌ حذف مشرف", callback_data="admin_delmod"))
        m.add(types.InlineKeyboardButton("📋 قائمة المشرفين", callback_data="admin_listmod"))
        m.add(types.InlineKeyboardButton("🎁 إدارة التساكر", callback_data="admin_library"))
    
    m.add(types.InlineKeyboardButton("🚫 حظر مستخدم", callback_data="admin_ban"))
    m.add(types.InlineKeyboardButton("🔓 فك حظر", callback_data="admin_unban"))
    m.add(types.InlineKeyboardButton("⬅️ الرئيسية", callback_data="main"))
    return m

def admin_library_keyboard():
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton("➕ إضافة ملف", callback_data="lib_admin_add"))
    m.add(types.InlineKeyboardButton("🗑 حذف ملف", callback_data="lib_admin_delete"))
    m.add(types.InlineKeyboardButton("📋 عرض التساكر", callback_data="lib_admin_view"))
    m.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin"))
    return m

def delete_library_keyboard():
    m = types.InlineKeyboardMarkup(row_width=1)
    files = get_library_files()
    
    for file in files:
        file_name = file.replace('.txt', '')
        m.add(types.InlineKeyboardButton(
            f"🗑 حذف: {file_name}",
            callback_data=f"lib_del_{file_name}"
        ))
    
    m.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_library"))
    return m

@bot.message_handler(commands=['start'])
def start(msg):
    uid = msg.from_user.id
    if uid in banned_users:
        bot.send_message(msg.chat.id, "❌ حسابك محظور من استخدام البوت")
        return
    
    init_user(uid)
    if uid not in active_users:
        active_users[uid] = {
            "name": msg.from_user.first_name,
            "username": msg.from_user.username,
            "date": str(datetime.datetime.now())
        }
        save_database()
    
    bot.send_message(msg.chat.id, 
        f"👋 أهلا {msg.from_user.first_name}\n\n🤖 بوت تحفيل احترافي\n💬 @uvvvrn",
        reply_markup=main_keyboard(uid))

@bot.callback_query_handler(func=lambda c: True)
def callback(c):
    uid = c.from_user.id
    d = c.data
    init_user(uid)
    
    try:
        if d == "main":
            user_state[uid] = {"action": "none", "bot_index": None}
            bot.edit_message_text("🏠 القائمة الرئيسية", c.message.chat.id, c.message.message_id, 
                                reply_markup=main_keyboard(uid))
        
        elif d == "menu_bulk":
            if not user_bots.get(uid):
                bot.answer_callback_query(c.id, "❌ مفيش بوتات", show_alert=True)
                return
            bot.edit_message_text("🤖 التحكم الجماعي", c.message.chat.id, c.message.message_id,
                                reply_markup=bulk_keyboard(uid))
        
        elif d.startswith("bot_"):
            idx = int(d.split("_")[1])
            user_state[uid]["bot_index"] = idx
            bot.edit_message_text(f"⚙️ {user_bots[uid][idx]['name']}", c.message.chat.id, c.message.message_id,
                                reply_markup=single_keyboard(uid, idx))
        
        elif d == "add_bot":
            if len(user_bots.get(uid, [])) >= 15:
                bot.answer_callback_query(c.id, "⚠️ الحد الأقصى 15 بوت", show_alert=True)
                return
            bot.send_message(c.message.chat.id, "✏️ ابعت التوكن من @BotFather:")
            bot.register_next_step_handler(c.message, add_bot_token)
        
        elif d == "instructions":
            bot.send_message(c.message.chat.id, 
                "📘 *دليل الاستخدام*\n\n"
                "1️⃣ ضيف بوتاتك من @BotFather\n"
                "2️⃣ اختر تحكم فردي أو جماعي\n"
                "3️⃣ ارفع ملف txt أو استخدم المكتبة الجاهزة\n"
                "4️⃣ اضبط السرعة (الفاصل بين الرسائل)\n"
                "5️⃣ للتكرار اللا نهائي: اكتب 0\n\n"
                "📚 *المكتبة الجاهزة:* ملفات txt جاهزة للاستخدام المباشر\n\n"
                "💬 @uvvvrn",
                parse_mode="Markdown")
        
        elif d == "set_speed":
            bot.send_message(c.message.chat.id, "⏱️ ابعت الفاصل بالثواني (0 = سريع):")
            bot.register_next_step_handler(c.message, lambda m: speed_save(m))
        
        elif d == "bulk_start":
            bot.send_message(c.message.chat.id, "🔢 عدد التكرار (0 = لا نهائي):")
            bot.register_next_step_handler(c.message, bulk_start)
        
        elif d == "bulk_stop":
            count = 0
            for i in range(len(user_bots.get(uid, []))):
                tid = f"{uid}_{i}"
                if running_threads.get(tid, False):
                    running_threads[tid] = False
                    count += 1
            
            bot.answer_callback_query(c.id, f"🛑 تم إيقاف {count} بوت", show_alert=True)
            time.sleep(0.5)
            bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id, reply_markup=bulk_keyboard(uid))
            logger.info(f"User {uid} stopped {count} bots")
        
        elif d == "bulk_write":
            user_state[uid]["action"] = "bulk_write"
            temp_storage[uid]["pending"] = []
            bot.send_message(c.message.chat.id, "✏️ ابعت رسائلك. للإنهاء: تم")
            bot.register_next_step_handler(c.message, collect_msgs)
        
        elif d == "bulk_file":
            bot.send_message(c.message.chat.id, "📤 ارفع ملف txt:")
            bot.register_next_step_handler(c.message, lambda m: upload_file(m, "bulk"))
        
        elif d == "bulk_library":
            bot.edit_message_text("🎁 التساكر الجاهزة - اختر الملف:", 
                                c.message.chat.id, c.message.message_id,
                                reply_markup=library_keyboard("lib"))
        
        elif d == "bulk_target":
            bot.send_message(c.message.chat.id, "📍 ابعت يوزر أو رابط الجروب:")
            bot.register_next_step_handler(c.message, lambda m: set_target(m, "bulk"))
        
        elif d == "single_start":
            bot.send_message(c.message.chat.id, "🔢 عدد التكرار (0 = لا نهائي):")
            bot.register_next_step_handler(c.message, single_start)
        
        elif d == "single_stop":
            idx = user_state[uid]["bot_index"]
            tid = f"{uid}_{idx}"
            running_threads[tid] = False
            bot.answer_callback_query(c.id, "🛑 تم الإيقاف", show_alert=True)
            time.sleep(0.5)
            bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id, reply_markup=single_keyboard(uid, idx))
            logger.info(f"User {uid} stopped bot {idx}")
        
        elif d == "single_write":
            user_state[uid]["action"] = "single_write"
            temp_storage[uid]["pending"] = []
            bot.send_message(c.message.chat.id, "✏️ ابعت رسائلك. للإنهاء: تم")
            bot.register_next_step_handler(c.message, collect_msgs)
        
        elif d == "single_file":
            bot.send_message(c.message.chat.id, "📤 ارفع ملف txt:")
            bot.register_next_step_handler(c.message, lambda m: upload_file(m, "single"))
        
        elif d == "single_library":
            bot.edit_message_text("🎁 التساكر الجاهزة - اختر الملف:", 
                                c.message.chat.id, c.message.message_id,
                                reply_markup=library_keyboard("slib"))
        
        elif d == "single_target":
            bot.send_message(c.message.chat.id, "📍 ابعت يوزر أو رابط:")
            bot.register_next_step_handler(c.message, lambda m: set_target(m, "single"))
        
        elif d == "single_delete":
            idx = user_state[uid]["bot_index"]
            removed = user_bots[uid].pop(idx)
            save_database()
            bot.answer_callback_query(c.id, f"✅ حذف {removed['name']}", show_alert=True)
            bot.edit_message_text("✅ تم حذف البوت", c.message.chat.id, c.message.message_id, reply_markup=main_keyboard(uid))
        
        # المكتبة
        elif d.startswith(("lib_", "slib_")) and not d.startswith(("lib_admin_", "lib_del_")):
            handle_library(c)
        
        # الإدارة
        elif d == "admin":
            if not is_admin(uid):
                bot.answer_callback_query(c.id, "❌ غير مصرح", show_alert=True)
                return
            bot.edit_message_text("🛠 لوحة الإدارة", c.message.chat.id, c.message.message_id, reply_markup=admin_keyboard(uid))
        
        elif d == "admin_sessions":
            admin_sessions(c)
        
        elif d == "admin_users":
            admin_users(c)
        
        elif d == "admin_broadcast":
            bot.send_message(c.message.chat.id, 
                "📢 *الإذاعة - إرسال لجميع المستخدمين*\n\n"
                "ابعت الرسالة اللي عايز تبعتها:\n"
                "• نص\n• صورة + نص\n• فيديو + نص\n\n"
                "للإلغاء: cancel",
                parse_mode="Markdown")
            bot.register_next_step_handler(c.message, broadcast_msg)
        
        elif d == "admin_addmod":
            if uid not in ADMIN_IDS:
                bot.answer_callback_query(c.id, "❌ فقط المطورين", show_alert=True)
                return
            bot.send_message(c.message.chat.id, "👨‍💼 ابعت ID المستخدم:")
            bot.register_next_step_handler(c.message, add_moderator)
        
        elif d == "admin_delmod":
            if uid not in ADMIN_IDS:
                bot.answer_callback_query(c.id, "❌ فقط المطورين", show_alert=True)
                return
            bot.send_message(c.message.chat.id, "❌ ابعت ID المشرف:")
            bot.register_next_step_handler(c.message, del_moderator)
        
        elif d == "admin_listmod":
            if uid not in ADMIN_IDS:
                bot.answer_callback_query(c.id, "❌ فقط المطورين", show_alert=True)
                return
            if not MODERATORS:
                bot.send_message(c.message.chat.id, "📋 مفيش مشرفين")
            else:
                txt = "📋 *قائمة المشرفين:*\n\n"
                for mid in MODERATORS:
                    user_info = active_users.get(mid, {})
                    txt += f"• ID: `{mid}`"
                    if user_info.get('name'):
                        txt += f" - {user_info['name']}"
                    txt += "\n"
                bot.send_message(c.message.chat.id, txt, parse_mode="Markdown")
        
        # إدارة المكتبة
        elif d == "admin_library":
            if uid not in ADMIN_IDS:
                bot.answer_callback_query(c.id, "❌ فقط المطورين", show_alert=True)
                return
            bot.edit_message_text("🎁 إدارة التساكر", c.message.chat.id,
                                c.message.message_id, reply_markup=admin_library_keyboard())
        
        elif d == "lib_admin_add":
            if uid not in ADMIN_IDS:
                return
            bot.answer_callback_query(c.id)
            bot.send_message(c.message.chat.id, 
                           "📤 ارفع ملف txt للتساكر\n\n"
                           "⚠️ تأكد إن اسم الملف واضح (مثال: تساكر1.txt)")
            bot.register_next_step_handler(c.message, admin_add_library_file)
        
        elif d == "lib_admin_delete":
            if uid not in ADMIN_IDS:
                return
            files = get_library_files()
            if not files:
                bot.answer_callback_query(c.id, "❌ لا توجد ملفات", show_alert=True)
                return
            bot.edit_message_text("🗑 اختر ملف للحذف:", c.message.chat.id,
                                c.message.message_id, reply_markup=delete_library_keyboard())
        
        elif d.startswith("lib_del_"):
            if uid not in ADMIN_IDS:
                return
            file_name = d.replace("lib_del_", "")
            admin_delete_library_file(c, file_name)
        
        elif d == "lib_admin_view":
            if uid not in ADMIN_IDS:
                return
            admin_view_library(c)
        
        elif d == "admin_ban":
            bot.send_message(c.message.chat.id, "🚫 ابعت ID المستخدم:")
            bot.register_next_step_handler(c.message, ban_user)
        
        elif d == "admin_unban":
            bot.send_message(c.message.chat.id, "🔓 ابعت ID:")
            bot.register_next_step_handler(c.message, unban_user)
        
        elif d.startswith("stop_"):
            if not is_admin(uid):
                return
            tid = d.replace("stop_", "")
            running_threads[tid] = False
            bot.answer_callback_query(c.id, "✅ تم إيقاف البوت", show_alert=True)
            
            user_id = int(tid.split("_")[0])
            try:
                bot.send_message(user_id, "⚠️ تم إيقاف أحد بوتاتك بواسطة الإدارة")
            except:
                pass
    
    except Exception as e:
        logger.error(f"Callback: {e}")

def handle_library(c):
    uid = c.from_user.id
    parts = c.data.split("_", 1)
    mode = parts[0]
    file_name = parts[1] + ".txt"
    file_path = os.path.join(LIBRARY_DIR, file_name)
    
    if not os.path.exists(file_path):
        bot.answer_callback_query(c.id, "❌ الملف غير موجود", show_alert=True)
        return
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        
        if mode == "slib":
            idx = user_state[uid]["bot_index"]
            user_bots[uid][idx]["messages"] = lines
            save_database()
            bot.answer_callback_query(c.id, f"✅ تحميل {file_name}")
            bot.send_message(c.message.chat.id, f"✅ {len(lines)} رسالة من {file_name}",
                           reply_markup=single_keyboard(uid, idx))
        else:
            for b in user_bots.get(uid, []):
                b["messages"] = lines
            save_database()
            bot.answer_callback_query(c.id, f"✅ تحميل {file_name}")
            bot.send_message(c.message.chat.id, f"✅ {len(lines)} رسالة للكل من {file_name}",
                           reply_markup=bulk_keyboard(uid))
    except Exception as e:
        logger.error(f"خطأ قراءة المكتبة: {e}")
        bot.answer_callback_query(c.id, "❌ خطأ في القراءة", show_alert=True)

def add_bot_token(m):
    uid = m.from_user.id
    try:
        r = requests.get(f"https://api.telegram.org/bot{m.text.strip()}/getMe", timeout=10)
        if r.status_code != 200:
            raise Exception()
        me = r.json()['result']
        user_bots[uid].append({
            "name": f"بوت {len(user_bots[uid]) + 1}",
            "token": m.text.strip(),
            "username": me['username'],
            "messages": [],
            "target": "",
            "repeat": 1
        })
        save_database()
        bot.send_message(m.chat.id, f"✅ تم إضافة @{me['username']}", reply_markup=main_keyboard(uid))
    except:
        bot.send_message(m.chat.id, "❌ توكن غير صحيح!")

def speed_save(m):
    try:
        user_settings[m.from_user.id]["delay"] = int(m.text.strip())
        save_database()
        bot.send_message(m.chat.id, "✅ تم ضبط السرعة", reply_markup=main_keyboard(m.from_user.id))
    except:
        bot.send_message(m.chat.id, "❌ رقم غير صحيح!")

def collect_msgs(m):
    uid = m.from_user.id
    if m.text in ["تم", "Done"]:
        msgs = temp_storage[uid]["pending"]
        if not msgs:
            bot.send_message(m.chat.id, "❌ مفيش رسائل!")
            return
        
        if user_state[uid]["action"] == "single_write":
            idx = user_state[uid]["bot_index"]
            user_bots[uid][idx]["messages"] = msgs
            save_database()
            bot.send_message(m.chat.id, f"✅ تم حفظ {len(msgs)} رسالة", reply_markup=single_keyboard(uid, idx))
        else:
            for b in user_bots.get(uid, []):
                b["messages"] = msgs
            save_database()
            bot.send_message(m.chat.id, f"✅ تم حفظ {len(msgs)} رسالة للكل", reply_markup=bulk_keyboard(uid))
        return
    
    temp_storage[uid]["pending"].append(m.text)
    bot.register_next_step_handler(m, collect_msgs)

def upload_file(m, mode):
    uid = m.from_user.id
    if not m.document:
        bot.send_message(m.chat.id, "❌ هذا ليس ملف!")
        return
    
    try:
        f = bot.get_file(m.document.file_id)
        lines = [l.strip() for l in bot.download_file(f.file_path).decode('utf-8').splitlines() if l.strip()]
        
        if mode == "single":
            idx = user_state[uid]["bot_index"]
            user_bots[uid][idx]["messages"] = lines
            save_database()
            bot.send_message(m.chat.id, f"✅ تم تحميل {len(lines)} رسالة", reply_markup=single_keyboard(uid, idx))
        else:
            for b in user_bots.get(uid, []):
                b["messages"] = lines
            save_database()
            bot.send_message(m.chat.id, f"✅ تم تحميل {len(lines)} رسالة للكل", reply_markup=bulk_keyboard(uid))
    except:
        bot.send_message(m.chat.id, "❌ خطأ في قراءة الملف!")

def set_target(m, mode):
    uid = m.from_user.id
    target = m.text.strip()
    if "t.me/" in target:
        target = "@" + target.split("/")[-1]
    elif not target.startswith(("@", "-100")):
        target = "@" + target
    
    if mode == "single":
        idx = user_state[uid]["bot_index"]
        user_bots[uid][idx]["target"] = target
        save_database()
        bot.send_message(m.chat.id, f"✅ الهدف: {target}", reply_markup=single_keyboard(uid, idx))
    else:
        for b in user_bots.get(uid, []):
            b["target"] = target
        save_database()
        bot.send_message(m.chat.id, f"✅ الهدف للكل: {target}", reply_markup=bulk_keyboard(uid))

def bulk_start(m):
    uid = m.from_user.id
    try:
        repeat = float('inf') if m.text.strip() in ["0", "∞"] else int(m.text.strip())
        delay = user_settings[uid]["delay"]
        count = 0
        
        for i, b in enumerate(user_bots.get(uid, [])):
            if not b["messages"] or not b["target"]:
                continue
            b["repeat"] = repeat
            tid = f"{uid}_{i}"
            running_threads[tid] = True
            threading.Thread(target=attack_worker, args=(b, delay, m.chat.id, tid), daemon=True).start()
            count += 1
        
        save_database()
        msg = f"🚀 تم تشغيل {count} بوت"
        if repeat == float('inf'):
            msg += " ♾️ (لا نهائي)"
        bot.send_message(m.chat.id, msg, reply_markup=bulk_keyboard(uid))
    except:
        bot.send_message(m.chat.id, "❌ رقم غير صحيح!")

def single_start(m):
    uid = m.from_user.id
    idx = user_state[uid]["bot_index"]
    try:
        repeat = float('inf') if m.text.strip() in ["0", "∞"] else int(m.text.strip())
        b = user_bots[uid][idx]
        
        if not b["messages"] or not b["target"]:
            bot.send_message(m.chat.id, "❌ البوت يحتاج رسائل وهدف!")
            return
        
        b["repeat"] = repeat
        tid = f"{uid}_{idx}"
        running_threads[tid] = True
        threading.Thread(target=attack_worker, args=(b, user_settings[uid]["delay"], m.chat.id, tid), daemon=True).start()
        save_database()
        
        msg = "🚀 تم بدء الإرسال"
        if repeat == float('inf'):
            msg += " ♾️ (لا نهائي)"
        bot.send_message(m.chat.id, msg, reply_markup=single_keyboard(uid, idx))
    except:
        bot.send_message(m.chat.id, "❌ رقم غير صحيح!")

def admin_sessions(c):
    if not is_admin(c.from_user.id):
        return
    
    txt = "📊 *الجلسات النشطة:*\n\n"
    m = types.InlineKeyboardMarkup(row_width=1)
    found = False
    
    for uid, bots in user_bots.items():
        for i, b in enumerate(bots):
            tid = f"{uid}_{i}"
            if running_threads.get(tid, False):
                found = True
                user_info = active_users.get(uid, {})
                user_name = user_info.get('name', f"User {uid}")
                txt += f"👤 {user_name} (ID: `{uid}`)\n🤖 {b['name']}\n🎯 {b.get('target', 'N/A')}\n🟢 نشط\n─────\n"
                m.add(types.InlineKeyboardButton(f"⏹️ إيقاف {b['name']}", callback_data=f"stop_{tid}"))
    
    m.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin"))
    
    if not found:
        bot.send_message(c.message.chat.id, "📭 لا توجد جلسات نشطة حالياً", reply_markup=m)
    else:
        bot.send_message(c.message.chat.id, txt, parse_mode="Markdown", reply_markup=m)

def admin_users(c):
    if not is_admin(c.from_user.id):
        return
    
    if not active_users:
        bot.send_message(c.message.chat.id, "📭 لا يوجد مستخدمين مسجلين")
        return
    
    txt = "👥 *المستخدمين المسجلين:*\n\n"
    txt += f"📊 العدد الكلي: *{len(active_users)}* مستخدم\n"
    txt += f"🤖 إجمالي البوتات: *{sum(len(user_bots.get(uid, [])) for uid in active_users)}*\n\n"
    txt += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for idx, (uid, info) in enumerate(list(active_users.items())[:50], 1):
        bot_count = len(user_bots.get(uid, []))
        is_active = any(running_threads.get(f"{uid}_{i}", False) for i in range(bot_count))
        status = "🟢 نشط" if is_active else "⚪️ متوقف"
        
        txt += f"*{idx}.* {status}\n"
        txt += f"👤 الاسم: {info.get('name', 'غير معروف')}\n"
        txt += f"🆔 ID: `{uid}`\n"
        
        if info.get('username'):
            txt += f"📱 اليوزر: @{info.get('username')}\n"
        
        txt += f"🤖 البوتات: {bot_count}\n"
        txt += f"📅 التسجيل: {info.get('date', 'غير معروف')[:10]}\n"
        txt += "─────────────────\n"
    
    if len(active_users) > 50:
        txt += f"\n➕ *و {len(active_users) - 50} مستخدم آخر...*"
    
    # تقسيم الرسالة إذا كانت طويلة
    if len(txt) > 4000:
        parts = []
        current = ""
        for line in txt.split('\n'):
            if len(current) + len(line) + 1 > 4000:
                parts.append(current)
                current = line + '\n'
            else:
                current += line + '\n'
        if current:
            parts.append(current)
        
        for part in parts:
            bot.send_message(c.message.chat.id, part, parse_mode="Markdown")
            time.sleep(0.3)
    else:
        bot.send_message(c.message.chat.id, txt, parse_mode="Markdown")

def add_moderator(m):
    if m.from_user.id not in ADMIN_IDS:
        return
    
    try:
        mod_id = int(m.text.strip())
        if mod_id in ADMIN_IDS:
            bot.send_message(m.chat.id, "❌ هذا مطور أساسي بالفعل!")
            return
        
        if mod_id in MODERATORS:
            bot.send_message(m.chat.id, "⚠️ هذا مشرف بالفعل!")
            return
        
        MODERATORS.append(mod_id)
        save_database()
        
        bot.send_message(m.chat.id, f"✅ تمت إضافة {mod_id} كمشرف")
        
        try:
            bot.send_message(mod_id, 
                "🎉 *تمت ترقيتك!*\n\n"
                "أصبحت الآن مشرفاً في البوت\n"
                "يمكنك الوصول للوحة الإدارة من القائمة الرئيسية",
                parse_mode="Markdown")
        except:
            pass
            
    except ValueError:
        bot.send_message(m.chat.id, "❌ ID غير صحيح!")

def del_moderator(m):
    if m.from_user.id not in ADMIN_IDS:
        return
    
    try:
        mod_id = int(m.text.strip())
        
        if mod_id not in MODERATORS:
            bot.send_message(m.chat.id, "❌ هذا ليس مشرفاً!")
            return
        
        MODERATORS.remove(mod_id)
        save_database()
        
        bot.send_message(m.chat.id, f"✅ تم حذف {mod_id} من المشرفين")
        
        try:
            bot.send_message(mod_id, "⚠️ تم إزالتك من منصب المشرف")
        except:
            pass
            
    except ValueError:
        bot.send_message(m.chat.id, "❌ ID غير صحيح!")

def ban_user(m):
    if not is_admin(m.from_user.id):
        return
    
    try:
        uid = int(m.text.strip())
        
        if uid in ADMIN_IDS:
            bot.send_message(m.chat.id, "❌ لا يمكن حظر المطورين!")
            return
        
        if uid in MODERATORS:
            bot.send_message(m.chat.id, "❌ لا يمكن حظر المشرفين! احذفه من المشرفين أولاً")
            return
        
        if uid not in banned_users:
            banned_users.append(uid)
            
            for i in range(len(user_bots.get(uid, []))):
                running_threads[f"{uid}_{i}"] = False
            
            save_database()
        
        bot.send_message(m.chat.id, f"✅ تم حظر المستخدم {uid}")
        
        try:
            bot.send_message(uid, "🚫 تم حظرك من استخدام البوت بواسطة الإدارة")
        except:
            pass
            
    except ValueError:
        bot.send_message(m.chat.id, "❌ ID غير صحيح!")

def unban_user(m):
    if not is_admin(m.from_user.id):
        return
    
    try:
        uid = int(m.text.strip())
        
        if uid in banned_users:
            banned_users.remove(uid)
            save_database()
            bot.send_message(m.chat.id, f"✅ تم فك حظر {uid}")
            
            try:
                bot.send_message(uid, "✅ تم فك حظرك! يمكنك استخدام البوت الآن")
            except:
                pass
        else:
            bot.send_message(m.chat.id, "❌ هذا المستخدم غير محظور!")
            
    except ValueError:
        bot.send_message(m.chat.id, "❌ ID غير صحيح!")

def broadcast_msg(m):
    if not is_admin(m.from_user.id):
        return
    
    if m.text and m.text.strip().lower() in ['إلغاء', 'cancel']:
        bot.send_message(m.chat.id, "❌ تم إلغاء الإذاعة")
        return
    
    temp_storage[m.from_user.id]['bcast'] = m
    bot.send_message(m.chat.id, 
        f"⚠️ *تأكيد الإذاعة*\n\n"
        f"سيتم الإرسال لـ {len(active_users)} مستخدم\n\n"
        f"اكتب 'نعم' للتأكيد\nاكتب 'لا' للإلغاء",
        parse_mode="Markdown")
    bot.register_next_step_handler(m, broadcast_confirm)

def broadcast_confirm(m):
    if not is_admin(m.from_user.id):
        return
    
    if m.text.strip().lower() not in ['نعم', 'yes', 'أيوة']:
        bot.send_message(m.chat.id, "❌ تم إلغاء الإذاعة")
        return
    
    bm = temp_storage[m.from_user.id].get('bcast')
    if not bm:
        bot.send_message(m.chat.id, "❌ حدث خطأ!")
        return
    
    status = bot.send_message(m.chat.id, "📤 جاري الإرسال... 0%")
    
    total = len(active_users)
    success = failed = blocked = 0
    
    for idx, uid in enumerate(active_users.keys(), 1):
        try:
            if bm.text:
                bot.send_message(uid, bm.text)
            elif bm.photo:
                bot.send_photo(uid, bm.photo[-1].file_id, caption=bm.caption or "")
            elif bm.video:
                bot.send_video(uid, bm.video.file_id, caption=bm.caption or "")
            elif bm.document:
                bot.send_document(uid, bm.document.file_id, caption=bm.caption or "")
            elif bm.audio:
                bot.send_audio(uid, bm.audio.file_id, caption=bm.caption or "")
            elif bm.voice:
                bot.send_voice(uid, bm.voice.file_id)
            else:
                continue
                
            success += 1
            time.sleep(0.05)
            
        except telebot.apihelper.ApiTelegramException as e:
            if e.error_code == 403:
                blocked += 1
            else:
                failed += 1
        except:
            failed += 1
        
        if idx % 10 == 0 or idx == total:
            try:
                pct = int((idx / total) * 100)
                bot.edit_message_text(
                    f"📤 جاري الإرسال... {pct}%\n\n"
                    f"✅ نجح: {success}\n"
                    f"❌ فشل: {failed}\n"
                    f"🚫 محظور: {blocked}",
                    m.chat.id, status.message_id
                )
            except:
                pass
    
    final = (
        "✅ *اكتملت الإذاعة!*\n\n"
        f"📊 *الإحصائيات:*\n"
        f"👥 إجمالي المستخدمين: {total}\n"
        f"✅ نجح الإرسال: {success}\n"
        f"❌ فشل الإرسال: {failed}\n"
        f"🚫 حظروا البوت: {blocked}\n\n"
        f"📈 نسبة النجاح: {int((success/total)*100) if total > 0 else 0}%"
    )
    
    bot.send_message(m.chat.id, final, parse_mode="Markdown")
    logger.info(f"Broadcast by {m.from_user.id}: {success}/{total} successful")
    
    if 'bcast' in temp_storage[m.from_user.id]:
        del temp_storage[m.from_user.id]['bcast']

def admin_add_library_file(m):
    if m.from_user.id not in ADMIN_IDS:
        return
    
    if not m.document:
        bot.send_message(m.chat.id, "❌ لازم يكون ملف txt!")
        return
    
    if not m.document.file_name.endswith('.txt'):
        bot.send_message(m.chat.id, "❌ الملف لازم يكون txt!")
        return
    
    try:
        file_info = bot.get_file(m.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        file_path = os.path.join(LIBRARY_DIR, m.document.file_name)
        with open(file_path, 'wb') as f:
            f.write(downloaded)
        
        lines = [l.strip() for l in downloaded.decode('utf-8').splitlines() if l.strip()]
        
        bot.send_message(
            m.chat.id,
            f"✅ تم إضافة الملف للتساكر\n\n"
            f"📄 الاسم: {m.document.file_name}\n"
            f"📊 عدد الرسائل: {len(lines)}\n"
            f"📁 المسار: {LIBRARY_DIR}/",
            reply_markup=admin_library_keyboard()
        )
        
        logger.info(f"✅ تم إضافة ملف للتساكر: {m.document.file_name}")
        
    except Exception as e:
        logger.error(f"خطأ إضافة ملف للتساكر: {e}")
        bot.send_message(m.chat.id, "❌ حدث خطأ أثناء حفظ الملف!")

def admin_delete_library_file(c, file_name):
    if c.from_user.id not in ADMIN_IDS:
        return
    
    try:
        file_path = os.path.join(LIBRARY_DIR, file_name + ".txt")
        
        if os.path.exists(file_path):
            os.remove(file_path)
            bot.answer_callback_query(c.id, f"✅ تم حذف {file_name}", show_alert=True)
            logger.info(f"✅ تم حذف ملف من المكتبة: {file_name}")
            
            files = get_library_files()
            if files:
                bot.edit_message_text("🗑 اختر ملف للحذف:", 
                                    c.message.chat.id, c.message.message_id,
                                    reply_markup=delete_library_keyboard())
            else:
                bot.edit_message_text("✅ تم حذف الملف\n\n❌ لا توجد ملفات أخرى", 
                                    c.message.chat.id, c.message.message_id,
                                    reply_markup=admin_library_keyboard())
        else:
            bot.answer_callback_query(c.id, "❌ الملف غير موجود", show_alert=True)
            
    except Exception as e:
        logger.error(f"خطأ حذف ملف من المكتبة: {e}")
        bot.answer_callback_query(c.id, "❌ حدث خطأ", show_alert=True)

def admin_view_library(c):
    if c.from_user.id not in ADMIN_IDS:
        return
    
    files = get_library_files()
    
    if not files:
        bot.send_message(
            c.message.chat.id,
            "🎁 *التساكر الجاهزة*\n\n❌ لا توجد ملفات حالياً",
            parse_mode="Markdown",
            reply_markup=admin_library_keyboard()
        )
        return
    
    report = f"🎁 *التساكر الجاهزة ({len(files)} ملف):*\n\n"
    
    for i, file in enumerate(files, 1):
        msg_count = count_messages_in_file(file)
        file_size = os.path.getsize(os.path.join(LIBRARY_DIR, file)) / 1024
        
        report += f"{i}. *{file}*\n"
        report += f"   📊 الرسائل: {msg_count}\n"
        report += f"   💾 الحجم: {file_size:.1f} KB\n"
        report += "─────\n"
    
    report += f"\n📁 المسار: `{LIBRARY_DIR}/`"
    
    bot.send_message(
        c.message.chat.id,
        report,
        parse_mode="Markdown",
        reply_markup=admin_library_keyboard()
    )

if __name__ == "__main__":
    load_database()
    schedule_restart()
    cleanup_dead_threads()
    
    logger.info("═" * 60)
    logger.info("🚀 Supreme Bot 2026 - Started")
    logger.info(f"👨‍💼 Admins: {len(ADMIN_IDS)}")
    logger.info(f"👥 Moderators: {len(MODERATORS)}")
    logger.info(f"📊 Users: {len(active_users)}")
    logger.info(f"📚 Library Files: {len(get_library_files())}")
    logger.info("═" * 60)
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        logger.info("🛑 Stopped by user")
        save_database()
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        save_database()
        time.sleep(5)
        restart_bot()
