import os
from dotenv import load_dotenv
load_dotenv()

import logging
import requests
import random
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackContext,
    JobQueue
)

TOKEN = os.getenv('8052134194:AAEE2tm6M4hqVBM8ZfwktS-mHkcI3EmzJO8')
USERS = set()
LIKES_DB = {}
API_BASE = 'https://api.alquran.cloud/v1'
IMAGE_BASE = 'https://quran.com/images/surah/'

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        if user_id not in USERS:
            USERS.add(user_id)
            with open("users.txt", "a") as f:
                f.write(f"{user_id}\n")
        await update.message.reply_text("✅ أهلاً بك في بوت القرآن الكريم.")
    except Exception as e:
        logger.error(f"Error in start: {e}")

async def users_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("users.txt", "r") as f:
            user_ids = set(line.strip() for line in f if line.strip())
        await update.message.reply_text(f"👤 عدد مستخدمي البوت حتى الآن: {len(user_ids)} مستخدمًا.")
    except FileNotFoundError:
        await update.message.reply_text("⚠️ لا يوجد أي مستخدم بعد.")
    except Exception as e:
        logger.error(f"Error in users_count: {e}")

def main():
    try:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("users_count", users_count))
        logger.info("✅ البوت يعمل الآن...")
        app.run_polling()
    except Exception as e:
        logger.critical(f"فشل تشغيل البوت: {e}")

if __name__ == '__main__':
    main()