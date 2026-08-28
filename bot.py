import os
import sqlite3
import random
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

# =========================
# CONFIG
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

INSTAGRAM_URL = "https://www.instagram.com/Clip2editz/"

DB_NAME = "bot.db"
STARTING_CREDITS = 3

# =========================
# DATABASE
# =========================

def db():
    return sqlite3.connect(DB_NAME)


def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        credits INTEGER DEFAULT 3,
        referred_by INTEGER,
        referral_rewarded INTEGER DEFAULT 0,
        daily_time TEXT,
        spin_time TEXT,
        verified INTEGER DEFAULT 0
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
        PRIMARY KEY(user_id, code)
    )
    """)

    con.commit()
    con.close()


def add_user(user_id, username, referred_by=None):
    con = db()
    cur = con.cursor()

    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    exists = cur.fetchone()

    if not exists:
        cur.execute("""
        INSERT INTO users (user_id, username, credits, referred_by)
        VALUES (?, ?, ?, ?)
        """, (user_id, username or "", STARTING_CREDITS, referred_by))

    con.commit()
    con.close()


def get_credits(user_id):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    con.close()
    return row[0] if row else 0


def add_credits(user_id, amount):
    con = db()
    cur = con.cursor()
    cur.execute(
        "UPDATE users SET credits = credits + ? WHERE user_id=?",
        (amount, user_id)
    )
    con.commit()
    con.close()


def remove_credit(user_id):
    credits = get_credits(user_id)

    if credits < 1:
        return False

    add_credits(user_id, -1)
    return True


# =========================
# KEYBOARDS
# =========================

def verification_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📸 Follow Instagram",
                url=INSTAGRAM_URL
            )
        ],
        [
            InlineKeyboardButton(
                "✅ Verify & Continue",
                callback_data="verify"
            )
        ]
    ])


def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 API Check", callback_data="api_menu")
        ],
        [
            InlineKeyboardButton("💰 My Credits", callback_data="credits"),
            InlineKeyboardButton("👥 Refer & Earn", callback_data="refer")
        ],
        [
            InlineKeyboardButton("🎁 Daily Claim", callback_data="daily"),
            InlineKeyboardButton("🎰 Spin & Win", callback_data="spin")
        ],
        [
            InlineKeyboardButton("🎟 Redeem Claim", callback_data="redeem")
        ]
    ])


def api_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚗 Vehicle Search", callback_data="vehicle"),
            InlineKeyboardButton("📍 Pincode Search", callback_data="pincode")
        ],
        [
            InlineKeyboardButton("🔎 API Option 3", callback_data="api3"),
            InlineKeyboardButton("🔎 API Option 4", callback_data="api4")
        ],
        [
            InlineKeyboardButton("🔎 API Option 5", callback_data="api5")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back")
        ]
    ])


def admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Bot Stats", callback_data="stats"),
            InlineKeyboardButton("➕ Add Credits", callback_data="admin_add")
        ],
        [
            InlineKeyboardButton("🎟 Create Redeem", callback_data="admin_redeem")
        ],
        [
            InlineKeyboardButton("🏠 Main Menu", callback_data="back")
        ]
    ])


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    referred_by = None

    if context.args:
        try:
            referred_by = int(context.args[0])
            if referred_by == user.id:
                referred_by = None
        except:
            pass

    add_user(user.id, user.username, referred_by)

    await update.message.reply_text(
        "⚡ <b>WELCOME TO API BOT</b> ⚡\n\n"
        "🔐 Access lene se pehle hamara Instagram follow karein.\n\n"
        "📸 Instagram: @Clip2editz\n\n"
        "━━━━━━━━━━━━━━\n"
        "〆 <b>DEVELOPER : SOHAIL</b>",
        parse_mode="HTML",
        reply_markup=verification_keyboard()
    )


# =========================
# CALLBACKS
# =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data

    await query.answer()

    # VERIFY
    if data == "verify":
        con = db()
        cur = con.cursor()

        cur.execute(
            "UPDATE users SET verified=1 WHERE user_id=?",
            (user.id,)
        )

        # Referral reward
        cur.execute(
            "SELECT referred_by, referral_rewarded FROM users WHERE user_id=?",
            (user.id,)
        )

        row = cur.fetchone()

        if row and row[0] and row[1] == 0:
            referrer = row[0]

            if referrer != user.id:
                cur.execute(
                    "UPDATE users SET credits=credits+3 WHERE user_id=?",
                    (referrer,)
                )

                cur.execute(
                    "UPDATE users SET referral_rewarded=1 WHERE user_id=?",
                    (user.id,)
                )

        con.commit()
        con.close()

        await query.edit_message_text(
            "✅ <b>Verification Successful!</b>\n\n"
            "Welcome bhai 😎\n"
            "Ab tum bot ke saare available options use kar sakte ho.\n\n"
            "〆 <b>DEVELOPER : SOHAIL</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
        return

    # API MENU
    if data == "api_menu":
        await query.edit_message_text(
            "🔍 <b>API CHECK MENU</b>\n\n"
            "Ek option select karo.\n"
            "⚡ Har successful API search = 1 Credit\n\n"
            "〆 <b>DEVELOPER : SOHAIL</b>",
            parse_mode="HTML",
            reply_markup=api_keyboard()
        )
        return

    # BACK
    if data == "back":
        await query.edit_message_text(
            "🏠 <b>MAIN MENU</b>\n\n"
            f"💰 Available Credits: <b>{get_credits(user.id)}</b>\n\n"
            "Option select karo 👇\n\n"
            "〆 <b>DEVELOPER : SOHAIL</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
        return

    # CREDITS
    if data == "credits":
        await query.answer(
            f"💰 Tumhare paas {get_credits(user.id)} Credits hain!",
            show_alert=True
        )
        return

    # REFER
    if data == "refer":
        bot_username = (await context.bot.get_me()).username
        link = f"https://t.me/{bot_username}?start={user.id}"

        await query.edit_message_text(
            "👥 <b>REFER & EARN</b>\n\n"
            "Apna referral link share karo.\n"
            "Har successful referral par tumhe <b>+3 Credits</b> milenge! 🎉\n\n"
            f"🔗 <code>{link}</code>\n\n"
            "〆 <b>DEVELOPER : SOHAIL</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )
        return

    # DAILY
    if data == "daily":
        await daily_claim(query, user.id)
        return

    # SPIN
    if data == "spin":
        await spin(query, user.id)
        return

    # REDEEM
    if data == "redeem":
        context.user_data["waiting"] = "redeem"

        await query.edit_message_text(
            "🎟 <b>REDEEM CLAIM</b>\n\n"
            "Apna redeem code bhejo 👇\n\n"
            "Example: <code>WELCOME10</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Cancel", callback_data="back")]
            ])
        )
        return

    # VEHICLE
    if data == "vehicle":
        context.user_data["waiting"] = "vehicle"

        await query.edit_message_text(
            "🚗 <b>VEHICLE SEARCH</b>\n\n"
            "Vehicle number bhejo.\n\n"
            "Example: <code>RJ14CV0002</code>\n\n"
            "💳 Cost: 1 Credit",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="api_menu")]
            ])
        )
        return

    # PINCODE
    if data == "pincode":
        context.user_data["waiting"] = "pincode"

        await query.edit_message_text(
            "📍 <b>PINCODE SEARCH</b>\n\n"
            "Pincode bhejo.\n\n"
            "Example: <code>411001</code>\n\n"
            "💳 Cost: 1 Credit",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="api_menu")]
            ])
        )
        return

    # PLACEHOLDERS
    if data in ["api3", "api4", "api5"]:
        await query.answer(
            "⚠️ Ye API option abhi configure nahi hua.",
            show_alert=True
        )
        return

    # ADMIN
    if data == "admin":
        if user.id != ADMIN_ID:
            return

        await query.edit_message_text(
            "👑 <b>ADMIN PANEL</b>\n\n"
            "Developer Control Panel",
            parse_mode="HTML",
            reply_markup=admin_keyboard()
        )
        return

    if data == "stats":
        if user.id != ADMIN_ID:
            return

        con = db()
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        total = cur.fetchone()[0]
        con.close()

        await query.answer(
            f"📊 Total Users: {total}",
            show_alert=True
        )
        return

    if data == "admin_add":
        if user.id != ADMIN_ID:
            return

        context.user_data["waiting"] = "admin_add"

        await query.edit_message_text(
            "➕ <b>ADD CREDITS</b>\n\n"
            "Format bhejo:\n"
            "<code>USER_ID AMOUNT</code>\n\n"
            "Example:\n"
            "<code>123456789 10</code>",
            parse_mode="HTML"
        )
        return

    if data == "admin_redeem":
        if user.id != ADMIN_ID:
            return

        context.user_data["waiting"] = "admin_redeem"

        await query.edit_message_text(
            "🎟 <b>CREATE REDEEM CODE</b>\n\n"
            "Format:\n"
            "<code>CODE CREDITS MAX_USES</code>\n\n"
            "Example:\n"
            "<code>WELCOME10 10 100</code>",
            parse_mode="HTML"
        )
        return


# =========================
# DAILY CLAIM
# =========================

async def daily_claim(query, user_id):
    con = db()
    cur = con.cursor()

    cur.execute(
        "SELECT daily_time FROM users WHERE user_id=?",
        (user_id,)
    )

    row = cur.fetchone()
    now = datetime.now(timezone.utc)

    if row and row[0]:
        last = datetime.fromisoformat(row[0])

        if now - last < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)

            con.close()

            await query.answer(
                f"⏳ Daily already claimed!\nWait {hours}h {minutes}m",
                show_alert=True
            )
            return

    reward = 1

    cur.execute(
        "UPDATE users SET credits=credits+?, daily_time=? WHERE user_id=?",
        (reward, now.isoformat(), user_id)
    )

    con.commit()
    con.close()

    await query.answer(
        f"🎉 Daily Claim Successful!\n+{reward} Credit",
        show_alert=True
    )


# =========================
# SPIN
# =========================

async def spin(query, user_id):
    con = db()
    cur = con.cursor()

    cur.execute(
        "SELECT spin_time FROM users WHERE user_id=?",
        (user_id,)
    )

    row = cur.fetchone()
    now = datetime.now(timezone.utc)

    if row and row[0]:
        last = datetime.fromisoformat(row[0])

        if now - last < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)

            con.close()

            await query.answer(
                f"⏳ Spin already used!\nWait {hours}h {minutes}m",
                show_alert=True
            )
            return

    reward = random.randint(1, 5)

    cur.execute(
        "UPDATE users SET credits=credits+?, spin_time=? WHERE user_id=?",
        (reward, now.isoformat(), user_id)
    )

    con.commit()
    con.close()

    await query.answer(
        f"🎰 SPIN RESULT!\n\n🎉 You won +{reward} Credits!",
        show_alert=True
    )


# =========================
# TEXT HANDLER
# =========================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    waiting = context.user_data.get("waiting")

    if not waiting:
        return

    # VEHICLE
    if waiting == "vehicle":
        context.user_data.pop("waiting", None)

        if get_credits(user.id) < 1:
            await update.message.reply_text(
                "❌ Tumhare paas enough credits nahi hain."
            )
            return

        try:
            url = (
                "https://nitin-api-free-user-1k-spacial.vercel.app/api"
                f"?type=vehicle&search={text}"
            )

            r = requests.get(url, timeout=15)

            if r.status_code != 200:
                await update.message.reply_text("❌ API Error.")
                return

            data = r.json()

            if not remove_credit(user.id):
                await update.message.reply_text("❌ Credit error.")
                return

            await update.message.reply_text(
                f"🚗 <b>VEHICLE RESULT</b>\n\n"
                f"<pre>{data}</pre>\n\n"
                f"💰 Remaining Credits: {get_credits(user.id)}\n"
                f"〆 <b>DEVELOPER : SOHAIL</b>",
                parse_mode="HTML"
            )

        except Exception as e:
            await update.message.reply_text(
                f"❌ Error: {str(e)}"
            )

        return

    # PINCODE
    if waiting == "pincode":
        context.user_data.pop("waiting", None)

        if get_credits(user.id) < 1:
            await update.message.reply_text(
                "❌ Tumhare paas enough credits nahi hain."
            )
            return

        try:
            url = (
                "https://nitin-api-free-user-1k-spacial.vercel.app/api"
                f"?type=pincode&search={text}"
            )

            r = requests.get(url, timeout=15)

            if r.status_code != 200:
                await update.message.reply_text("❌ API Error.")
                return

            data = r.json()

            if not remove_credit(user.id):
                await update.message.reply_text("❌ Credit error.")
                return

            await update.message.reply_text(
                f"📍 <b>PINCODE RESULT</b>\n\n"
                f"<pre>{data}</pre>\n\n"
                f"💰 Remaining Credits: {get_credits(user.id)}\n"
                f"〆 <b>DEVELOPER : SOHAIL</b>",
                parse_mode="HTML"
            )

        except Exception as e:
            await update.message.reply_text(
                f"❌ Error: {str(e)}"
            )

        return

    # REDEEM
    if waiting == "redeem":
        context.user_data.pop("waiting", None)

        code = text.upper()

        con = db()
        cur = con.cursor()

        cur.execute("""
        SELECT credits, max_uses, uses, active
        FROM redeem_codes
        WHERE code=?
        """, (code,))

        row = cur.fetchone()

        if not row:
            con.close()
            await update.message.reply_text("❌ Invalid Redeem Code.")
            return

        credits, max_uses, uses, active = row

        cur.execute("""
        SELECT 1 FROM redeemed
        WHERE user_id=? AND code=?
        """, (user.id, code))

        already = cur.fetchone()

        if not active or uses >= max_uses or already:
            con.close()
            await update.message.reply_text(
                "❌ Code expired, already used, or unavailable."
            )
            return

        cur.execute(
            "UPDATE users SET credits=credits+? WHERE user_id=?",
            (credits, user.id)
        )

        cur.execute(
            "UPDATE redeem_codes SET uses=uses+1 WHERE code=?",
            (code,)
        )

        cur.execute(
            "INSERT INTO redeemed (user_id, code) VALUES (?, ?)",
            (user.id, code)
        )

        con.commit()
        con.close()

        await update.message.reply_text(
            f"🎉 Redeem Successful!\n\n"
            f"➕ {credits} Credits added!\n"
            f"💰 Total: {get_credits(user.id)}"
        )

        return

    # ADMIN ADD CREDIT
    if waiting == "admin_add":
        if user.id != ADMIN_ID:
            return

        context.user_data.pop("waiting", None)

        try:
            uid, amount = map(int, text.split())
            add_credits(uid, amount)

            await update.message.reply_text(
                f"✅ {amount} credits added to {uid}"
            )

        except:
            await update.message.reply_text(
                "❌ Wrong format."
            )

        return

    # ADMIN CREATE REDEEM
    if waiting == "admin_redeem":
        if user.id != ADMIN_ID:
            return

        context.user_data.pop("waiting", None)

        try:
            code, credits, max_uses = text.split()

            con = db()
            cur = con.cursor()

            cur.execute("""
            INSERT OR REPLACE INTO redeem_codes
            (code, credits, max_uses, uses, active)
            VALUES (?, ?, ?, 0, 1)
            """, (
                code.upper(),
                int(credits),
                int(max_uses)
            ))

            con.commit()
            con.close()

            await update.message.reply_text(
                f"✅ Redeem Created!\n\n"
                f"🎟 Code: {code.upper()}\n"
                f"💰 Credits: {credits}\n"
                f"👥 Max Uses: {max_uses}"
            )

        except:
            await update.message.reply_text(
                "❌ Wrong format."
            )


# =========================
# ADMIN COMMAND
# =========================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "👑 <b>ADMIN PANEL</b>\n\n"
        "Developer Sohail Control Panel",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )


# =========================
# RUN
# =========================

def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN environment variable missing!")
        return

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)
    )

    print("Bot Started...")
    app.run_polling()


if __name__ == "__main__":
    main(import os
import sqlite3
import random
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

# =========================
# CONFIG
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

INSTAGRAM_URL = "https://www.instagram.com/Clip2editz/"

DB_NAME = "bot.db"
STARTING_CREDITS = 3

# =========================
# DATABASE
# =========================

def db():
    return sqlite3.connect(DB_NAME)


def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        credits INTEGER DEFAULT 3,
        referred_by INTEGER,
        referral_rewarded INTEGER DEFAULT 0,
        daily_time TEXT,
        spin_time TEXT,
        verified INTEGER DEFAULT 0
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
        PRIMARY KEY(user_id, code)
    )
    """)

    con.commit()
    con.close()


def add_user(user_id, username, referred_by=None):
    con = db()
    cur = con.cursor()

    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    exists = cur.fetchone()

    if not exists:
        cur.execute("""
        INSERT INTO users (user_id, username, credits, referred_by)
        VALUES (?, ?, ?, ?)
        """, (user_id, username or "", STARTING_CREDITS, referred_by))

    con.commit()
    con.close()


def get_credits(user_id):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    con.close()
    return row[0] if row else 0


def add_credits(user_id, amount):
    con = db()
    cur = con.cursor()
    cur.execute(
        "UPDATE users SET credits = credits + ? WHERE user_id=?",
        (amount, user_id)
    )
    con.commit()
    con.close()


def remove_credit(user_id):
    credits = get_credits(user_id)

    if credits < 1:
        return False

    add_credits(user_id, -1)
    return True


# =========================
# KEYBOARDS
# =========================

def verification_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📸 Follow Instagram",
                url=INSTAGRAM_URL
            )
        ],
        [
            InlineKeyboardButton(
                "✅ Verify & Continue",
                callback_data="verify"
            )
        ]
    ])


def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 API Check", callback_data="api_menu")
        ],
        [
            InlineKeyboardButton("💰 My Credits", callback_data="credits"),
            InlineKeyboardButton("👥 Refer & Earn", callback_data="refer")
        ],
        [
            InlineKeyboardButton("🎁 Daily Claim", callback_data="daily"),
            InlineKeyboardButton("🎰 Spin & Win", callback_data="spin")
        ],
        [
            InlineKeyboardButton("🎟 Redeem Claim", callback_data="redeem")
        ]
    ])


def api_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚗 Vehicle Search", callback_data="vehicle"),
            InlineKeyboardButton("📍 Pincode Search", callback_data="pincode")
        ],
        [
            InlineKeyboardButton("🔎 API Option 3", callback_data="api3"),
            InlineKeyboardButton("🔎 API Option 4", callback_data="api4")
        ],
        [
            InlineKeyboardButton("🔎 API Option 5", callback_data="api5")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back")
        ]
    ])


def admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Bot Stats", callback_data="stats"),
            InlineKeyboardButton("➕ Add Credits", callback_data="admin_add")
        ],
        [
            InlineKeyboardButton("🎟 Create Redeem", callback_data="admin_redeem")
        ],
        [
            InlineKeyboardButton("🏠 Main Menu", callback_data="back")
        ]
    ])


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    referred_by = None

    if context.args:
        try:
            referred_by = int(context.args[0])
            if referred_by == user.id:
                referred_by = None
        except:
            pass

    add_user(user.id, user.username, referred_by)

    await update.message.reply_text(
        "⚡ <b>WELCOME TO API BOT</b> ⚡\n\n"
        "🔐 Access lene se pehle hamara Instagram follow karein.\n\n"
        "📸 Instagram: @Clip2editz\n\n"
        "━━━━━━━━━━━━━━\n"
        "〆 <b>DEVELOPER : SOHAIL</b>",
        parse_mode="HTML",
        reply_markup=verification_keyboard()
    )


# =========================
# CALLBACKS
# =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data

    await query.answer()

    # VERIFY
    if data == "verify":
        con = db()
        cur = con.cursor()

        cur.execute(
            "UPDATE users SET verified=1 WHERE user_id=?",
            (user.id,)
        )

        # Referral reward
        cur.execute(
            "SELECT referred_by, referral_rewarded FROM users WHERE user_id=?",
            (user.id,)
        )

        row = cur.fetchone()

        if row and row[0] and row[1] == 0:
            referrer = row[0]

            if referrer != user.id:
                cur.execute(
                    "UPDATE users SET credits=credits+3 WHERE user_id=?",
                    (referrer,)
                )

                cur.execute(
                    "UPDATE users SET referral_rewarded=1 WHERE user_id=?",
                    (user.id,)
                )

        con.commit()
        con.close()

        await query.edit_message_text(
            "✅ <b>Verification Successful!</b>\n\n"
            "Welcome bhai 😎\n"
            "Ab tum bot ke saare available options use kar sakte ho.\n\n"
            "〆 <b>DEVELOPER : SOHAIL</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
        return

    # API MENU
    if data == "api_menu":
        await query.edit_message_text(
            "🔍 <b>API CHECK MENU</b>\n\n"
            "Ek option select karo.\n"
            "⚡ Har successful API search = 1 Credit\n\n"
            "〆 <b>DEVELOPER : SOHAIL</b>",
            parse_mode="HTML",
            reply_markup=api_keyboard()
        )
        return

    # BACK
    if data == "back":
        await query.edit_message_text(
            "🏠 <b>MAIN MENU</b>\n\n"
            f"💰 Available Credits: <b>{get_credits(user.id)}</b>\n\n"
            "Option select karo 👇\n\n"
            "〆 <b>DEVELOPER : SOHAIL</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
        return

    # CREDITS
    if data == "credits":
        await query.answer(
            f"💰 Tumhare paas {get_credits(user.id)} Credits hain!",
            show_alert=True
        )
        return

    # REFER
    if data == "refer":
        bot_username = (await context.bot.get_me()).username
        link = f"https://t.me/{bot_username}?start={user.id}"

        await query.edit_message_text(
            "👥 <b>REFER & EARN</b>\n\n"
            "Apna referral link share karo.\n"
            "Har successful referral par tumhe <b>+3 Credits</b> milenge! 🎉\n\n"
            f"🔗 <code>{link}</code>\n\n"
            "〆 <b>DEVELOPER : SOHAIL</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )
        return

    # DAILY
    if data == "daily":
        await daily_claim(query, user.id)
        return

    # SPIN
    if data == "spin":
        await spin(query, user.id)
        return

    # REDEEM
    if data == "redeem":
        context.user_data["waiting"] = "redeem"

        await query.edit_message_text(
            "🎟 <b>REDEEM CLAIM</b>\n\n"
            "Apna redeem code bhejo 👇\n\n"
            "Example: <code>WELCOME10</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Cancel", callback_data="back")]
            ])
        )
        return

    # VEHICLE
    if data == "vehicle":
        context.user_data["waiting"] = "vehicle"

        await query.edit_message_text(
            "🚗 <b>VEHICLE SEARCH</b>\n\n"
            "Vehicle number bhejo.\n\n"
            "Example: <code>RJ14CV0002</code>\n\n"
            "💳 Cost: 1 Credit",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="api_menu")]
            ])
        )
        return

    # PINCODE
    if data == "pincode":
        context.user_data["waiting"] = "pincode"

        await query.edit_message_text(
            "📍 <b>PINCODE SEARCH</b>\n\n"
            "Pincode bhejo.\n\n"
            "Example: <code>411001</code>\n\n"
            "💳 Cost: 1 Credit",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="api_menu")]
            ])
        )
        return

    # PLACEHOLDERS
    if data in ["api3", "api4", "api5"]:
        await query.answer(
            "⚠️ Ye API option abhi configure nahi hua.",
            show_alert=True
        )
        return

    # ADMIN
    if data == "admin":
        if user.id != ADMIN_ID:
            return

        await query.edit_message_text(
            "👑 <b>ADMIN PANEL</b>\n\n"
            "Developer Control Panel",
            parse_mode="HTML",
            reply_markup=admin_keyboard()
        )
        return

    if data == "stats":
        if user.id != ADMIN_ID:
            return

        con = db()
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        total = cur.fetchone()[0]
        con.close()

        await query.answer(
            f"📊 Total Users: {total}",
            show_alert=True
        )
        return

    if data == "admin_add":
        if user.id != ADMIN_ID:
            return

        context.user_data["waiting"] = "admin_add"

        await query.edit_message_text(
            "➕ <b>ADD CREDITS</b>\n\n"
            "Format bhejo:\n"
            "<code>USER_ID AMOUNT</code>\n\n"
            "Example:\n"
            "<code>123456789 10</code>",
            parse_mode="HTML"
        )
        return

    if data == "admin_redeem":
        if user.id != ADMIN_ID:
            return

        context.user_data["waiting"] = "admin_redeem"

        await query.edit_message_text(
            "🎟 <b>CREATE REDEEM CODE</b>\n\n"
            "Format:\n"
            "<code>CODE CREDITS MAX_USES</code>\n\n"
            "Example:\n"
            "<code>WELCOME10 10 100</code>",
            parse_mode="HTML"
        )
        return


# =========================
# DAILY CLAIM
# =========================

async def daily_claim(query, user_id):
    con = db()
    cur = con.cursor()

    cur.execute(
        "SELECT daily_time FROM users WHERE user_id=?",
        (user_id,)
    )

    row = cur.fetchone()
    now = datetime.now(timezone.utc)

    if row and row[0]:
        last = datetime.fromisoformat(row[0])

        if now - last < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)

            con.close()

            await query.answer(
                f"⏳ Daily already claimed!\nWait {hours}h {minutes}m",
                show_alert=True
            )
            return

    reward = 1

    cur.execute(
        "UPDATE users SET credits=credits+?, daily_time=? WHERE user_id=?",
        (reward, now.isoformat(), user_id)
    )

    con.commit()
    con.close()

    await query.answer(
        f"🎉 Daily Claim Successful!\n+{reward} Credit",
        show_alert=True
    )


# =========================
# SPIN
# =========================

async def spin(query, user_id):
    con = db()
    cur = con.cursor()

    cur.execute(
        "SELECT spin_time FROM users WHERE user_id=?",
        (user_id,)
    )

    row = cur.fetchone()
    now = datetime.now(timezone.utc)

    if row and row[0]:
        last = datetime.fromisoformat(row[0])

        if now - last < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)

            con.close()

            await query.answer(
                f"⏳ Spin already used!\nWait {hours}h {minutes}m",
                show_alert=True
            )
            return

    reward = random.randint(1, 5)

    cur.execute(
        "UPDATE users SET credits=credits+?, spin_time=? WHERE user_id=?",
        (reward, now.isoformat(), user_id)
    )

    con.commit()
    con.close()

    await query.answer(
        f"🎰 SPIN RESULT!\n\n🎉 You won +{reward} Credits!",
        show_alert=True
    )


# =========================
# TEXT HANDLER
# =========================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    waiting = context.user_data.get("waiting")

    if not waiting:
        return

    # VEHICLE
    if waiting == "vehicle":
        context.user_data.pop("waiting", None)

        if get_credits(user.id) < 1:
            await update.message.reply_text(
                "❌ Tumhare paas enough credits nahi hain."
            )
            return

        try:
            url = (
                "https://nitin-api-free-user-1k-spacial.vercel.app/api"
                f"?type=vehicle&search={text}"
            )

            r = requests.get(url, timeout=15)

            if r.status_code != 200:
                await update.message.reply_text("❌ API Error.")
                return

            data = r.json()

            if not remove_credit(user.id):
                await update.message.reply_text("❌ Credit error.")
                return

            await update.message.reply_text(
                f"🚗 <b>VEHICLE RESULT</b>\n\n"
                f"<pre>{data}</pre>\n\n"
                f"💰 Remaining Credits: {get_credits(user.id)}\n"
                f"〆 <b>DEVELOPER : SOHAIL</b>",
                parse_mode="HTML"
            )

        except Exception as e:
            await update.message.reply_text(
                f"❌ Error: {str(e)}"
            )

        return

    # PINCODE
    if waiting == "pincode":
        context.user_data.pop("waiting", None)

        if get_credits(user.id) < 1:
            await update.message.reply_text(
                "❌ Tumhare paas enough credits nahi hain."
            )
            return

        try:
            url = (
                "https://nitin-api-free-user-1k-spacial.vercel.app/api"
                f"?type=pincode&search={text}"
            )

            r = requests.get(url, timeout=15)

            if r.status_code != 200:
                await update.message.reply_text("❌ API Error.")
                return

            data = r.json()

            if not remove_credit(user.id):
                await update.message.reply_text("❌ Credit error.")
                return

            await update.message.reply_text(
                f"📍 <b>PINCODE RESULT</b>\n\n"
                f"<pre>{data}</pre>\n\n"
                f"💰 Remaining Credits: {get_credits(user.id)}\n"
                f"〆 <b>DEVELOPER : SOHAIL</b>",
                parse_mode="HTML"
            )

        except Exception as e:
            await update.message.reply_text(
                f"❌ Error: {str(e)}"
            )

        return

    # REDEEM
    if waiting == "redeem":
        context.user_data.pop("waiting", None)

        code = text.upper()

        con = db()
        cur = con.cursor()

        cur.execute("""
        SELECT credits, max_uses, uses, active
        FROM redeem_codes
        WHERE code=?
        """, (code,))

        row = cur.fetchone()

        if not row:
            con.close()
            await update.message.reply_text("❌ Invalid Redeem Code.")
            return

        credits, max_uses, uses, active = row

        cur.execute("""
        SELECT 1 FROM redeemed
        WHERE user_id=? AND code=?
        """, (user.id, code))

        already = cur.fetchone()

        if not active or uses >= max_uses or already:
            con.close()
            await update.message.reply_text(
                "❌ Code expired, already used, or unavailable."
            )
            return

        cur.execute(
            "UPDATE users SET credits=credits+? WHERE user_id=?",
            (credits, user.id)
        )

        cur.execute(
            "UPDATE redeem_codes SET uses=uses+1 WHERE code=?",
            (code,)
        )

        cur.execute(
            "INSERT INTO redeemed (user_id, code) VALUES (?, ?)",
            (user.id, code)
        )

        con.commit()
        con.close()

        await update.message.reply_text(
            f"🎉 Redeem Successful!\n\n"
            f"➕ {credits} Credits added!\n"
            f"💰 Total: {get_credits(user.id)}"
        )

        return

    # ADMIN ADD CREDIT
    if waiting == "admin_add":
        if user.id != ADMIN_ID:
            return

        context.user_data.pop("waiting", None)

        try:
            uid, amount = map(int, text.split())
            add_credits(uid, amount)

            await update.message.reply_text(
                f"✅ {amount} credits added to {uid}"
            )

        except:
            await update.message.reply_text(
                "❌ Wrong format."
            )

        return

    # ADMIN CREATE REDEEM
    if waiting == "admin_redeem":
        if user.id != ADMIN_ID:
            return

        context.user_data.pop("waiting", None)

        try:
            code, credits, max_uses = text.split()

            con = db()
            cur = con.cursor()

            cur.execute("""
            INSERT OR REPLACE INTO redeem_codes
            (code, credits, max_uses, uses, active)
            VALUES (?, ?, ?, 0, 1)
            """, (
                code.upper(),
                int(credits),
                int(max_uses)
            ))

            con.commit()
            con.close()

            await update.message.reply_text(
                f"✅ Redeem Created!\n\n"
                f"🎟 Code: {code.upper()}\n"
                f"💰 Credits: {credits}\n"
                f"👥 Max Uses: {max_uses}"
            )

        except:
            await update.message.reply_text(
                "❌ Wrong format."
            )


# =========================
# ADMIN COMMAND
# =========================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "👑 <b>ADMIN PANEL</b>\n\n"
        "Developer Sohail Control Panel",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )


# =========================
# RUN
# =========================

def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN environment variable missing!")
        return

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)
    )

    print("Bot Started...")
    app.run_polling()


if __name__ == "__main__":
    main()
