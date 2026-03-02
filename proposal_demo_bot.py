import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# ---------- CONFIG ----------
TOKEN = "8363494220:AAHioUmRhxz1waJDPdVBKycVtfccG5zhVMw"
ADMIN_ID = 909881648
TELEBIRR_NUMBERS = ["0953626153", "0962892238"]
# ----------------------------

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

user_balances = {}
pending_deposits = {}
pending_buys = {}
pending_sells = {}
user_state = {}

# ---------- HOME MENU ----------
def home_keyboard():
    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("📥 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("📲 Buy Airtime", callback_data="buy_airtime")],
        [InlineKeyboardButton("📤 Sell Airtime", callback_data="sell_airtime")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "✨ *Welcome to Mebatech Airtime Bot!* ✨\n\n"
        "Buy, Sell or Deposit airtime safely.\n"
        "All transactions require admin approval."
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=home_keyboard())

# ---------- USER BUTTON HANDLER ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # BALANCE
    if query.data == "balance":
        balance = user_balances.get(user_id, 0)
        await query.edit_message_text(
            f"💵 Your balance: {balance} ETB",
            reply_markup=home_keyboard()
        )

    # DEPOSIT
    elif query.data == "deposit":
        user_state[user_id] = "deposit_amount"
        await query.edit_message_text("📥 Enter deposit amount:")

    # BUY
    elif query.data == "buy_airtime":
        user_state[user_id] = "buy_amount"
        await query.edit_message_text("📲 Enter airtime amount to buy:")

    # SELL
    elif query.data == "sell_airtime":
        user_state[user_id] = "sell_amount"
        await query.edit_message_text("📤 Enter airtime amount to sell:")

    # DONE BUTTONS
    elif query.data.startswith("done_deposit_"):
        amount = int(query.data.split("_")[-1])
        user_state[user_id] = "deposit_screenshot"
        await query.edit_message_text(
            f"📱 Send Telebirr screenshot for {amount} ETB\n"
            f"Numbers: {', '.join(TELEBIRR_NUMBERS)}"
        )

    elif query.data.startswith("done_buy_"):
        amount = int(query.data.split("_")[-1])
        user_state[user_id] = "buy_screenshot"
        await query.edit_message_text(
            f"📱 Send Telebirr screenshot for {amount} ETB\n"
            f"Numbers: {', '.join(TELEBIRR_NUMBERS)}"
        )

    elif query.data.startswith("done_sell_"):
        parts = query.data.split("_")
        receive_amount = int(parts[-2])
        amount = int(parts[-1])
        user_state[user_id] = "sell_screenshot"
        await query.edit_message_text(
            f"📱 Send airtime screenshot\n"
            f"You will receive {receive_amount} ETB after approval."
        )

    # CANCEL (FULL FIX)
    elif query.data == "cancel":
        user_state[user_id] = None
        pending_deposits.pop(user_id, None)
        pending_buys.pop(user_id, None)
        pending_sells.pop(user_id, None)

        await query.edit_message_text(
            "❌ Transaction cancelled.",
            reply_markup=home_keyboard()
        )

# ---------- TEXT HANDLER ----------
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    state = user_state.get(user_id)

    if state is None:
        await update.message.reply_text("⚡ Back to Home.", reply_markup=home_keyboard())
        return

    # DEPOSIT AMOUNT
    if state == "deposit_amount":
        if not text.isdigit():
            await update.message.reply_text("❌ Enter valid number.")
            return

        amount = int(text)
        pending_deposits[user_id] = {"amount": amount}
        user_state[user_id] = None

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Done", callback_data=f"done_deposit_{amount}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ])

        await update.message.reply_text(
            f"Send {amount} ETB to: {', '.join(TELEBIRR_NUMBERS)}",
            reply_markup=keyboard
        )

    # BUY
    elif state == "buy_amount":
        if not text.isdigit():
            await update.message.reply_text("❌ Enter valid number.")
            return

        amount = int(text)
        pay_amount = int(amount * 0.9)
        balance = user_balances.get(user_id, 0)

        if balance < pay_amount:
            await update.message.reply_text("❌ Insufficient balance.", reply_markup=home_keyboard())
            user_state[user_id] = None
            return

        pending_buys[user_id] = {"amount": amount, "pay_amount": pay_amount}
        user_state[user_id] = None

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Done", callback_data=f"done_buy_{pay_amount}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ])

        await update.message.reply_text(
            f"Send {pay_amount} ETB to: {', '.join(TELEBIRR_NUMBERS)}",
            reply_markup=keyboard
        )

    # SELL
    elif state == "sell_amount":
        if not text.isdigit():
            await update.message.reply_text("❌ Enter valid number.")
            return

        amount = int(text)
        receive_amount = int(amount * 0.8)

        pending_sells[user_id] = {"amount": amount, "receive_amount": receive_amount}
        user_state[user_id] = None

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Done", callback_data=f"done_sell_{receive_amount}_{amount}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ])

        await update.message.reply_text(
            f"You will receive {receive_amount} ETB after approval.",
            reply_markup=keyboard
        )

# ---------- PHOTO HANDLER ----------
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    state = user_state.get(user_id)

    if state not in ["deposit_screenshot", "buy_screenshot", "sell_screenshot"]:
        return

    photo = await update.message.photo[-1].get_file()
    screenshot = await photo.download_as_bytearray()

    if state == "deposit_screenshot":
        amount = pending_deposits[user_id]["amount"]
        await context.bot.send_photo(
            ADMIN_ID,
            photo=InputFile(screenshot),
            caption=f"Deposit from {user_id}\nAmount: {amount} ETB"
        )

    elif state == "buy_screenshot":
        amount = pending_buys[user_id]["amount"]
        await context.bot.send_photo(
            ADMIN_ID,
            photo=InputFile(screenshot),
            caption=f"Buy request from {user_id}\nAmount: {amount} ETB"
        )

    elif state == "sell_screenshot":
        amount = pending_sells[user_id]["amount"]
        receive = pending_sells[user_id]["receive_amount"]
        await context.bot.send_photo(
            ADMIN_ID,
            photo=InputFile(screenshot),
            caption=f"Sell request from {user_id}\nAmount: {amount}\nReceive: {receive}"
        )

    await update.message.reply_text("✅ Sent for admin approval.", reply_markup=home_keyboard())
    user_state[user_id] = None

# ---------- ADMIN ----------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Not authorized.")
        return

    text = "📋 Pending Transactions\n"
    keyboard = []

    for uid, txn in pending_deposits.items():
        text += f"\nDeposit | {uid} | {txn['amount']} ETB"
        keyboard.append([
            InlineKeyboardButton("Approve", callback_data=f"approve_deposit_{uid}"),
            InlineKeyboardButton("Reject", callback_data=f"reject_deposit_{uid}")
        ])

    if keyboard:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("No pending transactions.")

async def admin_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("❌ Not authorized.")
        return

    parts = query.data.split("_")
    action, type_txn, uid = parts
    uid = int(uid)

    if action == "approve" and type_txn == "deposit":
        user_balances[uid] = user_balances.get(uid, 0) + pending_deposits[uid]["amount"]
        pending_deposits.pop(uid)
        await query.edit_message_text("✅ Deposit approved.")

    elif action == "reject" and type_txn == "deposit":
        pending_deposits.pop(uid)
        await query.edit_message_text("❌ Deposit rejected.")

# ---------- MAIN ----------
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))

    app.add_handler(CallbackQueryHandler(admin_button, pattern="^(approve|reject)_"))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(balance|deposit|buy_airtime|sell_airtime|done_.*|cancel)$"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    print("Bot running...")
    app.run_polling()