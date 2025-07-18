import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime
import json
import os
import asyncio

# CONFIG - Use environment variables for production
BOT_TOKEN = os.getenv("7971235582:AAEohUAc-DeD2OXXYGn_v8j_i0mnfb9fSF8")  # Set in Railway variables
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1002825976737"))  # Your channel ID (must be negative)
DATA_FILE = "members.json"

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load or initialize user data
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        members = json.load(f)
else:
    members = {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(members, f)

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE, duration_days: int):
    user = update.effective_user
    user_id = str(user.id)
    expires_at = (datetime.datetime.utcnow() + datetime.timedelta(days=duration_days)).isoformat()

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

async def check_expired(bot):
    now = datetime.datetime.utcnow()
    to_remove = []
    for user_id, info in members.items():
        expires = datetime.datetime.fromisoformat(info["expires"])
        if now > expires:
            try:
                await bot.ban_chat_member(CHANNEL_ID, int(user_id))
                await bot.unban_chat_member(CHANNEL_ID, int(user_id))
            except Exception as e:
                logger.error(f"Failed to remove {user_id}: {e}")
            to_remove.append(user_id)
    
    for uid in to_remove:
        del members[uid]
    if to_remove:
        save_data()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /trial, /week or /month to get access.")

async def trial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await add_user(update, context, 3)

async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await add_user(update, context, 7)

async def month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await add_user(update, context, 30)

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("trial", trial))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(CommandHandler("month", month))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_expired, 'interval', hours=1, args=[app.bot])
    scheduler.start()

    logger.info("Bot is starting...")
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped gracefully")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
