import os
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_KEY = "db7395bc22c960b4acc60f71083c8f19"
BOT_TOKEN = "8747036915:AAG9c4MRd6Fx-EDQOCpcxmFNGdRCAu995GE"
HEADERS = {"x-apisports-key": API_KEY}

GOOD_LEAGUES = [39, 140, 78, 135, 61]  # EPL, LaLiga, Bundesliga, Serie A, Ligue 1

def api_get(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def get_matches():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    url = f"https://v3.football.api-sports.io/fixtures?date={today}"
    data = api_get(url)
    return data.get("response", []), data

def get_last5(team_id):
    url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=5"
    data = api_get(url)
    return data.get("response", []), data

def team_stats(team_id):
    matches, raw = get_last5(team_id)

    if len(matches) < 5:
        return None, f"last5 eksik ({len(matches)})"

    wins = 0
    scored = 0
    conceded = 0

    for m in matches:
        home_id = m["teams"]["home"]["id"]
        away_id = m["teams"]["away"]["id"]
        gh = m["goals"]["home"]
        ga = m["goals"]["away"]

        if gh is None or ga is None:
            continue

        if team_id == home_id:
            scored += gh
            conceded += ga
            if gh > ga:
                wins += 1
        elif team_id == away_id:
            scored += ga
            conceded += gh
            if ga > gh:
                wins += 1

    return {
        "wins": wins,
        "scored": scored,
        "conceded": conceded
    }, None

def analyze_match(match):
    league_id = match["league"]["id"]
    league_name = match["league"]["name"]
    home_name = match["teams"]["home"]["name"]
    away_name = match["teams"]["away"]["name"]
    home_id = match["teams"]["home"]["id"]
    away_id = match["teams"]["away"]["id"]

    if league_id not in GOOD_LEAGUES:
        return None, f"lig elendi: {league_name}"

    home_stats, home_err = team_stats(home_id)
    if home_err:
        return None, f"{home_name}: {home_err}"

    away_stats, away_err = team_stats(away_id)
    if away_err:
        return None, f"{away_name}: {away_err}"

    home_wins = home_stats["wins"]
    away_wins = away_stats["wins"]
    home_scored = home_stats["scored"]
    away_scored = away_stats["scored"]

    # daha yumuşak kriter
    if home_wins >= 3 and away_wins <= 2 and home_scored >= 7:
        return (
            f"🔥 {home_name} vs {away_name}\n"
            f"Tahmin: MS1 ✅\n"
            f"Form: {home_wins}G vs {away_wins}G\n"
            f"Gol gücü: {home_scored}-{away_scored}\n"
            f"Güven: %82"
        ), None

    if away_wins >= 3 and home_wins <= 2 and away_scored >= 7:
        return (
            f"🔥 {home_name} vs {away_name}\n"
            f"Tahmin: MS2 ✅\n"
            f"Form: {away_wins}G vs {home_wins}G\n"
            f"Gol gücü: {away_scored}-{home_scored}\n"
            f"Güven: %82"
        ), None

    return None, (
        f"{home_name} - {away_name} elendi | "
        f"home_wins={home_wins}, away_wins={away_wins}, "
        f"home_scored={home_scored}, away_scored={away_scored}"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Analiz botu hazır kral 👑\n/maclar yaz")

async def maclar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matches, raw = get_matches()

    if not matches:
        msg = "Bugün maç verisi gelmedi ❌"
        if "errors" in raw:
            msg += f"\nAPI errors: {raw['errors']}"
        await update.message.reply_text(msg)
        return

    # sadece ilk 20 maç
    matches = matches[:20]

    found = []
    reasons = []

    for m in matches:
        result, reason = analyze_match(m)
        if result:
            time_text = m["fixture"]["date"][11:16]
            found.append(f"{result}\nSaat: {time_text}")
        else:
            reasons.append(reason)

    if found:
        await update.message.reply_text("\n\n".join(found[:3]))
    else:
        text = "Bugün kriterlere uyan NET maç yok ❌\n\nİlk eleme nedenleri:\n"
        text += "\n".join(reasons[:8])
        await update.message.reply_text(text[:4000])

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("maclar", maclar))
    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
