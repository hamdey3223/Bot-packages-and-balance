from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from telegram.constants import ParseMode
from datetime import datetime
import csv
from io import BytesIO

# إعدادات البوت
BOT_TOKEN = "7845079461:AAGunkhjcJg3Flp-Ri_63zm9j2oBXFtdDV0"
ADMIN_ID = 934143714
WHATSAPP_NUMBER = "201095587980"

orders = []

vodafone_offer = ("رصيد فودافون", "🔴 فودافون: 100 رصيد بـ 120 جنيه")
etisalat_offer = ("رصيد اتصالات", "🟢 اتصالات: 100 رصيد بـ 125 جنيه")

flex_packages = [
    ("فليكس 40", "1000 فليكس - 50 جنيه"),
    ("فليكس 45", "1500 فليكس - 60 جنيه"),
    ("فليكس 70", "3000 فليكس - 85 جنيه"),
    ("فليكس 100", "5000 فليكس - 120 جنيه"),
    ("فليكس 150", "8000 فليكس - 180 جنيه"),
    ("فليكس 300", "21000 فليكس - 350 جنيه"),
]

FLEX_NOTE = (
    "📌 ملاحظة:\n"
    "1 فليكس = 1 ميجا أو دقيقة فودافون أو رسالة\n"
    "5 فليكس = دقيقة لأي شبكة أو للخط الأرضي"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("عروض رصيد", callback_data="offers")],
        [InlineKeyboardButton("باقات فليكس", callback_data="flex")],
    ]
    await update.message.reply_text(
        "أهلاً بيك 👋\nاختر نوع العرض اللي يناسبك:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "offers":
        keyboard = [
            [InlineKeyboardButton("📲 اطلب فودافون", callback_data="order_Vodafone")],
            [InlineKeyboardButton("📲 اطلب اتصالات", callback_data="order_Etisalat")],
        ]
        offers_text = f"{vodafone_offer[1]}\n{etisalat_offer[1]}"
        await query.edit_message_text(
            text=offers_text, reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "flex":
        keyboard = [[InlineKeyboardButton(name, callback_data=f"flex_{name}")]
                    for name, _ in flex_packages]
        await query.edit_message_text(
            "اختر باقة الفليكس اللي تناسبك:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("flex_"):
        selected = query.data.split("_", 1)[1]
        for name, desc in flex_packages:
            if name == selected:
                reply_markup = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🛒 اطلب الباقة", callback_data=f"order_{name}")]]
                )
                await query.edit_message_text(f"{name}:\n{desc}\n\n{FLEX_NOTE}", reply_markup=reply_markup)
                break

    elif query.data.startswith("order_"):
        offer_name = query.data.split("_", 1)[1]
        context.user_data["selected_offer"] = offer_name

        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("📱 ارسال رقمي", request_contact=True)]],
            one_time_keyboard=True,
            resize_keyboard=True,
        )
        await query.message.reply_text(
            "من فضلك شارك رقم موبايلك علشان نكمل الطلب 👇",
            reply_markup=keyboard
        )

    elif query.data == "export_excel":
        user_id = query.from_user.id
        if user_id != ADMIN_ID:
            await query.answer("❌ غير مصرح لك.", show_alert=True)
            return
        if not orders:
            await query.edit_message_text("📭 لا توجد بيانات لتصديرها.")
            return
        output = BytesIO()
        writer = csv.writer(output)
        writer.writerow(["الاسم", "معرف المستخدم", "رقم الهاتف", "العرض", "التاريخ"])
        for row in orders:
            writer.writerow(row)
        output.seek(0)
        await query.message.reply_document(
            document=output,
            filename="طلبات_البوت.csv",
            caption="📄 تم تصدير الطلبات بنجاح."
        )

    elif query.data == "clear_data":
        if query.from_user.id != ADMIN_ID:
            await query.answer("❌ غير مصرح لك.", show_alert=True)
            return
        confirm_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ نعم، احذف الكل", callback_data="confirm_clear")],
            [InlineKeyboardButton("❌ لا، رجوع", callback_data="cancel_clear")],
        ])
        await query.edit_message_text("⚠️ هل أنت متأكد من حذف جميع الطلبات؟", reply_markup=confirm_keyboard)

    elif query.data == "confirm_clear":
        if query.from_user.id == ADMIN_ID:
            orders.clear()
            await query.edit_message_text("🗑️ تم حذف جميع الطلبات بنجاح.")

    elif query.data == "cancel_clear":
        await admin_panel(update, context)

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    phone = contact.phone_number
    user = update.message.from_user

    # ✅ لا يُسمح بإرسال الرقم إلا بعد اختيار عرض
    selected_offer = context.user_data.get("selected_offer")
    if not selected_offer:
        await update.message.reply_text("❗ من فضلك اختر العرض أولاً قبل إرسال رقم الهاتف.")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    context.user_data["order_details"] = {
        "name": user.full_name,
        "user_id": user.id,
        "phone": phone,
        "offer": selected_offer,
        "datetime": now,
    }

    await update.message.reply_text(
        "💳 برجاء تحويل المبلغ إلى رقم فودافون كاش التالي:\n"
        "📱 01095587980\n\n"
        "ثم قم بإرسال صورة (سكرين شوت) لعملية التحويل هنا داخل الشات."
    )

async def handle_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    if "order_details" not in context.user_data:
        await update.message.reply_text("❌ لا يوجد طلب مسجل حالياً. من فضلك أرسل الطلب أولاً.")
        return

    photo_file = await update.message.photo[-1].get_file()
    order = context.user_data["order_details"]

    orders.append([
        order['name'],
        order['user_id'],
        order['phone'],
        order['offer'],
        order['datetime']
    ])

    await update.message.reply_text(
        f"✅ تم استلام طلبك:\n"
        f"العرض: {order['offer']}\n"
        f"رقم الهاتف: {order['phone']}\n\n"
        f"سيتم التواصل معك قريباً عبر واتساب."
    )

    caption = (
        f"🆕 طلب جديد مع صورة تحويل:\n"
        f"👤 الاسم: {order['name']}\n"
        f"🆔 المعرف: {order['user_id']}\n"
        f"📞 الهاتف: {order['phone']}\n"
        f"🎁 العرض: {order['offer']}\n"
        f"🕒 التاريخ: {order['datetime']}\n"
        f"💬 واتساب: https://wa.me/{order['phone']}"
    )

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_file.file_id,
        caption=caption
    )

    context.user_data.pop("order_details", None)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    if user_id != ADMIN_ID:
        await update.callback_query.answer("❌ غير مصرح لك.", show_alert=True)
        return
    keyboard = [
        [InlineKeyboardButton("📄 تصدير الطلبات (CSV)", callback_data="export_excel")],
        [InlineKeyboardButton("🗑️ حذف جميع الطلبات", callback_data="clear_data")],
    ]
    await update.callback_query.edit_message_text(
        "👨‍💼 لوحة تحكم الأدمن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

if __name__ == "__main__":
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_buttons))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.PHOTO, handle_payment_screenshot))

    application.run_polling()