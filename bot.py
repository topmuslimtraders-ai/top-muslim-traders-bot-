# -*- coding: utf-8 -*-
"""
Telegram Obuna / Guruh Sotish Boti — "Top Muslim Traders"
------------------------------------------------------------
O'rnatish:
    pip install "python-telegram-bot[job-queue]" --upgrade

Ishga tushirish:
    python bot.py

Railway Variables:
    BOT_TOKEN, ADMIN_CHAT_ID, VIDEO_GROUP_ID, VIP_GROUP_ID,
    DATA_FILE=/data/data.json   (Volume /data ga ulangan bo'lishi kerak)
    ADMIN_BOT_LINK (ixtiyoriy)  — standart: https://t.me/Hanif_Trader_bot
"""

import json
import logging
import os
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ============================================================
# SOZLAMALAR
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. Uni Railway Variables'ga qo'shing.")

# "Admin bilan bog'lanish" bosilganda o'tadigan bot (faqat havola, token kerak emas)
ADMIN_BOT_LINK = os.environ.get("ADMIN_BOT_LINK", "https://t.me/Hanif_Trader_bot")
ADMIN_PROFILE_LINK = ADMIN_BOT_LINK   # xavfsizlik eslatmasida ham shu bot ko'rsatiladi

_admin_chat_id_raw = os.environ.get("ADMIN_CHAT_ID")
if not _admin_chat_id_raw:
    raise RuntimeError("ADMIN_CHAT_ID topilmadi.")
ADMIN_CHAT_ID = int(_admin_chat_id_raw)

WALLETS = {
    "trc20": os.environ.get("WALLET_TRC20", "TNC3Z4sAzWh2rykt54TG5ks1zkz7gZF7ze"),
    "bep20": os.environ.get("WALLET_BEP20", "0xc666deccbe959eed0fcf960b477fe79d97e652cc"),
}

_video_group_raw = os.environ.get("VIDEO_GROUP_ID")
_vip_group_raw = os.environ.get("VIP_GROUP_ID")
if not _video_group_raw or not _vip_group_raw:
    raise RuntimeError("VIDEO_GROUP_ID va VIP_GROUP_ID Railway Variables'ida bo'lishi shart.")
VIDEO_GROUP_ID = int(_video_group_raw)
VIP_GROUP_ID = int(_vip_group_raw)

DATA_FILE = os.environ.get("DATA_FILE", "data.json")
REMINDER_WINDOW_DAYS = 3
CHECK_INTERVAL_SECONDS = 6 * 60 * 60   # Har 6 soatda tekshiruv

# ------------------------------------------------------------
# MAHSULOT VA TARIFLAR
# ------------------------------------------------------------
VIDEO_DARSLIK = {"label": "🎥 Video darsliklar", "price": "149$"}

VIP_PLANS = {
    "vip_1oy":     {"label": "1 oylik",  "price": "20$",  "days": 30},
    "vip_3oy":     {"label": "3 oylik",  "price": "55$",  "days": 90},
    "vip_6oy":     {"label": "6 oylik",  "price": "100$", "days": 180},
    "vip_1yil":    {"label": "1 yillik", "price": "189$", "days": 365},
    "vip_cheksiz": {"label": "Cheksiz",  "price": "249$", "days": None},
}

# ------------------------------------------------------------
# MATNLAR
# ------------------------------------------------------------
WELCOME_TEXT = (
    "🕌 <b>Assalomu alaykum va xush kelibsiz!</b>\n\n"
    "Siz <b>Top Muslim Traders</b> jamoasining rasmiy botidasiz. Bu yerda siz:\n\n"
    "🎥 Amaliy <b>video darsliklarimiz</b> bilan savdo asoslarini o'rganishingiz,\n"
    "📈 <b>VIP Signal</b> xizmatimiz orqali professional tahlil va signallardan "
    "foydalanishingiz mumkin.\n\n"
    "Quyidagi bo'limlardan birini tanlang 👇"
)

VIDEO_TAVSIF = (
    "💎 <b>Moliyaviy erkinlikka bir qadam qoldi!</b>\n\n"
    "Tayyor video darsliklarimiz — bu shunchaki nazariya emas, balki "
    "<b>Top Muslim Traders</b> jamoasining birinchi va ikkinchi potoklarida "
    "sinovdan o'tgan amaliy tajribasidir.\n\n"
    "Bu yerda siz qimmatli vaqtingizni yo'qotmasdan, bozorni chuqur tushunishga "
    "yordam beradigan fundamental bilimlarni olasiz — zamonaviy <b>Smart Money "
    "(SMC)</b> va <b>ICT</b> konsepsiyalaridan tortib, vaqt sinovidan o'tgan "
    "klassik strategiyalargacha barchasi jamlangan.\n\n"
    "Lekin eng muhimi — bu <b>xavfni to'g'ri boshqarish</b>. Tajribamiz shuni "
    "ko'rsatadiki, hatto eng zo'r strategiya ham to'g'ri risk-menejment "
    "bo'lmasa, sizni moliyaviy qiyinchilikka olib kelishi mumkin. "
    "Darsliklarda depozitingizni qanday asrash, ruxsat etilgan zararni to'g'ri "
    "belgilash va bozor bosimiga psixologik bardosh berish bo'yicha aniq "
    "qoidalar va shaxsiy tajribamiz bilan bo'lishamiz.\n\n"
    "📌 <i>Kirish muddati: cheksiz — bir marta to'laysiz, umrbod sizniki.</i>"
)

VIP_SAFETY_NOTE = (
    "🛡️ <b>Xavfsizlik bo'yicha muhim eslatma:</b>\n"
    "Savdo jarayonida xavfsizligingiz — bizning ustuvor vazifamiz. Adminlar "
    "sizga hech qachon <b>shaxsiy xabar yozib pul so'ramaydi</b> va "
    "<b>alohida shartnomalar taklif qilmaydi</b>. Barcha rasmiy muloqot "
    f"faqat shu bot va rasmiy admin {ADMIN_PROFILE_LINK} orqali amalga oshiriladi.\n"
    "Guruhga qo'shilgach, avvalo qoidalarni diqqat bilan o'qib chiqing — bu "
    "sizning muvaffaqiyatli va xavfsiz ishlashingiz garovidir."
)

VIP_INTRO_HEADER = (
    "📈 <b>VIP Signal olamiga xush kelibsiz!</b>\n\n"
    "Bu yerda siz professional tahlil va aniq signallar yordamida "
    "daromadingizni barqaror oshirish imkoniga ega bo'lasiz."
)

VIP_PLAN_TAVSIF = {
    "vip_1oy": (
        "🔹 <b>1 oylik tarif</b> — signallarimizni birinchi marta sinab "
        "ko'rmoqchi bo'lganlar uchun ideal tanlov. Bir oy davomida barcha VIP "
        "signallardan to'liq foydalanasiz."
    ),
    "vip_3oy": (
        "🔹 <b>3 oylik tarif</b> — barqaror natija olish uchun eng maqbul "
        "muddat. Bozor harakatlarini chuqurroq kuzatib, strategiyangizni "
        "mustahkamlash imkoniyati."
    ),
    "vip_6oy": (
        "🔹 <b>6 oylik tarif</b> — uzoq muddatli reja tuzayotganlar uchun mos "
        "yechim. Qulay narxda yarim yillik VIP kirish huquqi."
    ),
    "vip_1yil": (
        "🔹 <b>1 yillik tarif</b> — eng tejamkor va uzoq muddatli tanlov. "
        "Butun yil davomida barcha yangilanishlar va signallardan bemalol "
        "foydalanasiz."
    ),
    "vip_cheksiz": (
        "🔹 <b>Cheksiz tarif</b> — bir martalik to'lov, umrbod kirish huquqi! "
        "Kelajakda narxlar oshsa ham, sizdan hech qanday qo'shimcha to'lov "
        "talab qilinmaydi."
    ),
}

WELCOME_DUA_TEXT = (
    "🤲 <b>Assalomu alaykum, {name}!</b>\n\n"
    "Jamoamizga xush kelibsiz! Alloh taolo savdo-sotiqlaringizga baraka va "
    "halol foyda ato etsin, har bir qadamingiz shirin va foydali bo'lsin. "
    "Sabr-toqat va ilm bilan mehnat qilganlarga Yaratgan albatta yordam "
    "beradi. Omin! 🌿"
)


# ============================================================
# MA'LUMOTLAR BAZASI
# ============================================================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"subs": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    folder = os.path.dirname(DATA_FILE)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_subscription(user_id: int, chat_id: int, plan_label: str, days):
    data = load_data()
    expiry = None
    if days is not None:
        expiry = (datetime.utcnow() + timedelta(days=days)).isoformat()
    # Kalit: user + guruh, shunda video va VIP bir-birining ustiga yozilmaydi
    data["subs"][f"{user_id}:{chat_id}"] = {
        "user_id": user_id,
        "chat_id": chat_id,
        "plan": plan_label,
        "expiry": expiry,
        "reminded": False,
    }
    save_data(data)


# ============================================================
# YORDAMCHI FUNKSIYALAR
# ============================================================
def get_plan_info(plan_code: str):
    if plan_code == "video":
        return VIDEO_DARSLIK["label"], VIDEO_DARSLIK["price"]
    plan = VIP_PLANS[plan_code]
    return plan["label"], plan["price"]


def network_keyboard(plan_code: str):
    keyboard = [
        [InlineKeyboardButton("🟢 TRC20 (TRON)", callback_data=f"net_trc20_{plan_code}")],
        [InlineKeyboardButton("🟡 BEP20 (BSC)", callback_data=f"net_bep20_{plan_code}")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_start")],
    ]
    return InlineKeyboardMarkup(keyboard)


def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton(VIDEO_DARSLIK["label"], callback_data="video_darslik")],
        [InlineKeyboardButton("📈 VIP Signal", callback_data="vip_menu")],
        # url= bo'lgani uchun bosilganda to'g'ridan-to'g'ri boshqa botga o'tadi
        [InlineKeyboardButton("👤 Admin bilan bog'lanish", url=ADMIN_BOT_LINK)],
    ]
    return InlineKeyboardMarkup(keyboard)


def vip_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton(p["label"], callback_data=key)]
        for key, p in VIP_PLANS.items()
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_start")])
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        WELCOME_TEXT, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML
    )


# ============================================================
# TUGMALAR (CALLBACK) BOSHQARUVI
# ============================================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_to_start":
        context.user_data.clear()
        await query.edit_message_text(
            WELCOME_TEXT, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML
        )
        return

    if data == "vip_menu":
        text = VIP_INTRO_HEADER + "\n\n📊 Quyidagi obuna muddatini tanlang:"
        await query.edit_message_text(
            text, reply_markup=vip_menu_keyboard(), parse_mode=ParseMode.HTML
        )
        return

    if data == "video_darslik" or data in VIP_PLANS:
        plan_code = "video" if data == "video_darslik" else data
        label, price = get_plan_info(plan_code)

        if plan_code == "video":
            tavsif = VIDEO_TAVSIF
        else:
            tavsif = VIP_PLAN_TAVSIF[plan_code] + "\n\n" + VIP_SAFETY_NOTE

        text = (
            f"📦 <b>{label}</b>\n💰 Narxi: <b>{price}</b>\n\n"
            f"{tavsif}\n\n"
            "💳 To'lovni amalga oshirish uchun tarmoqni tanlang:"
        )
        await query.edit_message_text(
            text, reply_markup=network_keyboard(plan_code), parse_mode=ParseMode.HTML
        )
        return

    if data.startswith("net_"):
        _, network, plan_code = data.split("_", 2)
        label, price = get_plan_info(plan_code)
        wallet = WALLETS[network]
        network_name = "TRC20 (TRON)" if network == "trc20" else "BEP20 (BSC)"

        context.user_data["pending_plan"] = plan_code
        context.user_data["awaiting_receipt"] = True

        text = (
            f"📦 <b>{label}</b> — {price}\n\n"
            f"💳 <b>To'lov manzili ({network_name}):</b>\n"
            f"<code>{wallet}</code>\n\n"
            "⚠️ Manzilni nusxalashda tarmoqni to'g'ri tanlaganingizga ishonch "
            "hosil qiling — noto'g'ri tarmoqda yuborilgan mablag' qaytarilmaydi.\n\n"
            "✅ To'lovni amalga oshirgach, chek/screenshot rasmini shu chatga "
            "(bevosita botga) yuboring."
        )
        keyboard = [[InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_start")]]
        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
        )
        return


# ============================================================
# FOYDALANUVCHI CHEK RASMINI YUBORGANDA
# ============================================================
async def receipt_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_receipt"):
        return

    plan_code = context.user_data.get("pending_plan")
    label, price = get_plan_info(plan_code)
    user = update.effective_user
    photo = update.message.photo[-1]

    caption = (
        f"🔔 <b>Yangi to'lov cheki!</b>\n\n"
        f"👤 Foydalanuvchi: {user.full_name} (@{user.username})\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📦 Tanlangan: {label} ({price})\n\n"
        f"Tasdiqlash uchun:\n<code>/tasdiqla {user.id} {plan_code}</code>"
    )
    try:
        await context.bot.send_photo(
            ADMIN_CHAT_ID, photo.file_id, caption=caption, parse_mode=ParseMode.HTML
        )
    except TelegramError as e:
        logger.error("Chekni adminga yuborishda xatolik: %s", e)

    context.user_data["awaiting_receipt"] = False
    await update.message.reply_text(
        "✅ <b>Chekingiz qabul qilindi!</b>\n\n"
        "⏳ Hozir admin tomonidan tekshirilmoqda. Tasdiqlangach, guruhga "
        "qo'shilish havolasi avtomatik ravishda shu botga yuboriladi.",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# GURUHGA QO'SHILGANDA — DUO/TABRIK XABARI
# ============================================================
async def on_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if result is None:
        return

    chat_id = result.chat.id
    if chat_id not in (VIDEO_GROUP_ID, VIP_GROUP_ID):
        return

    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status

    just_joined = old_status in ("left", "kicked", "restricted") and new_status == "member"
    if not just_joined:
        return

    user = result.new_chat_member.user
    try:
        await context.bot.send_message(
            chat_id,
            WELCOME_DUA_TEXT.format(name=user.full_name),
            parse_mode=ParseMode.HTML,
        )
    except TelegramError as e:
        logger.error("Duo xabarini yuborishda xatolik: %s", e)


# ============================================================
# ADMIN: TO'LOVNI TASDIQLASH
# ============================================================
async def tasdiqla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return

    if len(context.args) != 2 or not context.args[0].isdigit():
        await update.message.reply_text("Foydalanish: /tasdiqla <user_id> <reja_kodi>")
        return

    target_user_id = int(context.args[0])
    plan_code = context.args[1]

    if plan_code == "video":
        chat_id = VIDEO_GROUP_ID
        plan_label = VIDEO_DARSLIK["label"]
        days = None
    elif plan_code in VIP_PLANS:
        chat_id = VIP_GROUP_ID
        plan_label = VIP_PLANS[plan_code]["label"]
        days = VIP_PLANS[plan_code]["days"]
    else:
        await update.message.reply_text("Noto'g'ri reja_kodi.")
        return

    try:
        invite_link = await context.bot.create_chat_invite_link(chat_id=chat_id, member_limit=1)
        await context.bot.send_message(
            target_user_id,
            "✅ <b>To'lovingiz tasdiqlandi!</b>\n\n"
            f"📦 {plan_label}\n"
            "Guruhga qo'shilish uchun quyidagi havoladan foydalaning "
            f"(bir martalik):\n{invite_link.invite_link}\n\n"
            "Sizni jamoamizda ko'rishdan mamnunmiz! 🤍",
            parse_mode=ParseMode.HTML,
        )
        add_subscription(target_user_id, chat_id, plan_label, days)
        muddat_text = "cheksiz" if days is None else f"{days} kun"
        await update.message.reply_text(
            f"✅ Tasdiqlandi. Havola yuborildi. Muddat: {muddat_text}"
        )
    except TelegramError as e:
        await update.message.reply_text(
            f"❌ Xatolik: {e}\nBot guruhda admin ekanligini tekshiring."
        )


# ============================================================
# HAR 6 SOATDA: MUDDATI TUGAGANLARNI CHIQARISH + ESLATMA
# ============================================================
async def check_subscriptions(context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    now = datetime.utcnow()
    expired_keys = []
    changed = False

    logger.info("Obunalar tekshirilmoqda: %d ta yozuv", len(data["subs"]))

    for key, sub in list(data["subs"].items()):
        if sub.get("expiry") is None:
            continue  # cheksiz reja

        user_id = sub.get("user_id") or int(key.split(":")[0])
        chat_id = sub["chat_id"]
        remaining = datetime.fromisoformat(sub["expiry"]) - now

        # 1) Muddat tugagan -> guruhdan chiqarish
        if remaining.total_seconds() <= 0:
            try:
                await context.bot.ban_chat_member(chat_id, user_id)
                await context.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
            except TelegramError as e:
                logger.error("Chiqarishda xatolik (user %s): %s", user_id, e)
                continue   # yozuv saqlanadi, keyingi tekshiruvda qayta urinadi

            expired_keys.append(key)
            logger.info("Muddati tugadi va chiqarildi: %s", user_id)
            try:
                await context.bot.send_message(
                    user_id,
                    f"⏰ <b>«{sub['plan']}» obunangiz muddati tugadi</b> va "
                    "guruhdan chiqarildingiz.\n\n"
                    "Qayta foydalanish uchun /start bosing va tarifni yangilang.",
                    parse_mode=ParseMode.HTML,
                )
            except TelegramError as e:
                logger.warning("Xabar yuborilmadi (user %s): %s", user_id, e)
            continue

        # 2) Muddat yaqinlashdi -> eslatma
        if remaining <= timedelta(days=REMINDER_WINDOW_DAYS):
            days_left = remaining.days
            hours_left = remaining.seconds // 3600
            qolgan = f"{days_left} kun {hours_left} soat" if days_left > 0 else f"{hours_left} soat"
            try:
                await context.bot.send_message(
                    user_id,
                    f"⏳ <b>Eslatma:</b> «{sub['plan']}» obunangiz muddati "
                    f"tugashiga <b>{qolgan}</b> qoldi.\n\n"
                    "Uzluksiz foydalanish uchun /start orqali tarifni yangilang.",
                    parse_mode=ParseMode.HTML,
                )
                sub["reminded"] = True
                changed = True
            except TelegramError as e:
                logger.error("Eslatma xatosi (user %s): %s", user_id, e)

    for key in expired_keys:
        del data["subs"][key]
        changed = True

    if changed:
        save_data(data)


# ============================================================
# ASOSIY ISHGA TUSHIRISH
# ============================================================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tasdiqla", tasdiqla))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, receipt_photo_handler))
    app.add_handler(ChatMemberHandler(on_chat_member_update, ChatMemberHandler.CHAT_MEMBER))

    app.job_queue.run_repeating(check_subscriptions, interval=CHECK_INTERVAL_SECONDS, first=10)

    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
