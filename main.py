from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from quran_utils import get_surah, get_ayah, search_ayah
from config import BOT_TOKEN

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك في بوت القرآن الكريم! أرسل /help لرؤية الأوامر.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/surah رقم_السورة - لعرض سورة\n"
        "/ayah رقم_السورة رقم_الآية - لعرض آية\n"
        "/search كلمة - للبحث\n"
        "/audio رقم_السورة رقم_الآية - صوت التلاوة"
    )

async def surah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        surah_number = int(context.args[0])
        surah = get_surah(surah_number)
        text = f"سورة {surah['englishName']}\n\n"
        for ayah in surah['ayahs']:
            text += f"{ayah['numberInSurah']}: {ayah['text']}\n"
        await update.message.reply_text(text[:4096])
    except:
        await update.message.reply_text("يرجى إدخال رقم صحيح للسورة.")

async def ayah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        surah_number = int(context.args[0])
        ayah_number = int(context.args[1])
        ayah = get_ayah(surah_number, ayah_number)
        text = f"{ayah['surah']['englishName']} - {ayah['numberInSurah']}:\n{ayah['text']}"
        await update.message.reply_text(text)
    except:
        await update.message.reply_text("يرجى إدخال رقم السورة والآية بشكل صحيح.")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args)
    results = search_ayah(query)
    if not results:
        await update.message.reply_text("لم يتم العثور على نتائج.")
    else:
        reply = ""
        for res in results[:5]:
            reply += f"{res['surah']['name']} [{res['numberInSurah']}]: {res['text']}\n"
        await update.message.reply_text(reply)

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("surah", surah))
    app.add_handler(CommandHandler("ayah", ayah))
    app.add_handler(CommandHandler("search", search))
    print("Bot is running...")
    app.run_polling()
