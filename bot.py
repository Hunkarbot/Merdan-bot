import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot aktif kral ✅")

async def analiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = "🔥 GÜNÜN MAÇLARI:\n\n"
    maclar = [
        "Fenerbahçe vs Kasımpaşa",
        "Galatasaray vs Rizespor",
        "Liverpool vs Brighton"
    ]
    for mac in maclar:
        mesaj += f"⚽ {mac}\n"
    await update.message.reply_text(mesaj)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analiz", analiz))
    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
