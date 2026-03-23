
import os
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_KEY = "db7395bc22c960b4acc60f71083c8f19"
BOT_TOKEN = "8747036915:AAG9c4MRd6Fx-EDQOCpcxmFNGdRCAu995GE" 

HEADERS = {"x-apisports-key": API_KEY}

# 🔥 SON 5 MAÇ FORM
def get_last5(team_id):
    url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=5"
    r = requests.get(url, headers=HEADERS).json()
    matches = r.get("response", [])

    scored = 0
    conceded = 0
    wins = 0

    for m in matches:
        home = m["teams"]["home"]["id"]
        goals_home = m["goals"]["home"]
        goals_away = m["goals"]["away"]

        if home == team_id:
            scored += goals_home
            conceded += goals_away
            if goals_home > goals_away:
                wins += 1
        else:
            scored += goals_away
            conceded += goals_home
            if goals_away > goals_home:
                wins += 1

    return wins, scored, conceded

# 🔥 BUGÜNÜN MAÇLARI
def get_matches():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    url = f"https://v3.football.api-sports.io/fixtures?date={today}"
    r = requests.get(url, headers=HEADERS).json()
    return r.get("response", [])

# 🔥 ANALİZ
def analyze(match):
    home_team = match["teams"]["home"]["name"]
    away_team = match["teams"]["away"]["name"]

    home_id = match["teams"]["home"]["id"]
    away_id = match["teams"]["away"]["id"]

    hw, hs, hc = get_last5(home_id)
    aw, as_, ac = get_last5(away_id)

    # EZİCİ FAVORİ KURALI
    if hw >= 4 and aw <= 1 and hs >= 8:
        return f"🔥 {home_team} vs {away_team}\nMS1 ✅\nForm: {hw}G - {aw}G\nGüven: %88"

    if aw >= 4 and hw <= 1 and as_ >= 8:
        return f"🔥 {home_team} vs {away_team}\nMS2 ✅\nForm: {aw}G - {hw}G\nGüven: %88"

    return None

# 🔥 KOMUT
async def maclar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matches = get_matches()

    results = []

    for m in matches:
        analiz = analyze(m)
        if analiz:
            time = m["fixture"]["date"][11:16]
            results.append(f"{analiz}\nSaat: {time}")

    if results:
        await update.message.reply_text("\n\n".join(results[:5]))
    else:
        await update.message.reply_text("Bugün kriterlere uyan NET maç yok ❌")

# 🔥 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Analiz botu hazır kral 👑\n/maclar yaz")

# 🔥 MAIN
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("maclar", maclar))
    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
