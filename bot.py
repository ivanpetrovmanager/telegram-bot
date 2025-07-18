import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime
import json
import os
import asyncio
import sys

# ✅ Your Bot Token and Channel ID
BOT_TOKEN = "7971235582:AAEohUAc-DeD2OXXYGn_v8j_i0mnfb9fSF8"
CHANNEL_ID = -1002825976737
DATA_FILE = "members.json"

# ✅ Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ✅ Load user data
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        members = json.load(f)
else:
    members = {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(members, f)

# ✅ Invite user
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE, duration_days: int):
    user = update.effective_user
    user_id = str(user.id)
    expires_at = (datetime.datetime.utcnow() + datetime.timedelta(days=duration_days)).isoformat()

    try:
        invite_link = await context.bot.create_chat_invite_link(CHANNEL_ID, member_limit=1)
        await update.message.reply_text(f"✅ Click to join the channel: {invite_link.invite_link}")
    except Exception as e:
        await update.message.reply_text(f"❌ Couldn't create invite link: {e}")
        logger.error(f"Invite error for {user_id}: {e}")
        return

    members[user_id] = {
        "username": user.username,
        "expires": expires_at
    }
    save_data()

# ✅ Remove expired users
async def check_expired(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.utcnow()
    to_remove = []

    for user_id, info in members.items():
        try:
            expires = datetime.datetime.fromisoformat(info["expires"])
            if now > expires:
                try:
                    await context.bot.ban_chat_member(CHANNEL_ID, int(user_id))
                    await context.bot.unban_chat_member(CHANNEL_ID, int(user_id))
                    logger.info(f"Removed expired user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to remove {user_id}: {e}")
                to_remove.append(user_id)
        except Exception:
            continue

    for uid in to_remove:
        del members[uid]
    if to_remove:
        save_data()

# ✅ Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Use /trial, /week or /month to get access.")

async def trial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await add_user(update, context, 3)

async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await add_user(update, context, 7)

async def month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await add_user(update, context, 30)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in members:
        expires = members[user_id]["expires"]
        await update.message.reply_text(f"⏳ Your access expires at: {expires}")
    else:
        await update.message.reply_text("❌ You're not subscribed.")

# ✅ Main bot startup
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("trial", trial))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(CommandHandler("month", month))
    app.add_handler(CommandHandler("status", status))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_expired, 'interval', hours=1, args=[app.bot])
    scheduler.start()

    logger.info("🚀 Bot is running...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.updater.idle()

# ✅ Railway-compatible runner
if __name__ == "__main__":
    async def _main():
        try:
            await main()
        except Exception as e:
            logger.error(f"❌ Bot crashed: {e}")
            sys.exit(1)

    asyncio.get_event_loop().create_task(_main())
    asyncio.get_event_loop().run_forever()
