from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import os
BOT_TOKEN = os.getenv("BOT_TOKEN")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot aktif ✅")
    async def mesaj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Çalışıyorum 👍")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj))
print("Bot çalışıyor...")
app.run_polling() 
