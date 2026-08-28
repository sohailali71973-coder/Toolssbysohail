import os
import sqlite3
import random
import html
from datetime import datetime, timedelta, timezone

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==================================================
# CONFIG
# ==================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

INSTAGRAM_URL = "https://www.instagram.com/Clip2editz/"
DATABASE = "bot.db"

STARTING_CREDITS = 3
DAILY_REWARD = 1
REFERRAL_REWARD = 3

# Naye APIs Update kar diye hain:
API_KEY = "MY_TEST_KEY_123"
API3_URL = f"https://nitin-developer-api-paid.nitinshab43.workers.dev/api?action=num&key={API_KEY}&number="
API4_URL = f"https://nitin-developer-api-paid.nitinshab43.workers.dev/api?action=aadhar&key={API_KEY}&aadhar="
API5_URL = f"https://nitin-developer-api-paid.nitinshab43.workers.dev/api?action=upiinfo&key={API_KEY}&upi="


# ==================================================
# DATABASE
# ==================================================

def get_db():
    return sqlite3.connect(DATABASE)


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            credits INTEGER DEFAULT 3,
            verified INTEGER DEFAULT 0,
            referred_by INTEGER,
            referral_rewarded INTEGER DEFAULT 0,
            daily_time TEXT,
            spin_time TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS redeem_codes (
            code TEXT PRIMARY KEY,
            credits INTEGER NOT NULL,
            max_uses INTEGER NOT NULL,
            uses INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS redeemed (
            user_id INTEGER,
            code TEXT,
            PRIMARY KEY (user_id, code)
        )
    """)

    conn.commit()
    conn.close()


def create_user(user_id, username, referred_by=None):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    existing = cur.fetchone()

    if not existing:
        cur.execute("""
            INSERT INTO users (user_id, username, credits, referred_by)
            VALUES (?, ?, ?, ?)
        """, (user_id, username or "", STARTING_CREDITS, referred_by))

    conn.commit()
    conn.close()


def get_credits(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def add_credits(user_id, amount):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()


def remove_one_credit(user_id):
    credits = get_credits(user_id)
    if credits < 1:
        return False
    add_credits(user_id, -1)
    return True


# ==================================================
# KEYBOARDS
# ==================================================

def verify_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Follow Instagram", url=INSTAGRAM_URL)],
        [InlineKeyboardButton("✅ Verify & Continue", callback_data="verify")]
    ])


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 API Check", callback_data="api_menu")],
        [
            InlineKeyboardButton("💰 My Credits", callback_data="credits"),
            InlineKeyboardButton("👥 Refer & Earn", callback_data="refer")
        ],
        [
            InlineKeyboardButton("🎁 Daily Claim", callback_data="daily"),
            InlineKeyboardButton("🎰 Spin & Win", callback_data="spin")
        ],
        [InlineKeyboardButton("🎟 Redeem Claim", callback_data="redeem")]
    ])


def api_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚗 Vehicle Search", callback_data="vehicle")],
        [InlineKeyboardButton("📍 Pincode Search", callback_data="pincode")],
        [
            InlineKeyboardButton("📱 Mobile Search", callback_data="api3"),
            InlineKeyboardButton("🆔 ID Search", callback_data="api4")
        ],
        [InlineKeyboardButton("💳 UPI Search", callback_data="api5")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ])


def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Bot Stats", callback_data="stats")],
        [InlineKeyboardButton("➕ Add Credits", callback_data="admin_add")],
        [InlineKeyboardButton("🎟 Create Redeem", callback_data="admin_redeem")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
    ])


def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])


def api_back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="api_menu")]])


# ==================================================
# START COMMAND
# ==================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    referred_by = None

    if context.args:
        try:
            possible_referrer = int(context.args[0])
            if possible_referrer != user.id:
                referred_by = possible_referrer
        except ValueError:
            pass

    create_user(user.id, user.username, referred_by)

    await update.message.reply_text(
        "⚡ <b>WELCOME TO API BOT</b> ⚡\n\n"
        "🔐 Access lene se pehle hamara Instagram follow karein.\n\n"
        "📸 Instagram: @Clip2editz\n\n"
        "━━━━━━━━━━━━━━\n"
        "〆 <b>DEVELOPER : SOHAIL</b>",
        parse_mode="HTML",
        reply_markup=verify_keyboard()
    )


# ==================================================
# MAIN CALLBACK HANDLER
# ==================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data

    await query.answer()

    if data == "verify":
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE users SET verified = 1 WHERE user_id = ?", (user.id,))
        cur.execute("SELECT referred_by, referral_rewarded FROM users WHERE user_id = ?", (user.id,))
        row = cur.fetchone()

        if row and row[0] and row[1] == 0 and row[0] != user.id:
            cur.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (REFERRAL_REWARD, row[0]))
            cur.execute("UPDATE users SET referral_rewarded = 1 WHERE user_id = ?", (user.id,))

        conn.commit()
        conn.close()

        await query.edit_message_text(
            "✅ <b>Verification Successful!</b>\n\n"
            "Welcome! Ab API aur baaki options access kar sakte ho. 😎\n\n"
            "〆 <b>DEVELOPER : SOHAIL</b>",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
        return

    if data == "back":
        credits = get_credits(user.id)
        await query.edit_message_text(
            "🏠 <b>MAIN MENU</b>\n\n"
            f"💰 Available Credits: <b>{credits}</b>\n\n"
            "Option select karo 👇\n\n"
            "〆 <b>DEVELOPER : SOHAIL</b>",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
        return

    if data == "api_menu":
        await query.edit_message_text(
            "🔍 <b>API CHECK</b>\n\n"
            "Koi bhi API option select karo.\n\n"
            "💳 Successful search = <b>1 Credit</b>\n\n"
            "〆 <b>DEVELOPER : SOHAIL</b>",
            parse_mode="HTML",
            reply_markup=api_menu()
        )
        return

    if data == "credits":
        credits = get_credits(user.id)
        await query.answer(f"💰 Tumhare paas {credits} Credits hain!", show_alert=True)
        return

    if data == "refer":
        bot_info = await context.bot.get_me()
        referral_link = f"https://t.me/{bot_info.username}?start={user.id}"
        await query.edit_message_text(
            "👥 <b>REFER & EARN</b>\n\n"
            "Apna referral link share karo.\n\n"
            f"🎁 Har successful referral = <b>+{REFERRAL_REWARD} Credits</b>\n\n"
            f"🔗 <code>{referral_link}</code>\n\n"
            "〆 <b>DEVELOPER : SOHAIL</b>",
            parse_mode="HTML",
            reply_markup=back_button()
        )
        return

    if data == "daily":
        await handle_daily(query, user.id)
        return

    if data == "spin":
        await handle_spin(query, user.id)
        return

    if data == "redeem":
        context.user_data["waiting_for"] = "redeem"
        await query.edit_message_text(
            "🎟 <b>REDEEM CLAIM</b>\n\n"
            "Apna redeem code bhejo 👇\n\n"
            "Example: <code>WELCOME10</code>",
            parse_mode="HTML",
            reply_markup=back_button()
        )
        return

    # --- SEARCH PROMPTS ---
    if data == "vehicle":
        context.user_data["waiting_for"] = "vehicle"
        await query.edit_message_text(
            "🚗 <b>VEHICLE SEARCH</b>\n\n"
            "Vehicle number bhejo.\n\nExample: <code>RJ14CV0002</code>\n\n💳 Cost: <b>1 Credit</b>",
            parse_mode="HTML",
            reply_markup=api_back_button()
        )
        return

    if data == "pincode":
        context.user_data["waiting_for"] = "pincode"
        await query.edit_message_text(
            "📍 <b>PINCODE SEARCH</b>\n\n"
            "Pincode bhejo.\n\nExample: <code>411001</code>\n\n💳 Cost: <b>1 Credit</b>",
            parse_mode="HTML",
            reply_markup=api_back_button()
        )
        return

    if data == "api3":
        context.user_data["waiting_for"] = "api3"
        await query.edit_message_text(
            "📱 <b>MOBILE SEARCH</b>\n\n"
            "10 Digit Mobile Number bhejo.\n\nExample: <code>9876543210</code>\n\n💳 Cost: <b>1 Credit</b>",
            parse_mode="HTML",
            reply_markup=api_back_button()
        )
        return

    if data == "api4":
        context.user_data["waiting_for"] = "api4"
        await query.edit_message_text(
            "🆔 <b>ID SEARCH</b>\n\n"
            "12 Digit Number bhejo.\n\nExample: <code>327567544017</code>\n\n💳 Cost: <b>1 Credit</b>",
            parse_mode="HTML",
            reply_markup=api_back_button()
        )
        return

    if data == "api5":
        context.user_data["waiting_for"] = "api5"
        await query.edit_message_text(
            "💳 <b>UPI SEARCH</b>\n\n"
            "UPI ID bhejo.\n\nExample: <code>example@ybl</code>\n\n💳 Cost: <b>1 Credit</b>",
            parse_mode="HTML",
            reply_markup=api_back_button()
        )
        return

    # --- ADMIN HANDLERS ---
    if data == "admin":
        if user.id != ADMIN_ID:
            return
        await query.edit_message_text("👑 <b>ADMIN PANEL</b>\n\nDeveloper Sohail Control Panel", parse_mode="HTML", reply_markup=admin_menu())
        return

    if data == "stats":
        if user.id != ADMIN_ID:
            return
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        conn.close()
        await query.answer(f"📊 Total Users: {total_users}", show_alert=True)
        return

    if data == "admin_add":
        if user.id != ADMIN_ID:
            return
        context.user_data["waiting_for"] = "admin_add"
        await query.edit_message_text("➕ <b>ADD CREDITS</b>\n\nFormat: <code>USER_ID AMOUNT</code>", parse_mode="HTML")
        return

    if data == "admin_redeem":
        if user.id != ADMIN_ID:
            return
        context.user_data["waiting_for"] = "admin_redeem"
        await query.edit_message_text("🎟 <b>CREATE REDEEM CODE</b>\n\nFormat: <code>CODE CREDITS MAX_USES</code>", parse_mode="HTML")
        return


# ==================================================
# DAILY CLAIM LOGIC
# ==================================================

async def handle_daily(query, user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT daily_time FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    now = datetime.now(timezone.utc)

    if row and row[0]:
        last_time = datetime.fromisoformat(row[0])
        if now - last_time < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last_time)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            conn.close()
            await query.answer(f"⏳ Already claimed!\nWait {hours}h {minutes}m", show_alert=True)
            return

    cur.execute("UPDATE users SET credits = credits + ?, daily_time = ? WHERE user_id = ?", (DAILY_REWARD, now.isoformat(), user_id))
    conn.commit()
    conn.close()
    await query.answer(f"🎉 Daily Claim Successful!\n+{DAILY_REWARD} Credit", show_alert=True)


# ==================================================
# SPIN LOGIC
# ==================================================

async def handle_spin(query, user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT spin_time FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    now = datetime.now(timezone.utc)

    if row and row[0]:
        last_time = datetime.fromisoformat(row[0])
        if now - last_time < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last_time)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            conn.close()
            await query.answer(f"⏳ Spin already used!\nWait {hours}h {minutes}m", show_alert=True)
            return

    reward = random.randint(1, 5)
    cur.execute("UPDATE users SET credits = credits + ?, spin_time = ? WHERE user_id = ?", (reward, now.isoformat(), user_id))
    conn.commit()
    conn.close()
    await query.answer(f"🎰 SPIN RESULT!\n\n🎉 You won +{reward} Credits!", show_alert=True)


# ==================================================
# TEXT HANDLER (APIs & ADMIN INPUTS)
# ==================================================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    waiting_for = context.user_data.get("waiting_for")

    if not waiting_for:
        return

    # Generic API Fetcher Function
    async def fetch_api_result(api_endpoint, title_name):
        context.user_data.pop("waiting_for", None)
        if get_credits(user.id) < 1:
            await update.message.reply_text("❌ Tumhare paas enough credits nahi hain.")
            return

        try:
            url = f"{api_endpoint}{text}"
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            result = response.json()

            if not remove_one_credit(user.id):
                await update.message.reply_text("❌ Credit error.")
                return

            safe_result = html.escape(str(result))
            await update.message.reply_text(
                f"🔎 <b>{title_name} RESULT</b>\n\n"
                f"<pre>{safe_result}</pre>\n\n"
                f"💰 Remaining Credits: <b>{get_credits(user.id)}</b>\n\n"
                "〆 <b>DEVELOPER : SOHAIL</b>",
                parse_mode="HTML"
            )
        except Exception:
            await update.message.reply_text("❌ API request failed. Please try again later.")

    # Route Actions
    if waiting_for == "vehicle":
        await fetch_api_result("https://nitin-api-free-user-1k-spacial.vercel.app/api?type=vehicle&search=", "VEHICLE")
        return

    if waiting_for == "pincode":
        await fetch_api_result("https://nitin-api-free-user-1k-spacial.vercel.app/api?type=pincode&search=", "PINCODE")
        return

    if waiting_for == "api3":
        await fetch_api_result(API3_URL, "MOBILE SEARCH")
        return

    if waiting_for == "api4":
        await fetch_api_result(API4_URL, "ID SEARCH")
        return

    if waiting_for == "api5":
        await fetch_api_result(API5_URL, "UPI SEARCH")
        return

    # Redeem Handler
    if waiting_for == "redeem":
        context.user_data.pop("waiting_for", None)
        code = text.upper()
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT credits, max_uses, uses, active FROM redeem_codes WHERE code = ?", (code,))
        row = cur.fetchone()

        if not row:
            conn.close()
            await update.message.reply_text("❌ Invalid Redeem Code.")
            return

        credits, max_uses, uses, active = row
        cur.execute("SELECT 1 FROM redeemed WHERE user_id = ? AND code = ?", (user.id, code))
        already_used = cur.fetchone()

        if active == 0 or uses >= max_uses or already_used:
            conn.close()
            await update.message.reply_text("❌ Code expired, unavailable or already used.")
            return

        cur.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (credits, user.id))
        cur.execute("UPDATE redeem_codes SET uses = uses + 1 WHERE code = ?", (code,))
        cur.execute("INSERT INTO redeemed (user_id, code) VALUES (?, ?)", (user.id, code))
        conn.commit()
        conn.close()

        await update.message.reply_text(
            f"🎉 <b>Redeem Successful!</b>\n\n➕ {credits} Credits added!\n💰 Total Credits: <b>{get_credits(user.id)}</b>",
            parse_mode="HTML"
        )
        return

    # Admin Controls
    if waiting_for == "admin_add":
        if user.id != ADMIN_ID:
            return
        context.user_data.pop("waiting_for", None)
        try:
            target_user_id, amount = map(int, text.split())
            add_credits(target_user_id, amount)
            await update.message.reply_text(f"✅ {amount} credits added to <code>{target_user_id}</code>", parse_mode="HTML")
        except Exception:
            await update.message.reply_text("❌ Wrong format.\nExample: <code>123456789 10</code>", parse_mode="HTML")
        return

    if waiting_for == "admin_redeem":
        if user.id != ADMIN_ID:
            return
        context.user_data.pop("waiting_for", None)
        try:
            code, credits, max_uses = text.split()
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO redeem_codes (code, credits, max_uses, uses, active)
                VALUES (?, ?, ?, 0, 1)
            """, (code.upper(), int(credits), int(max_uses)))
            conn.commit()
            conn.close()
            await update.message.reply_text(
                f"✅ <b>Redeem Created!</b>\n\n🎟 Code: <code>{code.upper()}</code>\n💰 Credits: {credits}\n👥 Max Uses: {max_uses}",
                parse_mode="HTML"
            )
        except Exception:
            await update.message.reply_text("❌ Wrong format.\nExample: <code>WELCOME10 10 100</code>", parse_mode="HTML")
        return


# ==================================================
# ADMIN COMMAND
# ==================================================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("👑 <b>ADMIN PANEL</b>\n\nDeveloper Sohail Control Panel", parse_mode="HTML", reply_markup=admin_menu())


# ==================================================
# RUN BOT
# ==================================================

def main():
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN is missing!")
        return

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
