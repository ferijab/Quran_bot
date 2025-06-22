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

# 🔐 التوكن الصحيح
TOKEN = '8052134194:AAEE2tm6M4hqVBM8ZfwktS-mHkcI3EmzJO8' 

# ⚠️ المتغيرات الأساسية
API_BASE = 'https://api.alquran.cloud/v1'
IMAGE_BASE = 'https://quran.com/images/surah/' 

# 🔥 متغير تخزين الإعجابات (في الذاكرة)
LIKES_DB = {} 

# 🕌 قاعدة بيانات الأذكار
ADHKAR_DB = {
    "morning": [
        "أصبحنا وأصبح الملك لله، والحمد لله، لا إله إلا الله وحده لا شريك له، له الملك وله الحمد وهو على كل شيء قدير",
        "اللهم بك أصبحنا، وبك أمسينا، وبك نحيا، وبك نموت، وإليك النشور",
        "اللهم إني أصبحت أشهدك، وأشهد حملة عرشك، وملائكتك، وجميع خلقك، أنك أنت الله لا إله إلا أنت وحدك لا شريك لك، وأن محمداً عبدك ورسولك"
    ],
    "evening": [
        "أمسينا وأمسى الملك لله، والحمد لله، لا إله إلا الله وحده لا شريك له، له الملك وله الحمد وهو على كل شيء قدير",
        "اللهم بك أمسينا، وبك أصبحنا، وبك نحيا، وبك نموت، وإليك المصير",
        "اللهم إني أمسيت أشهدك، وأشهد حملة عرشك، وملائكتك، وجميع خلقك، أنك أنت الله لا إله إلا أنت وحدك لا شريك لك، وأن محمداً عبدك ورسولك"
    ],
    "other": [
        "سبحان الله وبحمده: عدد خلقه، ورضا نفسه، وزنة عرشه، ومداد كلماته",
        "لا إله إلا الله وحده لا شريك له، له الملك وله الحمد وهو على كل شيء قدير",
        "اللهم صل وسلم على نبينا محمد"
    ]
} 

# 🔔 مستخدمون مفعلون للتذكيرات
REMINDER_USERS = {} 

# 🔧 إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__) 

# ===================== وظائف الأساسية ===================== 

# 📚 وظيفة لتنظيم الآيات في صفحات
def paginate_ayahs(ayahs, page=0, page_size=10):
    total_pages = (len(ayahs) + page_size - 1) // page_size
    start_idx = page * page_size
    end_idx = min((page + 1) * page_size, len(ayahs))
    text = ""
    for ayah in ayahs[start_idx:end_idx]:
        text += f"<b>{ayah['numberInSurah']}.</b> {ayah['text']}\n"
    return text, total_pages 

# ⏰ وظيفة التذكير بالأذكار
async def send_adhkar_reminder(context: CallbackContext):
    job = context.job
    adhkar_type = job.data
    
    if adhkar_type not in ADHKAR_DB:
        return
    
    try:
        # اختيار ذكر عشوائي
        dhikr = random.choice(ADHKAR_DB[adhkar_type])
        
        # إرسال التذكير
        await context.bot.send_message(
            chat_id=job.chat_id,
            text=f"⏰ <b>تذكير {('صباحي' if adhkar_type == 'morning' else 'مسائي')}:</b>\n\n{dhikr}",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in reminder: {e}") 

# 📆 جدولة التذكيرات للمستخدم
def schedule_adhkar_reminders(user_id: int, job_queue: JobQueue):
    try:
        # إزالة أي تذكيرات سابقة
        current_jobs = job_queue.get_jobs_by_name(str(user_id))
        for job in current_jobs:
            job.schedule_removal()
        
        # التوقيتات (تعديل حسب التوقيت المحلي)
        morning_time = datetime.time(hour=6, minute=0, tzinfo=datetime.timezone.utc)
        evening_time = datetime.time(hour=18, minute=0, tzinfo=datetime.timezone.utc)
        
        # جدولة التذكيرات
        job_queue.run_daily(
            send_adhkar_reminder,
            morning_time,
            days=(0, 1, 2, 3, 4, 5, 6),
            data="morning",
            chat_id=user_id,
            name=str(user_id)
        )
        
        job_queue.run_daily(
            send_adhkar_reminder,
            evening_time,
            days=(0, 1, 2, 3, 4, 5, 6),
            data="evening",
            chat_id=user_id,
            name=str(user_id)
        )
        
        return True
    except Exception as e:
        logger.error(f"Error scheduling reminders: {e}")
        return False 

# ===================== معالجات البوت ===================== 

# 🌟 دالة البدء المحسنة مع واجهة جميلة
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # لوحة مفاتيح متكاملة
        keyboard = [
            [InlineKeyboardButton("📖 قائمة السور", callback_data='list_surahs')],
            [InlineKeyboardButton("🌄 آية عشوائية", callback_data='random_ayah'), 
             InlineKeyboardButton("🎧 تلاوات", callback_data='audio_menu')],
            [InlineKeyboardButton("📿 الأذكار", callback_data='adhkar_menu')],
            [InlineKeyboardButton("🔍 بحث عن سورة", callback_data='search_surah')]
        ]
        
        # رسالة ترحيبية محسنة
        welcome_text = """
        <b>مرحبًا بك في بوت القرآن الكريم 🌙</b>
        
        يمكنك:
        - تصفح سور القرآن الكريم 🕌
        - سماع آيات عشوائية 🎲
        - الاستماع إلى التلاوات 🎧
        - الوصول إلى الأذكار الصباحية والمسائية 📿
        - البحث عن سورة معينة 🔍
        
        اختر أحد الخيارات أدناه للبدء:
        """
        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in start: {e}") 

# 📚 عرض قائمة السور مع تحسين الواجهة
async def list_surahs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        response = requests.get(f"{API_BASE}/surah")
        if response.status_code != 200:
            await query.edit_message_text("⚠️ حدث خطأ في جلب السور")
            return
            
        surahs = response.json().get('data', [])
        keyboard = []
        
        # تنظيم السور في أعمدة متعددة
        for i in range(0, len(surahs[:30]), 3):
            row = []
            for s in surahs[i:i+3]:
                name = f"{s['number']}. {s['name']}"
                row.append(InlineKeyboardButton(name, callback_data=f"surah_{s['number']}_0"))
            keyboard.append(row)
            
        # أزرار إضافية
        keyboard.append([
            InlineKeyboardButton("🎲 آية عشوائية", callback_data='random_ayah'),
            InlineKeyboardButton("🔙 رجوع", callback_data='back_to_start')
        ])
        
        # رسالة مع تنسيق محسّن
        await query.edit_message_text(
            "<b>📚 قائمة سور القرآن الكريم</b>\n\nاختر سورة من القائمة:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in list_surahs: {e}") 

# 📖 عرض السورة كاملة مع تنظيم الآيات
async def show_surah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        data = query.data.split('_')
        surah_num = data[1]
        page = int(data[2]) if len(data) > 2 else 0
        
        response = requests.get(f"{API_BASE}/surah/{surah_num}/ar.alafasy")
        if response.status_code != 200:
            await query.edit_message_text("⚠️ لم يتم العثور على السورة")
            return
            
        surah_data = response.json().get('data', {})
        ayahs = surah_data.get('ayahs', [])
        
        if not ayahs:
            await query.edit_message_text("⚠️ لا توجد آيات في هذه السورة")
            return
            
        # تنظيم الآيات في صفحات
        text, total_pages = paginate_ayahs(ayahs, page)
        header = f"<b>سورة {surah_data.get('name', '')}</b>\n\n"
        footer = f"\n\n📄 الصفحة {page+1}/{total_pages}"
        full_text = header + text + footer
        
        # لوحة تحكم للتنقل بين الصفحات
        keyboard = []
        nav_buttons = []
        
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"surah_{surah_num}_{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("▶️ التالي", callback_data=f"surah_{surah_num}_{page+1}"))
            
        if nav_buttons:
            keyboard.append(nav_buttons)
            
        # زر الإعجاب
        like_count = LIKES_DB.get(surah_num, 0)
        like_button = InlineKeyboardButton(f"❤️ إعجاب ({like_count})", callback_data=f"like_{surah_num}")
        
        # أزرار إضافية
        keyboard.append([like_button])
        keyboard.append([
            InlineKeyboardButton("🎧 استماع للسورة", callback_data=f'audio_{surah_num}'),
            InlineKeyboardButton("📚 العودة للقائمة", callback_data='list_surahs')
        ])
        
        # إرسال الصورة مع تنسيق محسّن
        try:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=f"{IMAGE_BASE}{surah_num}.png",
                caption=full_text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as photo_error:
            logger.error(f"Photo error: {photo_error}")
            await query.edit_message_text(
                full_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error in show_surah: {e}") 

# 🔊 تشغيل صوت السورة
async def play_surah_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        surah_num = query.data.split('_')[1]
        
        # جلب بيانات السورة
        response = requests.get(f"{API_BASE}/surah/{surah_num}/ar.alafasy")
        if response.status_code != 200:
            await query.edit_message_text("⚠️ لم يتم العثور على السورة")
            return
            
        data = response.json().get('data', {})
        ayahs = data.get('ayahs', [])
        
        if not ayahs:
            await query.edit_message_text("⚠️ لا توجد آيات في هذه السورة")
            return
            
        # إرسال أول آية كمثال
        first_ayah = ayahs[0]
        await context.bot.send_audio(
            chat_id=query.message.chat_id,
            audio=first_ayah['audio'],
            title=f"سورة {data['name']} - الآية 1",
            performer="مشاري العفاسي"
        )
        
        # لوحة مفاتيح للتحكم
        keyboard = [
            [InlineKeyboardButton("⏩ التالية", callback_data=f"next_ayah_{surah_num}_1")],
            [InlineKeyboardButton("🔁 إعادة تشغيل", callback_data=f"audio_{surah_num}"),
             InlineKeyboardButton("📖 عرض السورة", callback_data=f"surah_{surah_num}_0")]
        ]
        
        await query.message.reply_text(
            f"جار تشغيل الآية 1 من سورة {data['name']}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in play_surah_audio: {e}") 

# ⏩ تشغيل الآية التالية
async def play_next_ayah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        data = query.data.split('_')
        surah_num = data[2]
        ayah_num = int(data[3])
        
        # جلب بيانات السورة
        response = requests.get(f"{API_BASE}/surah/{surah_num}/ar.alafasy")
        if response.status_code != 200:
            await query.edit_message_text("⚠️ لم يتم العثور على السورة")
            return
            
        data = response.json().get('data', {})
        ayahs = data.get('ayahs', [])
        
        if not ayahs or ayah_num >= len(ayahs):
            await query.edit_message_text("⏹ تم الوصول إلى نهاية السورة")
            return
            
        # إرسال الآية الحالية
        ayah = ayahs[ayah_num]
        await context.bot.send_audio(
            chat_id=query.message.chat_id,
            audio=ayah['audio'],
            title=f"سورة {data['name']} - الآية {ayah['numberInSurah']}",
            performer="مشاري العفاسي"
        )
        
        # لوحة مفاتيح للتحكم
        keyboard = [
            [InlineKeyboardButton("⏩ التالية", callback_data=f"next_ayah_{surah_num}_{ayah_num+1}")],
            [InlineKeyboardButton("🔁 إعادة تشغيل", callback_data=f"audio_{surah_num}"),
             InlineKeyboardButton("📖 عرض السورة", callback_data=f"surah_{surah_num}_0")]
        ]
        
        await query.edit_message_text(
            f"جار تشغيل الآية {ayah['numberInSurah']} من سورة {data['name']}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in play_next_ayah: {e}") 

# 🌄 آية عشوائية مع عرض كامل
async def random_ayah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        surah_num = random.randint(1, 114)
        response = requests.get(f"{API_BASE}/surah/{surah_num}/ar.alafasy")
        
        if response.status_code != 200:
            await query.edit_message_text("⚠️ حدث خطأ في جلب الآية")
            return
            
        data = response.json().get('data', {})
        ayahs = data.get('ayahs', [])
        
        if ayahs:
            ayah = random.choice(ayahs)
            text = f"""
            <b>سورة {data.get('name', '')} (آية {ayah.get('numberInSurah', '')})</b>
            {ayah.get('text', '')}
            
            <i>تلاوة: الشيخ مشاري العفاسي</i>
            """
            
            # زر الإعجاب
            like_count = LIKES_DB.get(surah_num, 0)
            like_button = InlineKeyboardButton(f"❤️ إعجاب ({like_count})", callback_data=f"like_{surah_num}")
            
            # أزرار التحكم
            keyboard = [
                [
                    InlineKeyboardButton("🎧 استماع للتلاوة", callback_data=f'play_ayah_{surah_num}_{ayah["numberInSurah"]}'),
                    like_button
                ],
                [
                    InlineKeyboardButton("🌄 آية أخرى", callback_data='random_ayah'),
                    InlineKeyboardButton("📖 عرض السورة", callback_data=f'surah_{surah_num}_0')
                ]
            ]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text("⚠️ لا توجد آيات في هذه السورة")
    except Exception as e:
        logger.error(f"Error in random_ayah: {e}") 

# 🔊 تشغيل آية محددة
async def play_specific_ayah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        data = query.data.split('_')
        surah_num = data[2]
        ayah_num = int(data[3])
        
        # جلب بيانات السورة
        response = requests.get(f"{API_BASE}/surah/{surah_num}/ar.alafasy")
        if response.status_code != 200:
            await query.edit_message_text("⚠️ لم يتم العثور على السورة")
            return
            
        data = response.json().get('data', {})
        ayahs = data.get('ayahs', [])
        
        if not ayahs or ayah_num > len(ayahs):
            await query.edit_message_text("⚠️ لا توجد آيات في هذه السورة")
            return
            
        # إرسال الآية المحددة
        ayah = next((a for a in ayahs if a['numberInSurah'] == ayah_num), ayahs[0])
        await context.bot.send_audio(
            chat_id=query.message.chat_id,
            audio=ayah['audio'],
            title=f"سورة {data['name']} - الآية {ayah['numberInSurah']}",
            performer="مشاري العفاسي"
        )
        
        # لوحة مفاتيح للتحكم
        keyboard = [
            [InlineKeyboardButton("⏩ التالية", callback_data=f"play_ayah_{surah_num}_{ayah_num+1}")],
            [InlineKeyboardButton("🔁 إعادة تشغيل", callback_data=f"play_ayah_{surah_num}_{ayah_num}"),
             InlineKeyboardButton("📖 عرض السورة", callback_data=f"surah_{surah_num}_0")]
        ]
        
        await query.message.reply_text(
            f"جار تشغيل الآية {ayah['numberInSurah']} من سورة {data['name']}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in play_specific_ayah: {e}") 

# 🎧 قائمة التلاوات
async def audio_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        # قائمة القراء المشهورين (محدثة)
        reciters = [
            {"name": "مشاري العفاسي", "code": "ar.alafasy"},
            {"name": "محمود خليل الحصري", "code": "ar.husary"},
            {"name": "عبد الباسط عبد الصمد", "code": "ar.abdulsamad"},
            {"name": "سعد الغامدي", "code": "ar.alghamdi"},
            {"name": "محمد صديق المنشاوي", "code": "ar.minshawi"},
            {"name": "ياسر الدوسري", "code": "ar.dosari"},
            {"name": "عمر القزابري", "code": "ar.omarq"},
            {"name": "فارس عباد", "code": "ar.abbad"},
            {"name": "هزاع البلوشي", "code": "ar.hazaq"},
            {"name": "أحمد النعينع", "code": "ar.ahmedajamy"}
        ]
        
        keyboard = []
        for reciter in reciters:
            keyboard.append([InlineKeyboardButton(
                f"🎧 {reciter['name']}",
                callback_data=f"reciter_{reciter['code']}"
            )])
            
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='back_to_start')])
        
        await query.edit_message_text(
            "<b>🎧 اختر قارئًا للاستماع:</b>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in audio_menu: {e}") 

# 🔊 معالج اختيار القارئ
async def handle_reciter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        reciter_code = query.data.split('_')[1]
        
        # حفظ اختيار القارئ
        context.user_data['reciter'] = reciter_code
        
        # عرض رسالة تأكيد
        reciter_name = next((r['name'] for r in [
            {"name": "مشاري العفاسي", "code": "ar.alafasy"},
            {"name": "محمود خليل الحصري", "code": "ar.husary"},
            {"name": "عبد الباسط عبد الصمد", "code": "ar.abdulsamad"},
            {"name": "سعد الغامدي", "code": "ar.alghamdi"},
            {"name": "محمد صديق المنشاوي", "code": "ar.minshawi"},
            {"name": "ياسر الدوسري", "code": "ar.dosari"},
            {"name": "عمر القزابري", "code": "ar.omarq"},
            {"name": "فارس عباد", "code": "ar.abbad"},
            {"name": "هزاع البلوشي", "code": "ar.hazaq"},
            {"name": "أحمد النعينع", "code": "ar.ahmedajamy"}
        ] if r['code'] == reciter_code), "القارئ")
        
        keyboard = [
            [InlineKeyboardButton("📖 اختيار سورة", callback_data='list_surahs')],
            [InlineKeyboardButton("🎧 آية عشوائية", callback_data='random_ayah')]
        ]
        
        await query.edit_message_text(
            f"<b>تم اختيار القارئ: {reciter_name}</b>\n\n"
            "يمكنك الآن اختيار سورة للاستماع أو طلب آية عشوائية",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in handle_reciter: {e}") 

# 🔍 بحث عن السور
async def search_surah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "🔍 <b>أدخل اسم السورة أو رقمها:</b>",
            parse_mode='HTML'
        )
        context.user_data['awaiting_search'] = True
    except Exception as e:
        logger.error(f"Error in search_surah: {e}") 

# 🔍 معالجة البحث
async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if 'awaiting_search' not in context.user_data:
            return
            
        search_query = update.message.text.strip()
        context.user_data['awaiting_search'] = False
        
        # إذا كان البحث رقم
        if search_query.isdigit():
            surah_num = int(search_query)
            if 1 <= surah_num <= 114:
                # استدعاء دالة عرض السورة
                keyboard = [
                    [InlineKeyboardButton("📖 عرض السورة", callback_data=f"surah_{surah_num}_0")],
                    [InlineKeyboardButton("🎧 استماع للسورة", callback_data=f"audio_{surah_num}")]
                ]
                await update.message.reply_text(
                    f"<b>تم العثور على سورة رقم {surah_num}</b>",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
                return
                
        # البحث بالاسم
        response = requests.get(f"{API_BASE}/surah")
        if response.status_code != 200:
            await update.message.reply_text("⚠️ حدث خطأ في جلب السور")
            return
            
        surahs = response.json().get('data', [])
        results = []
        
        for s in surahs:
            if (search_query.lower() in s['name'].lower() or 
                search_query.lower() in s['englishName'].lower()):
                results.append(s)
                
        if results:
            text = "<b>🔍 نتائج البحث:</b>\n\n"
            for s in results[:5]:  # عرض أول 5 نتائج فقط
                text += f"{s['number']}. {s['name']} ({s['englishName']})\n"
            text += "\nاضغط على رقم السورة لعرضها"
            await update.message.reply_text(text, parse_mode='HTML')
        else:
            await update.message.reply_text("⚠️ لم يتم العثور على سورة بهذا الاسم")
    except Exception as e:
        logger.error(f"Error in handle_search: {e}") 

# 🔙 العودة للقائمة الرئيسية
async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        # نقوم بإنشاء حدث جديد للبدء
        await start(update, context)
    except Exception as e:
        logger.error(f"Error in back_to_start: {e}") 

# ❤️ معالج الإعجابات
async def handle_like(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        data = query.data.split('_')
        surah_num = data[1]
        
        # تحديث عدد الإعجابات
        LIKES_DB[surah_num] = LIKES_DB.get(surah_num, 0) + 1
        like_count = LIKES_DB[surah_num]
        
        # إرسال رسالة تأكيد
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"❤️ تم تسجيل إعجابك بسورة {surah_num} (الإجمالي: {like_count})"
        )
        
        # تحديث الزر في الرسالة الأصلية
        new_keyboard = []
        for row in query.message.reply_markup.inline_keyboard:
            new_row = []
            for button in row:
                if button.callback_data == f"like_{surah_num}":
                    new_button = InlineKeyboardButton(
                        f"❤️ إعجاب ({like_count})",
                        callback_data=button.callback_data
                    )
                    new_row.append(new_button)
                else:
                    new_row.append(button)
            new_keyboard.append(new_row)
        
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(new_keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in handle_like: {e}") 

# ===================== معالجات الأذكار ===================== 

# 📿 قائمة الأذكار الجديدة
async def adhkar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("أذكار الصباح 🌅", callback_data='morning_adhkar')],
            [InlineKeyboardButton("أذكار المساء 🌇", callback_data='evening_adhkar')],
            [InlineKeyboardButton("أذكار متنوعة 🌙", callback_data='other_adhkar')],
            [InlineKeyboardButton("تفعيل التذكيرات 🔔", callback_data='enable_reminders')],
            [InlineKeyboardButton("تعطيل التذكيرات 🔕", callback_data='disable_reminders')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_start')]
        ]
        
        await query.edit_message_text(
            "<b>📿 قائمة الأذكار</b>\n\nاختر نوع الأذكار:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in adhkar_menu: {e}") 

# 🌅 عرض أذكار الصباح
async def morning_adhkar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        text = "<b>🌅 أذكار الصباح:</b>\n\n"
        for i, dhikr in enumerate(ADHKAR_DB['morning'], 1):
            text += f"{i}. {dhikr}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("📿 المزيد من الأذكار", callback_data='adhkar_menu'),
            InlineKeyboardButton("🔔 تفعيل التذكيرات", callback_data='enable_reminders')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_start')]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in morning_adhkar: {e}") 

# 🌇 عرض أذكار المساء
async def evening_adhkar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        text = "<b>🌇 أذكار المساء:</b>\n\n"
        for i, dhikr in enumerate(ADHKAR_DB['evening'], 1):
            text += f"{i}. {dhikr}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("📿 المزيد من الأذكار", callback_data='adhkar_menu'),
            InlineKeyboardButton("🔔 تفعيل التذكيرات", callback_data='enable_reminders')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_start')]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in evening_adhkar: {e}") 

# 🌙 عرض أذكار متنوعة
async def other_adhkar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        text = "<b>🌙 أذكار متنوعة:</b>\n\n"
        for i, dhikr in enumerate(ADHKAR_DB['other'], 1):
            text += f"{i}. {dhikr}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("📿 المزيد من الأذكار", callback_data='adhkar_menu')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_start')]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in other_adhkar: {e}") 

# 🔔 تفعيل التذكيرات
async def enable_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # جدولة التذكيرات
        if schedule_adhkar_reminders(user_id, context.job_queue):
            REMINDER_USERS[user_id] = True
            message = "✅ <b>تم تفعيل التذكيرات اليومية</b>\n\nستصلك أذكار الصباح والمساء تلقائياً حسب التوقيت المحلي"
        else:
            message = "⚠️ <b>حدث خطأ في تفعيل التذكيرات</b>\n\nيرجى المحاولة لاحقاً"
        
        keyboard = [
            [InlineKeyboardButton("📿 قائمة الأذكار", callback_data='adhkar_menu')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_start')]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in enable_reminders: {e}") 

# 🔕 تعطيل التذكيرات
async def disable_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # إزالة التذكيرات
        current_jobs = context.job_queue.get_jobs_by_name(str(user_id))
        for job in current_jobs:
            job.schedule_removal()
        
        REMINDER_USERS[user_id] = False
        message = "🔕 <b>تم تعطيل التذكيرات اليومية</b>"
        
        keyboard = [
            [InlineKeyboardButton("📿 قائمة الأذكار", callback_data='adhkar_menu')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_start')]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in disable_reminders: {e}") 

# ===================== التشغيل الرئيسي ===================== 

# 🏁 تشغيل البوت مع إضافة معالجات الأذكار
def main():
    try:
        app = ApplicationBuilder().token(TOKEN).build()
        
        # إضافة جميع المعالجات
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(list_surahs, pattern='^list_surahs$'))
        app.add_handler(CallbackQueryHandler(show_surah, pattern='^surah_'))
        app.add_handler(CallbackQueryHandler(random_ayah, pattern='^random_ayah$'))
        app.add_handler(CallbackQueryHandler(audio_menu, pattern='^audio_menu$'))
        app.add_handler(CallbackQueryHandler(search_surah, pattern='^search_surah$'))
        app.add_handler(CallbackQueryHandler(back_to_start, pattern='^back_to_start$'))
        
        # معالجات الصوت
        app.add_handler(CallbackQueryHandler(play_surah_audio, pattern='^audio_'))
        app.add_handler(CallbackQueryHandler(play_next_ayah, pattern='^next_ayah_'))
        app.add_handler(CallbackQueryHandler(play_specific_ayah, pattern='^play_ayah_'))
        app.add_handler(CallbackQueryHandler(handle_reciter, pattern='^reciter_'))
        
        # معالجات الإعجابات
        app.add_handler(CallbackQueryHandler(handle_like, pattern='^like_'))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))
        
        # معالجات الأذكار الجديدة
        app.add_handler(CallbackQueryHandler(adhkar_menu, pattern='^adhkar_menu$'))
        app.add_handler(CallbackQueryHandler(morning_adhkar, pattern='^morning_adhkar$'))
        app.add_handler(CallbackQueryHandler(evening_adhkar, pattern='^evening_adhkar$'))
        app.add_handler(CallbackQueryHandler(other_adhkar, pattern='^other_adhkar$'))
        app.add_handler(CallbackQueryHandler(enable_reminders, pattern='^enable_reminders$'))
        app.add_handler(CallbackQueryHandler(disable_reminders, pattern='^disable_reminders$'))
        
        logger.info("✅ البوت يعمل الآن بنجاح...")
        app.run_polling()
    except Exception as e:
        logger.critical(f"فشل تشغيل البوت: {e}") 

if __name__ == '__main__':
    main()
