
import os
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_KEY = "db7395bc22c960b4acc60f71083c8f19"
BOT_TOKEN =  "8747036915:AAG9c4MRd6Fx-EDQOCpcxmFNGdRCAu995GE"

# 🔥 MAÇLARI ÇEK
def get_matches():
    url = "https://v3.football.api-sports.io/fixtures?date=" + datetime.now().strftime("%Y-%m-%d")
    headers = {"x-apisports-key": API_KEY}
    res = requests.get(url, headers=headers).json()
    return res.get("response", [])

# 🔥 EZİCİ FAVORİ ANALİZ
def analyze_match(match):
    home = match["teams"]["home"]["name"]
    away = match["teams"]["away"]["name"]

    home_goals = match["goals"]["home"]
    away_goals = match["goals"]["away"]

    # Basit güç kontrolü (geliştirilebilir)
    if home_goals is not None and away_goals is not None:
        if home_goals >= 2 and (home_goals - away_goals) >= 2:
            return f"🔥 {home} vs {away}\nTahmin: MS1 ✅ (EZİCİ FAVORİ)"
        elif away_goals >= 2 and (away_goals - home_goals) >= 2:
            return f"🔥 {home} vs {away}\nTahmin: MS2 ✅ (EZİCİ FAVORİ)"

    return None

# 🔥 KOMUT
async def maclar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matches = get_matches()
    results = []

    for m in matches:
        analiz = analyze_match(m)
        if analiz:
            time = m["fixture"]["date"][11:16]
            results.append(f"{analiz}\nSaat: {time}\n")

    if results:
        await update.message.reply_text("\n\n".join(results[:5]))
    else:
        await update.message.reply_text("Bugün net favori bulunamadı ❌")

# 🔥 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot hazır kral 👑\n/maclar yaz")

# 🔥 MAIN
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("maclar", maclar))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
