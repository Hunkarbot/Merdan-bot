import os
import requests
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "8747036915:AAES-UKrjW3xU891kX9s36sNn5gdaNlgaz8"
API_KEY = "9d815aaf3a5947e681eda9a895a281b5"

# Football-Data.org örnek bazlı yazıldı
BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}

# Çok API yememesi için
CACHE = {
    "matches": None,
    "time": None
}

# İstersen ligleri artırırız
LEAGUES = [
    "PL",    # Premier League
    "BL1",   # Bundesliga
    "SA",    # Serie A
    "PD",    # La Liga
    "FL1",   # Ligue 1
    "DED",   # Eredivisie
    "PPL",   # Primeira Liga
    "BSA"    # Brazil Serie A
]

def now_utc():
    return datetime.now(timezone.utc)

def safe_get(url, params=None):
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=20)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

def get_matches_today_and_tonight():
    # cache 15 dk
    if CACHE["matches"] and CACHE["time"]:
        if (now_utc() - CACHE["time"]).total_seconds() < 900:
            return CACHE["matches"]

    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)

    all_matches = []

    for code in LEAGUES:
        data = safe_get(
            f"{BASE_URL}/competitions/{code}/matches",
            params={
                "dateFrom": str(today),
                "dateTo": str(tomorrow)
            }
        )
        if not data or "matches" not in data:
            continue
        all_matches.extend(data["matches"])

    CACHE["matches"] = all_matches
    CACHE["time"] = now_utc()
    return all_matches

def get_team_matches(team_id, limit=5):
    data = safe_get(f"{BASE_URL}/teams/{team_id}/matches", params={"limit": limit, "status": "FINISHED"})
    if not data or "matches" not in data:
        return []
    return data["matches"][:limit]

def form_points(team_matches, team_id):
    pts = 0
    gf = 0
    ga = 0

    for m in team_matches:
        home_id = m["homeTeam"]["id"]
        away_id = m["awayTeam"]["id"]
        full = m.get("score", {}).get("fullTime", {})
        hs = full.get("home")
        aws = full.get("away")

        if hs is None or aws is None:
            continue

        is_home = home_id == team_id
        team_goals = hs if is_home else aws
        opp_goals = aws if is_home else hs

        gf += team_goals
        ga += opp_goals

        if team_goals > opp_goals:
            pts += 3
        elif team_goals == opp_goals:
            pts += 1

    return {
        "points": pts,
        "gf": gf,
        "ga": ga
    }

def team_strength_score(team_id):
    recent = get_team_matches(team_id, limit=5)
    if len(recent) < 3:
        return None

    fp = form_points(recent, team_id)

    # basit güç puanı
    score = 0
    score += fp["points"] * 6
    score += fp["gf"] * 2
    score -= fp["ga"] * 2

    return {
        "score": score,
        "points": fp["points"],
        "gf": fp["gf"],
        "ga": fp["ga"]
    }

def analyze_match(match):
    if match.get("status") not in ["TIMED", "SCHEDULED"]:
        return None

    home = match["homeTeam"]
    away = match["awayTeam"]

    home_data = team_strength_score(home["id"])
    away_data = team_strength_score(away["id"])

    if not home_data or not away_data:
        return None

    diff = home_data["score"] - away_data["score"]

    # favori belirleme
    if diff >= 18:
        fav = home["name"]
        underdog = away["name"]
        confidence = min(93, 70 + diff)
        side = "1"
    elif diff <= -18:
        fav = away["name"]
        underdog = home["name"]
        confidence = min(93, 70 + abs(diff))
        side = "2"
    else:
        return None

    # çok düşük kalite maçları ele
    if confidence < 82:
        return None

    utc_date = match["utcDate"]
    try:
        dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
        local_dt = dt + timedelta(hours=1)  # Almanya için kaba yaklaşım
        saat = local_dt.strftime("%d.%m.%Y %H:%M")
    except:
        saat = utc_date

    competition = match.get("competition", {}).get("name", "Bilinmeyen Lig")

    return {
        "league": competition,
        "time": saat,
        "home": home["name"],
        "away": away["name"],
        "favorite": fav,
        "opponent": underdog,
        "confidence": confidence,
        "pick": side,
        "reason": (
            f"Son 5 form farkı yüksek | "
            f"{home['name']} puan:{home_data['points']} gol:{home_data['gf']}-{home_data['ga']} | "
            f"{away['name']} puan:{away_data['points']} gol:{away_data['gf']}-{away_data['ga']}"
        )
    }

def find_best_favorites():
    matches = get_matches_today_and_tonight()
    picks = []

    for match in matches:
        try:
            analyzed = analyze_match(match)
            if analyzed:
                picks.append(analyzed)
        except:
            continue

    picks = sorted(picks, key=lambda x: x["confidence"], reverse=True)

    # aynı takımı tekrar tekrar verme ihtimalini azalt
    used = set()
    final = []
    for p in picks:
        key1 = p["home"]
        key2 = p["away"]
        if key1 in used or key2 in used:
            continue
        final.append(p)
        used.add(key1)
        used.add(key2)
        if len(final) >= 5:
            break

    return final

def format_picks(picks):
    if not picks:
        return (
            "Bugün filtreye uyan güçlü favori çıkmadı.\n\n"
            "Sebep:\n"
            "- Güven puanı yeterli değil\n"
            "- Son 5 maç verisi zayıf\n"
            "- Maçlar dengeli\n\n"
            "Daha gevşek filtre istersek 3-5 maç çıkarmak kolay."
        )

    text = "🔥 Bugünün En Güçlü Favorileri\n\n"

    for i, p in enumerate(picks, 1):
        text += (
            f"{i}) {p['home']} vs {p['away']}\n"
            f"🏆 Lig: {p['league']}\n"
            f"⏰ Saat: {p['time']}\n"
            f"✅ Favori: {p['favorite']}\n"
            f"🎯 Tercih: Maç Sonucu {p['pick']}\n"
            f"📊 Güven: {p['confidence']}/100\n"
            f"📝 Neden: {p['reason']}\n\n"
        )

    text += "Not: Bu sistem risk azaltır ama garanti vermez."
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "Hoş geldin kral 👊\n\n"
        "Komutlar:\n"
        "/maclar - Bugünün en güçlü favori maçlarını getirir\n"
    )
    await update.message.reply_text(msg)

async def maclar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bugünün maçlarını tarıyorum...")

    picks = find_best_favorites()
    msg = format_picks(picks)

    # Telegram mesaj limiti için böl
    for i in range(0, len(msg), 3900):
        await update.message.reply_text(msg[i:i+3900])

def main():
    if not BOT_TOKEN or not API_KEY:
        print("HATA: BOT_TOKEN veya API_KEY eksik.")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("maclar", maclar))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
