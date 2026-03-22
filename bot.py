import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
BOT_TOKEN = "8747036915:AAG9c4MRd6Fx-EDQOCpcxmFNGdRCAu995GE"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot aktif ✅")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    print("Bot çalışıyor...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main()) 
