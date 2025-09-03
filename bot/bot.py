import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# DB imports
from app.db import SessionLocal, User, DailyLog

load_dotenv(override=True)  # ensure .env wins
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def upsert_user(chat_id: int):
    """Create the user if not exists, else return existing."""
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(tg_chat_id=chat_id).first()
        if not user:
            user = User(tg_chat_id=chat_id)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    finally:
        db.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    upsert_user(chat_id)
    await update.message.reply_text(
        "👋 Hi! I’m your accountability coach.\n"
        "Use /log <what you ate/did> (e.g., /log 2 eggs + dal).\n"
        "Try /status to see how many entries you’ve logged."
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong")

async def log_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = upsert_user(chat_id)

    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Usage: /log 2 eggs + dal + rice")
        return

    db = SessionLocal()
    try:
        db.add(DailyLog(user_id=user.id, text_log=text))
        db.commit()
    finally:
        db.close()

    await update.message.reply_text(f"✅ Saved log: {text}")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(tg_chat_id=chat_id).first()
        if not user:
            await update.message.reply_text("Send /start first.")
            return
        count = db.query(DailyLog).filter_by(user_id=user.id).count()
        await update.message.reply_text(f"📊 You’ve logged {count} entries.")
    finally:
        db.close()

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("I understand: /start, /ping, /log, /status")

def main():
    if not TOKEN:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN in your .env file")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("log", log_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback))
    app.run_polling()

if __name__ == "__main__":
    main()
