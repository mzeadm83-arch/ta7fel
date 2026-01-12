from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import asyncio
import os

# --- إعدادات الحساب ---
api_id = 24911514 
api_hash = 'f9f38f141846b0d912952467f5a9f5d3'

# ⚠️ هنا تحط الكود اللي هتجيبه من بوت استخراج الجلسة (Telethon String)
# لو مش معاك، قولي فوراً وهديك كود بسيط تطلعه بيه
STRING_SESSION = 'حط الكود هنا' 

client = TelegramClient(StringSession(STRING_SESSION), api_id, api_hash)

# --- قائمة الأزرار ---
main_buttons = [
    [Button.inline("القسم الأول 1️⃣", data="section1"), Button.inline("القسم الثاني 2️⃣", data="section2")],
    [Button.inline("🚀 التحفيل 🚀", data="tahfel_info"), Button.inline("🎫 التساكر 🎫", data="tickets_list")],
    [Button.url("قناة البوت", url="https://t.me/x_b_rn")]
]

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply("**نورت يا حبي ⚡**\n\nإليك قائمة التحكم الخاصة بك:", buttons=main_buttons)

@client.on(events.CallbackQuery)
async def callback(event):
    if event.data == b'tahfel_info':
        await event.edit("**✨ أنورت يا اخويا ✨**\n\nابعت: `.تحفيل (العدد) (النص)`", buttons=[Button.inline("⬅️ رجوع", data="back")])
    elif event.data == b'tickets_list':
        # بيدور في المجلد الرئيسي أو tickets
        path = "./tickets" if os.path.exists("./tickets") else "."
        files = [f for f in os.listdir(path) if f.endswith('.rsmk')]
        if not files:
            return await event.answer("❌ مفيش ملفات حالياً!", alert=True)
        buttons = [[Button.inline(f"📄 {f}", data=f"send:{f}")] for f in files[:10]]
        buttons.append([Button.inline("⬅️ رجوع", data="back")])
        await event.edit("**📂 اختر الملف:**", buttons=buttons)
    elif event.data == b'back':
        await event.edit("**القائمة الرئيسية:**", buttons=main_buttons)
    elif event.data.startswith(b'send:'):
        f_name = event.data.decode().split(':')[1]
        path = f"./tickets/{f_name}" if os.path.exists("./tickets") else f"./{f_name}"
        await client.send_file(event.chat_id, path, caption=f"✅ تم إرسال: `{f_name}`")

@client.on(events.NewMessage(pattern=r'^\.تحفيل (\d+) (.+)'))
async def tahfel_handler(event):
    count = int(event.pattern_match.group(1))
    msg = event.pattern_match.group(2)
    await event.reply(f"⏳ جاري إرسال {count} رسالة...")
    for i in range(count):
        try:
            await client.send_message(event.chat_id, msg)
            await asyncio.sleep(0.1) # تأخير بسيط للأمان
        except: break

print("البوت بدأ العمل...")
client.start()
client.run_until_disconnected()
