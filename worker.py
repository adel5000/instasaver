# worker.py

import os
import io
import requests
import instaloader
from dotenv import load_dotenv
from supabase import create_client
from telegram import Bot, InputFile
import asyncio

# تحميل المتغيرات من .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# الاتصال بـ Supabase و Telegram Bot
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# تحميل الفيديو أو الصورة من إنستغرام وإرسالها للمستخدم
async def download_and_send(link, user_id):
    try:
        loader = instaloader.Instaloader()
        shortcode = link.strip("/").split("/")[-2]
        print(shortcode)
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        if post.is_video:
            video_data = requests.get(post.video_url).content
            media = io.BytesIO(video_data)
            media.name = "video.mp4"
            media.seek(0)
            await bot.send_video(chat_id=user_id, video=InputFile(media), caption="🎥 فيديو من إنستغرام")
        else:
            image_data = requests.get(post.url).content
            media = io.BytesIO(image_data)
            media.name = "image.jpg"
            media.seek(0)
            await bot.send_photo(chat_id=user_id, photo=InputFile(media), caption="📸 صورة من إنستغرام")

        return True

    except Exception as e:
        print(f"❌ خطأ أثناء تحميل الرابط: {e}")
        await bot.send_message(chat_id=user_id, text="❌ فشل تحميل الرابط، تأكد أنه صالح.")
        return False

# دالة لمعالجة عناصر الطابور
async def process_queue():
    while True:
        try:
            result = supabase.table("queue") \
                .select("*") \
                .eq("status", "pending") \
                .order("created_at") \
                .limit(1) \
                .execute()

            if result.data:
                item = result.data[0]
                queue_id = item["id"]
                user_id = item["user_id"]
                link = item["link"]

                print(f"🚀 معالجة: {link} للمستخدم {user_id}")

                # تحديث الحالة إلى 'processing'
                supabase.table("queue").update({"status": "processing"}).eq("id", queue_id).execute()

                success = await download_and_send(link, user_id)

                if success:
                    supabase.table("queue").delete().eq("id", queue_id).execute()
                    print(f"✅ تم إرسال الرابط للمستخدم {user_id}")
                else:
                    supabase.table("queue").update({"status": "failed"}).eq("id", queue_id).execute()
                    print(f"⚠️ فشل الإرسال للمستخدم {user_id}")
            else:
                await asyncio.sleep(5)  # انتظار قبل إعادة المحاولة
        except Exception as e:
            print(f"❌ خطأ أثناء معالجة الطابور: {e}")
            await asyncio.sleep(5)

# تشغيل العامل
if __name__ == "__main__":
    print("🎯 بدأ العامل لمعالجة الروابط...")
    asyncio.run(process_queue())
