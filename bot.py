import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = 8723446498:AAEE6KTtf9oMDUs419fFenVv0WFnEkmsDUo

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot aktif kral ✅")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main() 
