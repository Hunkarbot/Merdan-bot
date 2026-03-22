import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_KEY = os.getenv("API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")

headers = {
    "x-apisports-key": API_KEY
}

def get_matches():
    url = "https://v3.football.api-sports.io/fixtures?next=20"
    res = requests.get(url, headers=headers, timeout=20)
    data = res.json()
    return data.get("response", [])

def get_form(team_id):
    url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=5"
    res = requests.get(url, headers=headers, timeout=20)
    matches = res.json().get("response", [])

    wins = 0
    losses = 0
    scored = 0
    conceded = 0

    for m in matches:
        is_home = m["teams"]["home"]["id"] == team_id
        goals_for = m["goals"]["home"] if is_home else m["goals"]["away"]
        goals_against = m["goals"]["away"] if is_home else m["goals"]["home"]

        if goals_for > goals_against:
            wins += 1
        elif goals_for < goals_against:
            losses += 1

        if goals_for > 0:
            scored += 1
        if goals_against > 0:
            conceded += 1

    return wins, losses, scored, conceded

def analyze(match):
    home = match["teams"]["home"]["name"]
    away = match["teams"]["away"]["name"]
    home_id = match["teams"]["home"]["id"]
    away_id = match["teams"]["away"]["id"]

    hw, hl, hs, hc = get_form(home_id)
    aw, al, a_s, ac = get_form(away_id)

    if hs == 5 and hc == 5 and a_s == 5 and ac == 5:
        return f"🟢 BTTS → {home} vs {away}"

    if hw >= 4 and al >= 4:
        return f"💀 FAVORİ → {home} kazanır"
    if aw >= 4 and hl >= 4:
        return f"💀 FAVORİ → {away} kazanır"

    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot aktif kral 👑")

async def maclar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        matches = get_matches()

        if not matches:
            await update.message.reply_text("Maç verisi gelmedi kral. API_KEY kontrol et.")
            return

        btts_list = []
        fav_list = []

        for m in matches:
            result = analyze(m)
            if result:
                if "BTTS" in result:
                    btts_list.append(result)
                elif "FAVORİ" in result:
                    fav_list.append(result)

        mesaj = "🔥 GÜNLÜK SİSTEM 🔥\n\n"

        if btts_list:
            mesaj += "🟢 BTTS\n"
            for item in btts_list[:3]:
                mesaj += f"{item}\n"
            mesaj += "\n"

        if fav_list:
            mesaj += "💀 FAVORİ\n"
            for item in fav_list[:3]:
                mesaj += f"{item}\n"

        if not btts_list and not fav_list:
            mesaj += "Bugün filtreye tam uyan maç çıkmadı kral."

        await update.message.reply_text(mesaj)

    except Exception as e:
        await update.message.reply_text(f"Hata var kral: {e}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("maclar", maclar))

    print("Bot çalışıyor kral 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
