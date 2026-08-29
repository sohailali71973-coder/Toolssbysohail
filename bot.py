import sqlite3
import random
import logging
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)

# Configuration
BOT_TOKEN = "8659882105:AAFrCNFCjMM3hCWXlPPg9HdC1bc756XR0FQ"
ADMIN_ID = 7394600693
API_KEY = "MY_TEST_KEY_123"

# Setup Database
conn = sqlite3.connect("bot_database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    credits INTEGER DEFAULT 3,
    referred_by INTEGER,
    daily_time TEXT,
    spin_time TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS redeem_codes (
    code TEXT PRIMARY KEY,
    credits INTEGER,
    max_uses INTEGER,
    uses INTEGER DEFAULT 0
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS redeemed (
    user_id INTEGER,
    code TEXT
)
''')
conn.commit()

# Helper function to check and deduct credits
def deduct_credit(user_id):
    cursor.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if not res or res[0] < 1:
        return False
    cursor.execute("UPDATE users SET credits = credits - 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    return True

# --- API HANDLERS ---
async def fetch_pincode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("❌ Usage: /pincode 411001")
    
    if not deduct_credit(user_id):
        return await update.message.reply_text("❌ Insufficient Credits! Daily Claim ya Spin karke credits earn karo.")

    query = context.args[0]
    await update.message.reply_text("🔎 Fetching Pincode Info...")
    try:
        url = f"https://nitin-api-free-user-1k-spacial.vercel.app/api?type=pincode&search={query}"
        res = requests.get(url, timeout=10).text
        await update.message.reply_text(f"📍 **Pincode Result:**\n\n`{res[:3500]}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("❌ API Server Response Error.")

async def fetch_vehicle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("❌ Usage: /vehicle RJ14CV0002")

    if not deduct_credit(user_id):
        return await update.message.reply_text("❌ Insufficient Credits!")

    query = context.args[0]
    await update.message.reply_text("🔎 Fetching Vehicle Info...")
    try:
        url = f"https://nitin-api-free-user-1k-spacial.vercel.app/api?type=vehicle&search={query}"
        res = requests.get(url, timeout=10).text
        await update.message.reply_text(f"🚘 **Vehicle Result:**\n\n`{res[:3500]}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("❌ API Server Response Error.")

async def fetch_num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("❌ Usage: /num 9876543210")

    if not deduct_credit(user_id):
        return await update.message.reply_text("❌ Insufficient Credits!")

    query = context.args[0]
    await update.message.reply_text("🔎 Fetching Number Info...")
    try:
        url = f"https://nitin-developer-api-paid.nitinshab43.workers.dev/api?action=num&number={query}&key={API_KEY}"
        res = requests.get(url, timeout=10).text
        await update.message.reply_text(f"📞 **Number Result:**\n\n`{res[:3500]}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("❌ API Server Response Error.")

async def fetch_upi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("❌ Usage: /upi example@ybl")

    if not deduct_credit(user_id):
        return await update.message.reply_text("❌ Insufficient Credits!")

    query = context.args[0]
    await update.message.reply_text("🔎 Fetching UPI Info...")
    try:
        url = f"https://nitin-developer-api-paid.nitinshab43.workers.dev/api?action=upiinfo&upi={query}&key={API_KEY}"
        res = requests.get(url, timeout=10).text
        await update.message.reply_text(f"💳 **UPI Result:**\n\n`{res[:3500]}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("❌ API Server Response Error.")

async def fetch_id_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("❌ Usage: /id <12-digit-id>")

    if not deduct_credit(user_id):
        return await update.message.reply_text("❌ Insufficient Credits!")

    query = context.args[0]
    await update.message.reply_text("🔎 Fetching ID Info...")
    try:
        url = f"https://nitin-developer-api-paid.nitinshab43.workers.dev/api?action=aadhar&aadhar={query}&key={API_KEY}"
        res = requests.get(url, timeout=10).text
        await update.message.reply_text(f"🆔 **ID Search Result:**\n\n`{res[:3500]}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("❌ API Server Response Error.")

# --- BASE BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user.id,))
    db_user = cursor.fetchone()

    if not db_user:
        ref_id = None
        if args and args[0].startswith("ref_"):
            try:
                ref_id = int(args[0].replace("ref_", ""))
                if ref_id == user.id:
                    ref_id = None
            except:
                ref_id = None

        cursor.execute(
            "INSERT INTO users (user_id, username, credits, referred_by) VALUES (?, ?, 3, ?)",
            (user.id, user.username or user.first_name, ref_id)
        )
        if ref_id:
            cursor.execute("UPDATE users SET credits = credits + 2 WHERE user_id = ?", (ref_id,))
            try:
                await context.bot.send_message(chat_id=ref_id, text="🎉 Naya user aapke link se join hua! +2 CREDITS!")
            except:
                pass
        conn.commit()

    cursor.execute("SELECT credits FROM users WHERE user_id = ?", (user.id,))
    credits = cursor.fetchone()[0]

    keyboard = [
        [InlineKeyboardButton("🎁 Daily Claim", callback_data="daily"), InlineKeyboardButton("🎰 Spin Wheel", callback_data="spin")],
        [InlineKeyboardButton("👤 My Profile", callback_data="profile"), InlineKeyboardButton("🔗 Refer Link", callback_data="refer")],
        [InlineKeyboardButton("🔑 Redeem Code Info", callback_data="redeem_info")]
    ]

    msg = (
        f"👋 Hey {user.first_name}!\n\n"
        f"Your Credits: 💎 {credits}\n\n"
        f"⚡ **Available Commands:**\n"
        f"• `/pincode 411001`\n"
        f"• `/vehicle RJ14CV0002`\n"
        f"• `/num 9876543210`\n"
        f"• `/upi example@ybl`\n"
        f"• `/id <12-digit-id>`"
    )

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    today = datetime.now().strftime("%Y-%m-%d")

    if query.data == "profile":
        cursor.execute("SELECT credits, username FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        await query.message.reply_text(f"👤 USER PROFILE\n\n🆔 ID: {user_id}\n👤 Name: {res[1]}\n💎 Credits: {res[0]}")

    elif query.data == "refer":
        bot_user = await context.bot.get_me()
        link = f"https://t.me/{bot_user.username}?start=ref_{user_id}"
        await query.message.reply_text(f"🔗 YOUR REFERRAL LINK\n\nShare link to get 2 Credits per refer:\n{link}")

    elif query.data == "daily":
        cursor.execute("SELECT daily_time FROM users WHERE user_id = ?", (user_id,))
        last_daily = cursor.fetchone()[0]
        if last_daily == today:
            await query.message.reply_text("❌ Aaj ka Daily Claim pehle hi le chuke ho!")
        else:
            cursor.execute("UPDATE users SET credits = credits + 1, daily_time = ? WHERE user_id = ?", (today, user_id))
            conn.commit()
            await query.message.reply_text("🎉 Daily Reward: +1 Credit Claimed!")

    elif query.data == "spin":
        cursor.execute("SELECT spin_time FROM users WHERE user_id = ?", (user_id,))
        last_spin = cursor.fetchone()[0]
        if last_spin == today:
            await query.message.reply_text("❌ Aaj ka Spin complete ho chuka hai!")
        else:
            reward = random.randint(1, 4)
            cursor.execute("UPDATE users SET credits = credits + ?, spin_time = ? WHERE user_id = ?", (reward, today, user_id))
            conn.commit()
            await query.message.reply_text(f"🎰 Spin Result: +{reward} Credits Won!")

    elif query.data == "redeem_info":
        await query.message.reply_text("🔑 REDEEM CODE\n\nCode use karne ke liye type karo:\n/redeem YOUR_CODE")

async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("❌ Code format: /redeem YOUR_CODE")
    
    code_input = context.args[0]
    cursor.execute("SELECT credits, max_uses, uses FROM redeem_codes WHERE code = ?", (code_input,))
    code_data = cursor.fetchone()

    if not code_data:
        return await update.message.reply_text("❌ Invalid ya Expired Code!")

    credits, max_uses, uses = code_data
    if uses >= max_uses:
        return await update.message.reply_text("❌ Code limit full ho gayi hai!")

    cursor.execute("SELECT * FROM redeemed WHERE user_id = ? AND code = ?", (user_id, code_input))
    if cursor.fetchone():
        return await update.message.reply_text("❌ Code pehle hi redeem kar chuke ho!")

    cursor.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (credits, user_id))
    cursor.execute("UPDATE redeem_codes SET uses = uses + 1 WHERE code = ?", (code_input,))
    cursor.execute("INSERT INTO redeemed (user_id, code) VALUES (?, ?)", (user_id, code_input))
    conn.commit()

    await update.message.reply_text(f"🎉 Success! Got +{credits} Credits!")

# Admin Command (/gen CODE CREDITS MAX_USES)
async def gen_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        code = context.args[0]
        credits = int(context.args[1])
        max_uses = int(context.args[2]) if len(context.args) > 2 else 1

        cursor.execute("INSERT INTO redeem_codes (code, credits, max_uses) VALUES (?, ?, ?)", (code, credits, max_uses))
        conn.commit()
        await update.message.reply_text(f"✅ Code Created: {code}\nCredits: {credits}\nMax Uses: {max_uses}")
    except Exception as e:
        await update.message.reply_text("❌ Usage: /gen CODE CREDITS MAX_USES")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Base Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("redeem", redeem))
    app.add_handler(CommandHandler("gen", gen_code))
    
    # API Commands
    app.add_handler(CommandHandler("pincode", fetch_pincode))
    app.add_handler(CommandHandler("vehicle", fetch_vehicle))
    app.add_handler(CommandHandler("num", fetch_num))
    app.add_handler(CommandHandler("upi", fetch_upi))
    app.add_handler(CommandHandler("id", fetch_id_info))

    app.add_handler(CallbackQueryHandler(button_click))

    print("🤖 Starting Bot with API Handlers...")
    
    # Python 3.13 compatibility fix for polling
    app.run_polling(drop_pending_updates=True, close_loop=False)
