import os
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN =  "8747036915:AAG9c4MRd6Fx-EDQOCpcxmFNGdRCAu995GE"
API_KEY =  " db7395bc22c960b4acc60f71083c8f19"

BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

def bugunun_tarihi():
    return datetime.now().strftime("%Y-%m-%d")

def fixtures_today():
    url = f"{BASE_URL}/fixtures"
    params = {"date": bugunun_tarihi()}
    r = requests.get(url, headers=HEADERS, params=params, timeout=20)
    r.raise_for_status()
    return r.json().get("response", [])

def get_standings(league_id, season):
    url = f"{BASE_URL}/standings"
    params = {"league": league_id, "season": season}
    r = requests.get(url, headers=HEADERS, params=params, timeout=20)
    r.raise_for_status()
    data = r.json().get("response", [])

    if not data:
        return {}

    tables = data[0].get("league", {}).get("standings", [])
    if not tables or not tables[0]:
        return {}

    team_map = {}
    for row in tables[0]:
        team_id = row["team"]["id"]
        team_map[team_id] = {
            "rank": row.get("rank", 999),
            "points": row.get("points", 0),
            "goalsDiff": row.get("goalsDiff", 0),
            "form": row.get("form", "")
        }
    return team_map

def guven_skoru(home_data, away_data):
    home_rank = home_data.get("rank", 999)
    away_rank = away_data.get("rank", 999)
    home_points = home_data.get("points", 0)
    away_points = away_data.get("points", 0)
    home_gd = home_data.get("goalsDiff", 0)
    away_gd = away_data.get("goalsDiff", 0)

    rank_gap = away_rank - home_rank
    points_gap = home_points - away_points
    gd_gap = home_gd - away_gd

    score = 50
    score += rank_gap * 4
    score += points_gap * 0.8
    score += gd_gap * 0.5

    if score > 99:
        score = 99
    if score < 1:
        score = 1

    return round(score)

def analiz_yap():
    fixtures = fixtures_today()
    if not fixtures:
        return []

    standings_cache = {}
    secimler = []

    for fx in fixtures:
        league = fx.get("league", {})
        teams = fx.get("teams", {})
        fixture = fx.get("fixture", {})

        league_id = league.get("id")
        league_name = league.get("name", "Bilinmeyen Lig")
        country = league.get("country", "")
        season = league.get("season")

        home = teams.get("home", {})
        away = teams.get("away", {})

        home_id = home.get("id")
        away_id = away.get("id")
        home_name = home.get("name", "Ev Sahibi")
        away_name = away.get("name", "Deplasman")

        match_time = fixture.get("date", "")
        if match_time:
            try:
                match_time = datetime.fromisoformat(match_time.replace("Z", "+00:00")).strftime("%H:%M")
            except:
                match_time = "Saat yok"
        else:
            match_time = "Saat yok"

        cache_key = f"{league_id}_{season}"
        if cache_key not in standings_cache:
            try:
                standings_cache[cache_key] = get_standings(league_id, season)
            except:
                standings_cache[cache_key] = {}

        table = standings_cache[cache_key]
        if home_id not in table or away_id not in table:
            continue

        home_data = table[home_id]
        away_data = table[away_id]

        if home_data["rank"] >= away_data["rank"]:
            continue

        skor = guven_skoru(home_data, away_data)

        secimler.append({
            "lig": f"{country} - {league_name}",
            "saat": match_time,
            "mac": f"{home_name} vs {away_name}",
            "tahmin": f"{home_name} kazanır",
            "puan": skor,
            "home_rank": home_data["rank"],
            "away_rank": away_data["rank"],
            "home_points": home_data["points"],
            "away_points": away_data["points"],
        })

    secimler = sorted(secimler, key=lambda x: x["puan"], reverse=True)
    return secimler[:5]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot aktif kral ✅\n"
        "/maclar yazarak bugünün en güvenli maçlarını test et."
    )

async def maclar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not BOT_TOKEN:
            await update.message.reply_text("Hata kral ❌ BOT_TOKEN yok")
            return

        if not API_KEY:
            await update.message.reply_text("Hata kral ❌ API_KEY yok")
            return

        picks = analiz_yap()

        if not picks:
            await update.message.reply_text(
                "Bugün testte net favori maç bulunamadı ❌\n"
                "Ama bot çalışıyor, komut çalışıyor.\n"
                "Sorun veri ya da filtre tarafında olabilir."
            )
            return

        mesaj = "Bugünün test amaçlı en güvenli maçları 👑\n\n"

        for i, p in enumerate(picks, start=1):
            mesaj += (
                f"{i}) {p['mac']}\n"
                f"Lig: {p['lig']}\n"
                f"Saat: {p['saat']}\n"
                f"Tahmin: {p['tahmin']}\n"
                f"Güven: {p['puan']}/100\n"
                f"Sıralama: {p['home_rank']}. sıra vs {p['away_rank']}. sıra\n"
                f"Puan farkı: {p['home_points']} - {p['away_points']}\n\n"
            )

        await update.message.reply_text(mesaj)

    except Exception as e:
        await update.message.reply_text(f"Hata oluştu kral ❌\n{str(e)}")

def main():
    if not BOT_TOKEN:
        print("HATA: BOT_TOKEN bulunamadı")
        return

    if not API_KEY:
        print("HATA: API_KEY bulunamadı")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("maclar", maclar))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
