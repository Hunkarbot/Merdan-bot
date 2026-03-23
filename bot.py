import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_KEY = "9d815aaf3a5947e681eda9a895a281b5"
BOT_TOKEN = "8747036915:AAG9c4MRd6Fx-EDQOCpcxmFNGdRCAu995GE"

HEADERS = {"x-apisports-key": API_KEY}

# 🔥 API TEST
async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        url = "https://v3.football.api-sports.io/status"
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()

        if "errors" in data and data["errors"]:
            await update.message.reply_text(f"❌ API HATA:\n{data['errors']}")
        else:
            await update.message.reply_text(f"✅ API AKTİF\n\n{data}")

    except Exception as e:
        await update.message.reply_text(f"❌ BAĞLANTI HATASI:\n{e}")

# 🔥 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Test bot hazır kral 👑\n/test yaz")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test))

    print("Test bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
