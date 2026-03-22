import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("8747036915:AAG9c4MRd6Fx-EDQOCpcxmFNGdRCAu995GE"
API_KEY = os.getenv("7fb5f8cb38a416199abc19415a485fa7"

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot aktif kral 👑\n\n"
        "Komutlar:\n"
        "/start\n"
        "/maclar"
    )


def api_get(path: str, params: dict):
    r = requests.get(
        f"{BASE_URL}/{path}",
        headers=HEADERS,
        params=params,
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("response", [])


def get_next_matches():
    return api_get("fixtures", {"next": 20})


def get_last5_form(team_id: int):
    matches = api_get("fixtures", {"team": team_id, "last": 5})

    wins = 0
    losses = 0
    scored = 0
    conceded = 0

    for m in matches:
        home_id = m["teams"]["home"]["id"]
        away_id = m["teams"]["away"]["id"]
        home_goals = m["goals"]["home"]
        away_goals = m["goals"]["away"]

        if team_id == home_id:
            gf = home_goals
            ga = away_goals
        else:
            gf = away_goals
            ga = home_goals

        if gf is None:
            gf = 0
        if ga is None:
            ga = 0

        if gf > ga:
            wins += 1
        elif gf < ga:
            losses += 1

        if gf > 0:
            scored += 1
        if ga > 0:
            conceded += 1

    return {
        "wins": wins,
        "losses": losses,
        "scored": scored,
        "conceded": conceded,
    }


def analyze_match(match: dict):
    home_name = match["teams"]["home"]["name"]
    away_name = match["teams"]["away"]["name"]
    home_id = match["teams"]["home"]["id"]
    away_id = match["teams"]["away"]["id"]

    home_form = get_last5_form(home_id)
    away_form = get_last5_form(away_id)

    # BTTS 5/5
    if (
        home_form["scored"] == 5
        and home_form["conceded"] == 5
        and away_form["scored"] == 5
        and away_form["conceded"] == 5
    ):
        return {
            "type": "BTTS",
            "text": f"🟢 BTTS → {home_name} vs {away_name}",
        }

    # Favori 4/5 vs 4/5
    if home_form["wins"] >= 4 and away_form["losses"] >= 4:
        return {
            "type": "FAVORI",
            "text": f"💀 FAVORİ → {home_name} kazanır",
        }

    if away_form["wins"] >= 4 and home_form["losses"] >= 4:
        return {
            "type": "FAVORI",
            "text": f"💀 FAVORİ → {away_name} kazanır",
        }

    return None


async def maclar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not BOT_TOKEN:
            await update.message.reply_text("BOT_TOKEN eksik kral.")
            return

        if not API_KEY:
            await update.message.reply_text("API_KEY eksik kral.")
            return

        fixtures = get_next_matches()

        if not fixtures:
            await update.message.reply_text("Maç bulunamadı kral.")
            return

        btts_list = []
        favori_list = []

        for match in fixtures:
            result = analyze_match(match)
            if result:
                if result["type"] == "BTTS":
                    btts_list.append(result["text"])
                elif result["type"] == "FAVORI":
                    favori_list.append(result["text"])

        message = "🔥 GÜNLÜK SİSTEM 🔥\n\n"

        if btts_list:
            message += "🟢 BTTS ADAYLARI\n"
            for item in btts_list[:5]:
                message += item + "\n"
            message += "\n"

        if favori_list:
            message += "💀 FAVORİ ADAYLARI\n"
            for item in favori_list[:5]:
                message += item + "\n"

        if not btts_list and not favori_list:
            message += "Bugün filtreye uyan maç yok kral."

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
