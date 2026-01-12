from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.errors import UserNotParticipantError
import asyncio
import os

# --- إعدادات الحساب ---
api_id = 24911514 
api_hash = 'f9f38f141846b0d912952467f5a9f5d3'
CH_USERNAME = 'x_b_rn' 

client = TelegramClient('session_name', api_id, api_hash)

# دالة التحقق من الاشتراك
async def check_subscribe(user_id):
    try:
        await client(GetParticipantRequest(channel=CH_USERNAME, participant=user_id))
        return True
    except UserNotParticipantError:
        return False
    except Exception:
        return True

# --- قائمة الأزرار الرئيسية ---
main_buttons = [
    [Button.inline("القسم الأول 1️⃣", data="section1"), Button.inline("القسم الثاني 2️⃣", data="section2")],
    [Button.inline("🚀 التحفيل 🚀", data="tahfel_info"), Button.inline("🎫 التساكر 🎫", data="tickets_list")],
    [Button.url("قناة البوت", url=f"https://t.me/{CH_USERNAME}")]
]

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = event.sender_id
    if not await check_subscribe(user_id):
        return await event.reply(
            f"**⚠️ عذراً عزيزي، يجب عليك الاشتراك في القناة أولاً!**\n\nقناتنا: @{CH_USERNAME}",
            buttons=[Button.url("اضغط هنا للاشتراك", url=f"https://t.me/{CH_USERNAME}")]
        )
    await event.reply("**نورت يا حبي ⚡**\n\nإليك قائمة التحكم الخاصة بك:", buttons=main_buttons)

# --- معالجة الضغط على الأزرار ---
@client.on(events.CallbackQuery)
async def callback(event):
    user_id = event.sender_id
    if not await check_subscribe(user_id):
        return await event.answer("⚠️ اشترك في القناة أولاً!", alert=True)

    # قسم معلومات الإرسال (التحفيل سابقاً في الداخل)
    if event.data == b'tahfel_info':
        text = (
            "**✨ أنورت يا اخويا ✨**\n\n"
            "هنا تقدر تكرر الرسايل براحتك.\n"
            "**طريقة الاستخدام:**\n"
            "ابعت الأمر كالتالي:\n"
            "`.تحفيل` (العدد) (نص الرسالة)\n\n"
            "**مثال:**\n"
            "`.تحفيل 100 صباح الخير`"
        )
        await event.edit(text, buttons=[Button.inline("⬅️ رجوع", data="back")])

    # قائمة الملفات (التساكر سابقاً في الداخل)
    elif event.data == b'tickets_list':
        path = "./tickets"
        if not os.path.exists(path) or not os.listdir(path):
            return await event.answer("❌ مفيش ملفات متاحة حالياً!", alert=True)
        
        files = os.listdir(path)
        buttons = []
        for file_name in files[:10]: 
            buttons.append([Button.inline(f"📄 {file_name}", data=f"send_file:{file_name}")])
        
        buttons.append([Button.inline("⬅️ رجوع", data="back")])
        await event.edit("**📂 اختر الملف اللي محتاجه:**", buttons=buttons)

    # إرسال الملف المختار
    elif event.data.startswith(b'send_file:'):
        file_name = event.data.decode().split(':')[1]
        file_path = f"./tickets/{file_name}"
        await event.answer("⏳ جاري إرسال الملف...", alert=False)
        await client.send_file(event.chat_id, file_path, caption=f"✅ تم استخراج ملف: `{file_name}`")

    elif event.data == b'back':
        await event.edit("**القائمة الرئيسية:**", buttons=main_buttons)

# --- كود تكرار الرسائل ---
@client.on(events.NewMessage(pattern=r'^\.تحفيل (\d+) (.+)'))
async def tahfel_handler(event):
    if not await check_subscribe(event.sender_id):
        return await event.reply(f"**❌ اشترك أولاً: @{CH_USERNAME}**")

    count = int(event.pattern_match.group(1))
    message_to_send = event.pattern_match.group(2)
    
    status_msg = await event.reply(f"⏳ لحظات وهيتم إرسال {count} رسالة...")

    for i in range(count):
        try:
            await client.send_message(event.chat_id, message_to_send)
            await asyncio.sleep(0.05) 
        except Exception: break
    await status_msg.edit(f"✅ فل عليك يا معلم، تم إرسال {count} رسالة بنجاح!")

# --- تشغيل البوت ---
print("البوت يعمل الآن...")
client.start()
client.run_until_disconnected()
