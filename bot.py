import os
from telegram.ext import ApplicationBuilder, CommandHandler

token = os.getenv("BOT_TOKEN")

async def start(update, context):
    await update.message.reply_text("Bot aktif kral ✅")

app = ApplicationBuilder().token(token).build()
app.add_handler(CommandHandler("start", start))
app.run_polling()
