import os 
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "8747036915:AAG9c4MRd6Fx-EDQOCpcxmFNGdRCAu995GE"
API_KEY =   "7395bc22c960b4acc60f71083c8f19" 
HEADERS = {"x-apisports-key": API_KEY}

BAD_LEAGUES = ["Ethiopia", "Kenya", "Tanzania"]
NIGHT_HOURS = {"18", "19", "20", "21", "22", "23", "00"}

def get_json(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        return r.json()
    except:
        return {}

def get_matches():
    data = get_json("https://v3.football.api-sports.io/fixtures?next=30")
    return data.get("response", [])

def last5(team_id):
    data = get_json(f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=5")
    return data.get("response", [])

def team_stats(team_id):
    games = last5(team_id)
    scored = conceded = wins = losses = btts = total_goals = 0

    for m in games:
        try:
            home_id = m["teams"]["home"]["id"]
            hg = m["goals"]["home"] or 0
            ag = m["goals"]["away"] or 0

            if team_id == home_id:
                gf, ga = hg, ag
            else:
                gf, ga = ag, hg

            if gf > 0:
                scored += 1
            if ga > 0:
                conceded += 1
            if gf > ga:
                wins += 1
            if gf < ga:
                losses += 1
            if gf > 0 and ga > 0:
                btts += 1

            total_goals += gf
        except:
            pass

    avg_goals = total_goals / len(games) if games else 0

    return {
        "scored": scored,
        "conceded": conceded,
        "wins": wins,
        "losses": losses,
        "btts": btts,
        "avg_goals": avg_goals
    }

def is_bad_league(match):
    country = str(match.get("league", {}).get("country", ""))
    league = str(match.get("league", {}).get("name", ""))
    text = f"{country} {league}"
    return any(x.lower() in text.lower() for x in BAD_LEAGUES)

def is_night_match(match):
    date_str = str(match.get("fixture", {}).get("date", ""))
    hour = date_str[11:13] if len(date_str) >= 13 else ""
    return hour in NIGHT_HOURS

def analyze_match(match):
    try:
        home_id = match["teams"]["home"]["id"]
        away_id = match["teams"]["away"]["id"]

        h = team_stats(home_id)
        a = team_stats(away_id)

        btts_score = 0
        fav_score = 0

        if h["scored"] == 5:
            btts_score += 20
        if h["conceded"] == 5:
            btts_score += 20
        if a["scored"] == 5:
            btts_score += 20
        if a["conceded"] == 5:
            btts_score += 20
        if h["btts"] == 5:
            btts_score += 10
        if a["btts"] == 5:
            btts_score += 10

        if h["wins"] >= 4:
            fav_score += 30
        if h["avg_goals"] >= 1.8:
            fav_score += 20
        if a["losses"] >= 3:
            fav_score += 20
        if a["conceded"] >= 4:
            fav_score += 20
        if h["scored"] >= 4:
            fav_score += 10

        if a["wins"] >= 4:
            fav_score_away = 30
        else:
            fav_score_away = 0
        if a["avg_goals"] >= 1.8:
            fav_score_away += 20
        if h["losses"] >= 3:
            fav_score_away += 20
        if h["conceded"] >= 4:
            fav_score_away += 20
        if a["scored"] >= 4:
            fav_score_away += 10

        if btts_score >= 90:
            return "BTTS", btts_score
        if fav_score >= 90:
            return "FAVORI 1", fav_score
        if fav_score_away >= 90:
            return "FAVORI 2", fav_score_away

        return None, 0
    except:
        return None, 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot aktif ✅ /maclar yaz")

async def maclar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matches = get_matches()
    picks = []

    for m in matches:
        if is_bad_league(m):
            continue

        market, score = analyze_match(m)
        if score < 90:
            continue

        home = m["teams"]["home"]["name"]
        away = m["teams"]["away"]["name"]
        saat = m["fixture"]["date"][11:16]
        lig = m["league"]["name"]
        gece = "🌙" if is_night_match(m) else ""

        picks.append({
            "text": f"{gece} ⚽ {home} vs {away}\n⏰ {saat}\n🏆 {lig}\n🎯 {market}\n📊 {score}/100\n",
            "night": 1 if is_night_match(m) else 0,
            "score": score
        })

    picks = sorted(picks, key=lambda x: (x["night"], x["score"]), reverse=True)

    if not picks:
        await update.message.reply_text("Bugün 90 üstü güvenli maç yok ❌")
        return

    text = "🔥 V2 90+ MAÇLAR\n\n" + "\n".join([p["text"] for p in picks[:5]])
    await update.message.reply_text(text)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("maclar", maclar))
    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
