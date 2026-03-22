import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN =  "8747036915:AAG9c4MRd6Fx-EDQOCpcxmFNGdRCAu995GE"
API_KEY = os.getenv("API_KEY")

HEADERS = {
    "x-apisports-key": API_KEY
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot aktif kral 👑\n"
        "Komutlar:\n"
        "/start\n"
        "/maclar"
    )


def get_matches():
    url = "https://v3.football.api-sports.io/fixtures?next=20"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data.get("response", [])


def get_form(team_id: int):
    url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=5"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    matches = r.json().get("response", [])

    wins = 0
    losses = 0
    scored = 0
    conceded = 0

    for m in matches:
        is_home = m["teams"]["home"]["id"] == team_id
        gf = m["goals"]["home"] if is_home else m["goals"]["away"]
        ga = m["goals"]["away"] if is_home else m["goals"]["home"]

        if gf > ga:
            wins += 1
        elif gf < ga:
            losses += 1

        if gf > 0:
            scored += 1
        if ga > 0:
            conceded += 1

    return wins, losses, scored, conceded


def analyze_match(match):
    home = match["teams"]["home"]["name"]
    away = match["teams"]["away"]["name"]
    home_id = match["teams"]["home"]["id"]
    away_id = match["teams"]["away"]["id"]

    hw, hl, hs, hc = get_form(home_id)
    aw, al, a_s, ac = get_form(away_id)

    # BTTS: iki takım da son 5 maçta gol atmış ve gol yemiş
    if hs == 5 and hc == 5 and a_s == 5 and ac == 5:
        return ("BTTS", f"🟢 BTTS → {home} vs {away}")

    # Favori: takım 4/5 kazanmış, rakip 4/5 kaybetmiş
    if hw >= 4 and al >= 4:
        return ("FAVORI", f"💀 FAVORİ → {home} kazanır")
    if aw >= 4 and hl >= 4:
        return ("FAVORI", f"💀 FAVORİ → {away} kazanır")

    return (None, None)


async def maclar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not API_KEY:
            await update.message.reply_text("API_KEY eksik kral.")
            return

        matches = get_matches()

        if not matches:
            await update.message.reply_text("Maç bulunamadı kral.")
            return

        btts_list = []
        fav_list = []

        for match in matches:
            kind, text = analyze_match(match)
            if kind == "BTTS":
                btts_list.append(text)
            elif kind == "FAVORI":
                fav_list.append(text)

        message = "🔥 GÜNLÜK SİSTEM 🔥\n\n"

        if btts_list:
            message += "🟢 BTTS ADAYLARI\n"
            for item in btts_list[:3]:
                message += item + "\n"
            message += "\n"

        if fav_list:
            message += "💀 FAVORİ ADAYLARI\n"
            for item in fav_list[:3]:
                message += item + "\n"

        if not btts_list and not fav_list:
            message += "Bugün filtreye uyan maç çıkmadı kral."

        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(f"Hata var kral: {e}")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("maclar", maclar))

    print("Bot calisiyor kral...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
