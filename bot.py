import logging
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import json
import os

# CONFIG
BOT_TOKEN = "7971235582:AAEohUAc-DeD2OXXYGn_v8j_i0mnfb9fSF8"
CHANNEL_ID = -1002825976737  # Your channel ID, must be an integer and negative for private channels
DATA_FILE = "members.json"

# Setup logging
logging.basicConfig(level=logging.INFO)

# Load or initialize user data
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        members = json.load(f)
else:
    members = {}

# Save user data
def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(members, f)

# Add user
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE, duration_days: int):
    user = update.effective_user
    user_id = str(user.id)
    expires_at = (datetime.datetime.utcnow() + datetime.timedelta(days=duration_days)).isoformat()

    # Add user to channel
    try:
        await context.bot.invite_chat_member(CHANNEL_ID, user.id)
    except Exception as e:
        await update.message.reply_text(f"❌ Couldn't invite you: {e}")
        return

    members[user_id] = {
        "username": user.username,
        "expires": expires_at
    }
    save_data()
    await update.message.reply_text(f"✅ Added to channel for {duration_days} days.")

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /trial, /week or /month to get access.")

async def trial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await add_user(update, context, 3)

async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await add_user(update, context, 7)

async def month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await add_user(update, context, 30)

# Scheduled job to check expired users
async def check_expired(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.utcnow()
    to_remove = []
    for user_id, info in members.items():
        expires = datetime.datetime.fromisoformat(info["expires"])
        if now > expires:
            try:
                await context.bot.ban_chat_member(CHANNEL_ID, int(user_id))
                await context.bot.unban_chat_member(CHANNEL_ID, int(user_id))  # Optional: unban so they can rejoin later
            except Exception as e:
                print(f"Failed to remove {user_id}: {e}")
            to_remove.append(user_id)
    for uid in to_remove:
        del members[uid]
    save_data()

# Main application
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("trial", trial))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(CommandHandler("month", month))

    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: app.create_task(check_expired(app.bot)), 'interval', hours=1)
    scheduler.start()

    print("Bot is running...")
    await app.run_polling()

# Entry point
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
