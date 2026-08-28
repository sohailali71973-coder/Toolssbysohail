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

    cur.execute(
        "SELECT user_id FROM users WHERE user_id = ?",
        (user_id,)
    )

    existing = cur.fetchone()

    if not existing:
        cur.execute("""
            INSERT INTO users
            (user_id, username, credits, referred_by)
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            username or "",
            STARTING_CREDITS,
            referred_by
        ))

    conn.commit()
    conn.close()


def get_credits(user_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT credits FROM users WHERE user_id = ?",
        (user_id,)
    )

    row = cur.fetchone()
    conn.close()

    if row:
        return row[0]

    return 0


def add_credits(user_id, amount):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET credits = credits + ?
        WHERE user_id = ?
    """, (amount, user_id))

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


def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔍 API Check",
                callback_data="api_menu"
            )
        ],
        [
            InlineKeyboardButton(
                "💰 My Credits",
                callback_data="credits"
            ),
            InlineKeyboardButton(
                "👥 Refer & Earn",
                callback_data="refer"
            )
        ],
        [
            InlineKeyboardButton(
                "🎁 Daily Claim",
                callback_data="daily"
            ),
            InlineKeyboardButton(
                "🎰 Spin & Win",
                callback_data="spin"
            )
        ],
        [
            InlineKeyboardButton(
                "🎟 Redeem Claim",
                callback_data="redeem"
            )
        ]
    ])


def api_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🚗 Vehicle Search",
                callback_data="vehicle"
            )
        ],
        [
            InlineKeyboardButton(
                "📍 Pincode Search",
                callback_data="pincode"
            )
        ],
        [
            InlineKeyboardButton(
                "🔎 API Option 3",
                callback_data="api3"
            ),
            InlineKeyboardButton(
                "🔎 API Option 4",
                callback_data="api4"
            )
        ],
        [
            InlineKeyboardButton(
                "🔎 API Option 5",
                callback_data="api5"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back"
            )
        ]
    ])


def admin_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📊 Bot Stats",
                callback_data="stats"
            )
        ],
        [
            InlineKeyboardButton(
                "➕ Add Credits",
                callback_data="admin_add"
            )
        ],
        [
            InlineKeyboardButton(
                "🎟 Create Redeem",
                callback_data="admin_redeem"
            )
        ],
        [
            InlineKeyboardButton(
                "🏠 Main Menu",
                callback_data="back"
            )
        ]
    ])


def back_button():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back"
            )
        ]
    ])


def api_back_button():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="api_menu"
            )
        ]
    ])


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

    create_user(
        user.id,
        user.username,
        referred_by
    )

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

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    user = query.from_user
    data = query.data

    await query.answer()

    # ----------------------------------------------
    # VERIFY
    # ----------------------------------------------

    if data == "verify":

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            UPDATE users
            SET verified = 1
            WHERE user_id = ?
        """, (user.id,))

        cur.execute("""
            SELECT referred_by, referral_rewarded
            FROM users
            WHERE user_id = ?
        """, (user.id,))

        row = cur.fetchone()

        if row:
            referred_by = row[0]
            rewarded = row[1]

            if (
                referred_by
                and rewarded == 0
                and referred_by != user.id
            ):
                cur.execute("""
                    UPDATE users
                    SET credits = credits + ?
                    WHERE user_id = ?
                """, (
                    REFERRAL_REWARD,
                    referred_by
                ))

                cur.execute("""
                    UPDATE users
                    SET referral_rewarded = 1
                    WHERE user_id = ?
                """, (user.id,))

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

    # ----------------------------------------------
    # MAIN MENU
    # ----------------------------------------------

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

    # ----------------------------------------------
    # API MENU
    # ----------------------------------------------

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

    # ----------------------------------------------
    # CREDITS
    # ----------------------------------------------

    if data == "credits":

        credits = get_credits(user.id)

        await query.answer(
            f"💰 Tumhare paas {credits} Credits hain!",
            show_alert=True
        )

        return

    # ----------------------------------------------
    # REFER
    # ----------------------------------------------

    if data == "refer":

        bot_info = await context.bot.get_me()
        bot_username = bot_info.username

        referral_link = (
            f"https://t.me/{bot_username}"
            f"?start={user.id}"
        )

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

    # ----------------------------------------------
    # DAILY
    # ----------------------------------------------

    if data == "daily":

        await handle_daily(query, user.id)
        return

    # ----------------------------------------------
    # SPIN
    # ----------------------------------------------

    if data == "spin":

        await handle_spin(query, user.id)
        return

    # ----------------------------------------------
    # REDEEM
    # ----------------------------------------------

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

    # ----------------------------------------------
    # VEHICLE
    # ----------------------------------------------

    if data == "vehicle":

        context.user_data["waiting_for"] = "vehicle"

        await query.edit_message_text(
            "🚗 <b>VEHICLE SEARCH</b>\n\n"
            "Vehicle number bhejo.\n\n"
            "Example:\n"
            "<code>RJ14CV0002</code>\n\n"
            "💳 Cost: <b>1 Credit</b>",
            parse_mode="HTML",
            reply_markup=api_back_button()
        )

        return

    # ----------------------------------------------
    # PINCODE
    # ----------------------------------------------

    if data == "pincode":

        context.user_data["waiting_for"] = "pincode"

        await query.edit_message_text(
            "📍 <b>PINCODE SEARCH</b>\n\n"
            "Pincode bhejo.\n\n"
            "Example:\n"
            "<code>411001</code>\n\n"
            "💳 Cost: <b>1 Credit</b>",
            parse_mode="HTML",
            reply_markup=api_back_button()
        )

        return

    # ----------------------------------------------
    # PLACEHOLDER OPTIONS
    # ----------------------------------------------

    if data in ["api3", "api4", "api5"]:

        await query.answer(
            "⚠️ Ye option abhi configured nahi hai.",
            show_alert=True
        )

        return

    # ----------------------------------------------
    # ADMIN PANEL
    # ----------------------------------------------

    if data == "admin":

        if user.id != ADMIN_ID:
            return

        await query.edit_message_text(
            "👑 <b>ADMIN PANEL</b>\n\n"
            "Developer Sohail Control Panel",
            parse_mode="HTML",
            reply_markup=admin_menu()
        )

        return

    # ----------------------------------------------
    # STATS
    # ----------------------------------------------

    if data == "stats":

        if user.id != ADMIN_ID:
            return

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT COUNT(*) FROM users"
        )

        total_users = cur.fetchone()[0]

        conn.close()

        await query.answer(
            f"📊 Total Users: {total_users}",
            show_alert=True
        )

        return

    # ----------------------------------------------
    # ADMIN ADD CREDITS
    # ----------------------------------------------

    if data == "admin_add":

        if user.id != ADMIN_ID:
            return

        context.user_data["waiting_for"] = "admin_add"

        await query.edit_message_text(
            "➕ <b>ADD CREDITS</b>\n\n"
            "Is format mein bhejo:\n\n"
            "<code>USER_ID AMOUNT</code>\n\n"
            "Example:\n"
            "<code>123456789 10</code>",
            parse_mode="HTML"
        )

        return

    # ----------------------------------------------
    # ADMIN CREATE REDEEM
    # ----------------------------------------------

    if data == "admin_redeem":

        if user.id != ADMIN_ID:
            return

        context.user_data["waiting_for"] = "admin_redeem"

        await query.edit_message_text(
            "🎟 <b>CREATE REDEEM CODE</b>\n\n"
            "Format:\n\n"
            "<code>CODE CREDITS MAX_USES</code>\n\n"
            "Example:\n"
            "<code>WELCOME10 10 100</code>",
            parse_mode="HTML"
        )

        return


# ==================================================
# DAILY CLAIM
# ==================================================

async def handle_daily(query, user_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT daily_time
        FROM users
        WHERE user_id = ?
    """, (user_id,))

    row = cur.fetchone()

    now = datetime.now(timezone.utc)

    if row and row[0]:

        last_time = datetime.fromisoformat(row[0])

        if now - last_time < timedelta(hours=24):

            remaining = (
                timedelta(hours=24)
                - (now - last_time)
            )

            hours = int(
                remaining.total_seconds() // 3600
            )

            minutes = int(
                (remaining.total_seconds() % 3600) // 60
            )

            conn.close()

            await query.answer(
                f"⏳ Already claimed!\n"
                f"Wait {hours}h {minutes}m",
                show_alert=True
            )

            return

    cur.execute("""
        UPDATE users
        SET credits = credits + ?,
            daily_time = ?
        WHERE user_id = ?
    """, (
        DAILY_REWARD,
        now.isoformat(),
        user_id
    ))

    conn.commit()
    conn.close()

    await query.answer(
        f"🎉 Daily Claim Successful!\n"
        f"+{DAILY_REWARD} Credit",
        show_alert=True
    )


# ==================================================
# SPIN
# ==================================================

async def handle_spin(query, user_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT spin_time
        FROM users
        WHERE user_id = ?
    """, (user_id,))

    row = cur.fetchone()

    now = datetime.now(timezone.utc)

    if row and row[0]:

        last_time = datetime.fromisoformat(row[0])

        if now - last_time < timedelta(hours=24):

            remaining = (
                timedelta(hours=24)
                - (now - last_time)
            )

            hours = int(
                remaining.total_seconds() // 3600
            )

            minutes = int(
                (remaining.total_seconds() % 3600) // 60
            )

            conn.close()

            await query.answer(
                f"⏳ Spin already used!\n"
                f"Wait {hours}h {minutes}m",
                show_alert=True
            )

            return

    reward = random.randint(1, 5)

    cur.execute("""
        UPDATE users
        SET credits = credits + ?,
            spin_time = ?
        WHERE user_id = ?
    """, (
        reward,
        now.isoformat(),
        user_id
    ))

    conn.commit()
    conn.close()

    await query.answer(
        f"🎰 SPIN RESULT!\n\n"
        f"🎉 You won +{reward} Credits!",
        show_alert=True
    )


# ==================================================
# TEXT HANDLER
# ==================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user
    text = update.message.text.strip()

    waiting_for = context.user_data.get(
        "waiting_for"
    )

    if not waiting_for:
        return

    # ----------------------------------------------
    # VEHICLE SEARCH
    # ----------------------------------------------

    if waiting_for == "vehicle":

        context.user_data.pop(
            "waiting_for",
            None
        )

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

            response = requests.get(
                url,
                timeout=20
            )

            response.raise_for_status()

            result = response.json()

            if not remove_one_credit(user.id):

                await update.message.reply_text(
                    "❌ Credit error."
                )

                return

            safe_result = html.escape(
                str(result)
            )

            await update.message.reply_text(
                "🚗 <b>VEHICLE RESULT</b>\n\n"
                f"<pre>{safe_result}</pre>\n\n"
                f"💰 Remaining Credits: "
                f"<b>{get_credits(user.id)}</b>\n\n"
                "〆 <b>DEVELOPER : SOHAIL</b>",
                parse_mode="HTML"
            )

        except Exception:

            await update.message.reply_text(
                "❌ API request failed. "
                "Please try again later."
            )

        return

    # ----------------------------------------------
    # PINCODE SEARCH
    # ----------------------------------------------

    if waiting_for == "pincode":

        context.user_data.pop(
            "waiting_for",
            None
        )

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

            response = requests.get(
                url,
                timeout=20
            )

            response.raise_for_status()

            result = response.json()

            if not remove_one_credit(user.id):

                await update.message.reply_text(
                    "❌ Credit error."
                )

                return

            safe_result = html.escape(
                str(result)
            )

            await update.message.reply_text(
                "📍 <b>PINCODE RESULT</b>\n\n"
                f"<pre>{safe_result}</pre>\n\n"
                f"💰 Remaining Credits: "
                f"<b>{get_credits(user.id)}</b>\n\n"
                "〆 <b>DEVELOPER : SOHAIL</b>",
                parse_mode="HTML"
            )

        except Exception:

            await update.message.reply_text(
                "❌ API request failed. "
                "Please try again later."
            )

        return

    # ----------------------------------------------
    # REDEEM
    # ----------------------------------------------

    if waiting_for == "redeem":

        context.user_data.pop(
            "waiting_for",
            None
        )

        code = text.upper()

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT credits, max_uses, uses, active
            FROM redeem_codes
            WHERE code = ?
        """, (code,))

        row = cur.fetchone()

        if not row:

            conn.close()

            await update.message.reply_text(
                "❌ Invalid Redeem Code."
            )

            return

        credits, max_uses, uses, active = row

        cur.execute("""
            SELECT 1
            FROM redeemed
            WHERE user_id = ?
            AND code = ?
        """, (
            user.id,
            code
        ))

        already_used = cur.fetchone()

        if (
            active == 0
            or uses >= max_uses
            or already_used
        ):

            conn.close()

            await update.message.reply_text(
                "❌ Code expired, unavailable "
                "or already used."
            )

            return

        cur.execute("""
            UPDATE users
            SET credits = credits + ?
            WHERE user_id = ?
        """, (
            credits,
            user.id
        ))

        cur.execute("""
            UPDATE redeem_codes
            SET uses = uses + 1
            WHERE code = ?
        """, (code,))

        cur.execute("""
            INSERT INTO redeemed
            (user_id, code)
            VALUES (?, ?)
        """, (
            user.id,
            code
        ))

        conn.commit()
        conn.close()

        await update.message.reply_text(
            "🎉 <b>Redeem Successful!</b>\n\n"
            f"➕ {credits} Credits added!\n"
            f"💰 Total Credits: "
            f"<b>{get_credits(user.id)}</b>",
            parse_mode="HTML"
        )

        return

    # ----------------------------------------------
    # ADMIN ADD CREDITS
    # ----------------------------------------------

    if waiting_for == "admin_add":

        if user.id != ADMIN_ID:
            return

        context.user_data.pop(
            "waiting_for",
            None
        )

        try:

            user_id, amount = map(
                int,
                text.split()
            )

            add_credits(
                user_id,
                amount
            )

            await update.message.reply_text(
                f"✅ {amount} credits added to "
                f"<code>{user_id}</code>",
                parse_mode="HTML"
            )

        except Exception:

            await update.message.reply_text(
                "❌ Wrong format.\n\n"
                "Example:\n"
                "<code>123456789 10</code>",
                parse_mode="HTML"
            )

        return

    # ----------------------------------------------
    # ADMIN CREATE REDEEM
    # ----------------------------------------------

    if waiting_for == "admin_redeem":

        if user.id != ADMIN_ID:
            return

        context.user_data.pop(
            "waiting_for",
            None
        )

        try:

            code, credits, max_uses = text.split()

            credits = int(credits)
            max_uses = int(max_uses)

            conn = get_db()
            cur = conn.cursor()

            cur.execute("""
                INSERT OR REPLACE INTO redeem_codes
                (code, credits, max_uses, uses, active)
                VALUES (?, ?, ?, 0, 1)
            """, (
                code.upper(),
                credits,
                max_uses
            ))

            conn.commit()
            conn.close()

            await update.message.reply_text(
                "✅ <b>Redeem Created!</b>\n\n"
                f"🎟 Code: <code>{code.upper()}</code>\n"
                f"💰 Credits: {credits}\n"
                f"👥 Max Uses: {max_uses}",
                parse_mode="HTML"
            )

        except Exception:

            await update.message.reply_text(
                "❌ Wrong format.\n\n"
                "Example:\n"
                "<code>WELCOME10 10 100</code>",
                parse_mode="HTML"
            )

        return


# ==================================================
# ADMIN COMMAND
# ==================================================

async def admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "👑 <b>ADMIN PANEL</b>\n\n"
        "Developer Sohail Control Panel",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )


# ==================================================
# RUN BOT
# ==================================================

def main():

    if not BOT_TOKEN:
        print(
            "ERROR: BOT_TOKEN is missing!"
        )
        return

    init_db()

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("admin", admin)
    )

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    print("Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
