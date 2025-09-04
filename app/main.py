# app/main.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Header, HTTPException
from telegram import Update
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)
from app.db import SessionLocal, User, DailyLog

load_dotenv(override=True)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "dev-secret")

app = FastAPI(title="Accountability Coach API")

# ---------- DB helpers ----------
def upsert_user(chat_id: int):
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(tg_chat_id=chat_id).first()
        if not user:
            user = User(tg_chat_id=chat_id)
            db.add(user); db.commit(); db.refresh(user)
        return user
    finally:
        db.close()

# ---------- Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upsert_user(update.effective_chat.id)
    await update.message.reply_text(
        "👋 Hi! I’m your accountability coach.\n"
        "Use /log <what you ate/did> (e.g., /log 2 eggs + dal).\n"
        "Try /status to see your count."
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong")

async def log_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Usage: /log 2 eggs + dal + rice"); return
    db = SessionLocal()
    try:
        user = upsert_user(update.effective_chat.id)
        db.add(DailyLog(user_id=user.id, text_log=text)); db.commit()
    finally:
        db.close()
    await update.message.reply_text(f"✅ Saved log: {text}")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(tg_chat_id=update.effective_chat.id).first()
        if not user:
            await update.message.reply_text("Send /start first."); return
        count = db.query(DailyLog).filter_by(user_id=user.id).count()
        await update.message.reply_text(f"📊 You’ve logged {count} entries.")
    finally:
        db.close()

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("I understand: /start, /ping, /log, /status")

# One global PTB application reused by webhook
application: Application = ApplicationBuilder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("ping", ping))
application.add_handler(CommandHandler("log", log_cmd))
application.add_handler(CommandHandler("status", status_cmd))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback))

@app.on_event("startup")
async def on_startup():
    await application.initialize()
    await application.start()

@app.on_event("shutdown")
async def on_shutdown():
    await application.stop()
    await application.shutdown()

@app.get("/health")
async def health():
    return {"status": "ok"}
@app.get("/")
def home():
    return {"ok": True, "service": "Accountability Coach"}

@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
):
    if WEBHOOK_SECRET and x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="bad secret")
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}
