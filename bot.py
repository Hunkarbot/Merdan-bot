import os
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("8747036915:AAG9c4MRd6Fx-EDQOCpcxmFNGdRCAu995GE"
API_KEY = os.getenv("db7395bc22c960b4acc60f71083c8f19"

HIGH_SCORING_LEAGUES = [39, 78, 61, 135, 140]  
# Premier League, Bundesliga, Ligue1, Serie A, La Liga

def get_matches():
    today = datetime.utcnow().strftime("%Y-%m-%d")

    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": API_KEY}
    params = {"date": today}

    res = requests.get(url, headers=headers, params=params)
    data = res.json()

    return data.get("response", [])

def analyze_matches(matches):
    picks = []

    for m in matches:
        league_id = m["league"]["id"]

        # sadece iyi ligler
        if league_id in HIGH_SCORING_LEAGUES:

            home = m["teams"]["home"]["name"]
            away = m["teams"]["away"]["name"]
            time = m["fixture"]["date"][11:16]

            picks.append(f"🔥 {home} vs {away}\n🕒 {time}\n👉 ÜST 2.5 ADAYI")

        if len(picks) >= 5:
            break

    return picks

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot aktif kral ✅\n/maclar yaz")

async def maclar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        matches = get_matches()

        if not matches:
            await update.message.reply_text("Bugün veri yok ❌")
            return

        analyzed = analyze_matches(matches)

        if not analyzed:
            await update.message.reply_text("Uygun maç bulunamadı ❌")
            return

        mesaj = "🔥 BUGÜNÜN ANALİZLİ MAÇLARI 🔥\n\n"

        for m in analyzed:
            mesaj += m + "\n\n"

        await update.message.reply_text(mesaj)

    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("maclar", maclar))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
