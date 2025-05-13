import os
import random
import string
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import re
from supabase import create_client

import instaloader
import io
from telegram import InputFile
import requests
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_1_USERNAME = os.getenv("CHANNEL_1_USERNAME")
CHANNEL_2_USERNAME = os.getenv("CHANNEL_2_USERNAME")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# توليد رمز التفعيل
def generate_token(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# دالة التحقق من الاشتراك في القنوات
async def check_subscription(update):
    user_id = update.effective_user.id
    unsubscribed_channels = []

    try:
        member1 = await bot.get_chat_member(CHANNEL_1_USERNAME, user_id)
        if member1.status not in ['member', 'administrator', 'creator']:
            unsubscribed_channels.append(f"1️⃣ {CHANNEL_1_USERNAME}")
    except Exception as e:
        print(f"Error checking {CHANNEL_1_USERNAME}: {e}")
        unsubscribed_channels.append(f"1️⃣ {CHANNEL_1_USERNAME}")

    try:
        member2 = await bot.get_chat_member(CHANNEL_2_USERNAME, user_id)
        if member2.status not in ['member', 'administrator', 'creator']:
            unsubscribed_channels.append(f"2️⃣ {CHANNEL_2_USERNAME}")
    except Exception as e:
        print(f"Error checking {CHANNEL_2_USERNAME}: {e}")
        unsubscribed_channels.append(f"2️⃣ {CHANNEL_2_USERNAME}")

    if unsubscribed_channels:
        message = "❌ يجب عليك الاشتراك في القنوات التالية لاستخدام البوت:\n\n"
        message += "\n".join(unsubscribed_channels)
        await update.message.reply_text(message)
        return False

    return True

# أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name

    # التحقق من الاشتراك في القنوات
    if not await check_subscription(update):
        return

    
    message = "أهلاَ وسهلاَ بك في بوت التحميل من الانستغرام :)"

    await update.message.reply_text(message, parse_mode="Markdown")

# استقبال روابط إنستغرام
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # التحقق من الاشتراك في القنوات
    if not await check_subscription(update):
        return
    message_text = update.message.text.strip()
    instagram_links = re.findall(r'https?://www\.instagram\.com/[^\s]+', message_text)

    if not instagram_links:
        await update.message.reply_text("❌ الرجاء إرسال رابط إنستغرام فقط.\nمثال: https://www.instagram.com/p/xyz")
        return

    for link in instagram_links:
        # إدخال الرابط في جدول الطابور
        supabase.table("queue").insert({
            "user_id": update.effective_user.id,
            "username": update.effective_user.username,
            "link": link,
        }).execute()

    await update.message.reply_text("✅ تم استلام الروابط، وسيتم معالجتها بالترتيب قريباً.")

# دالة تحميل محتوى إنستغرام
async def download_instagram_media_and_send(url, update):
    try:
        loader = instaloader.Instaloader()
    
        # تحميل المنشور من الرابط باستخدام loader.download_post
        post = instaloader.Post.from_shortcode(loader.context, url.split("/")[-1])
    
        if post.is_video:
            # تحميل الفيديو باستخدام الرابط
            video_url = post.video_url
            video_data = requests.get(video_url).content
    
            # تحويل الفيديو إلى BytesIO
            media_file = io.BytesIO(video_data)
            media_file.name = "video.mp4"
            media_file.seek(0)
    
            # إرسال الفيديو عبر تيليغرام
            await update.message.reply_video(video=InputFile(media_file), caption="🎥 فيديو من إنستغرام")
    
        else:
            # تحميل الصورة
            media_file = io.BytesIO(requests.get(post.url).content)  # تحميل الصورة
            media_file.name = "image.jpg"
            media_file.seek(0)
    
            # إرسال الصورة عبر تيليغرام
            await update.message.reply_photo(photo=InputFile(media_file), caption="📸 صورة من إنستغرام")
    
        return "✅ تم إرسال المحتوى بنجاح."
    
    except Exception as e:
        print("❌ خطأ أثناء التحميل:", e)
        return "❌ فشل تحميل المحتوى، حاول لاحقًا."

# دالة التشغيل الرئيسية
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    print("✅ بوت تيليغرام جاهز...")
    app.run_polling()

if __name__ == "__main__":
    main()
