import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "8747036915:AAG9c4MRd6Fx-EDQOCpcxmFNGdRCAu995GE"
API_KEY = os.getenv("API_KEY")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot aktif 👑")

async def maclar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = "https://v3.football.api-sports.io/fixtures?next=10"
    headers = {"x-apisports-key": API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=20)

        if response.status_code != 200:
            await update.message.reply_text("API hata verdi kral ❌")
            return

        data = response.json()
        matches = data.get("response", [])

        if not matches:
            await update.message.reply_text("Maç bulunamadı kral.")
            return

        mesaj = "🔥 MAÇLAR 🔥\n\n"
        for m in matches[:5]:
            home = m["teams"]["home"]["name"]
            away = m["teams"]["away"]["name"]
            mesaj += f"{home} vs {away}\n"

        await update.message.reply_text(mesaj)

    except Exception as e:
        await update.message.reply_text(f"Hata var kral: {e}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("maclar", maclar))
    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
