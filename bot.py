import os
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_KEY = "9d815aaf3a5947e681eda9a895a281b5"
BOT_TOKEN = "8747036915:AAG9c4MRd6Fx-EDQOCpcxmFNGdRCAu995GE"

HEADERS = {"x-apisports-key": API_KEY}

def get_matches():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    url = f"https://v3.football.api-sports.io/fixtures?date={today}"
    r = requests.get(url, headers=HEADERS, timeout=20)
    return r.json().get("response", [])

def analyze(m):
    home = m["teams"]["home"]["name"]
    away = m["teams"]["away"]["name"]
    league = m["league"]["name"]

    good = ["Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"]

    if not any(g.lower() in league.lower() for g in good):
        return None

    strong = [
        "Manchester City", "Real Madrid", "Bayern Munich",
        "PSG", "Barcelona", "Liverpool", "Inter", "Arsenal"
    ]

    if any(s.lower() in home.lower() for s in strong):
        return f"🔥 {home} vs {away}\nMS1 ✅ (%80)"

    if any(s.lower() in away.lower() for s in strong):
        return f"🔥 {home} vs {away}\nMS2 ✅ (%80)"

    return None

async def maclar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matches = get_matches()

    if not matches:
        await update.message.reply_text("Veri yok ❌")
        return

    results = []

    for m in matches[:20]:
        r = analyze(m)
        if r:
            time = m["fixture"]["date"][11:16]
            results.append(f"{r}\nSaat: {time}")

    if results:
        await update.message.reply_text("\n\n".join(results[:5]))
    else:
        await update.message.reply_text("Bugün uygun maç yok ❌")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sistem hazır kral 👑\n/maclar yaz")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("maclar", maclar))
    app.run_polling()

if __name__ == "__main__":
    main()
