import os 
import time
import requests
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_KEY = "9d815aaf3a5947e681eda9a895a281b5"
BOT_TOKEN = "8747036915:AAES-UKrjW3xU891kX9s36sNn5gdaNlgaz8"

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# Gollü ligler
GOLLU_LIGLER = [
    "Eredivisie",
    "Bundesliga",
    "Belgium",
    "MLS",
    "A-League",
    "Austria",
    "Switzerland",
    "Denmark",
    "Norway",
    "Sweden",
    "Czech"
]

# API koruma ve hafıza
team_cache = {}
fixture_cache = {}

def is_gollu_lig(league_name: str, country_name: str) -> bool:
    text = f"{country_name} {league_name}".lower()
    return any(lig.lower() in text for lig in GOLLU_LIGLER)

def get_dates():
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    return today, tomorrow

def safe_request(url: str, params: dict):
    try:
        print("API istek:", url, params)
        res = requests.get(url, headers=HEADERS, params=params, timeout=30)
        data = res.json()
        time.sleep(1)  # API koruma
        return data
    except Exception as e:
        print("API hatası:", e)
        return {}

def fetch_fixtures_by_date(date_str: str):
    if date_str in fixture_cache:
        print("Cache fixtures kullanıldı:", date_str)
        return fixture_cache[date_str]

    url = f"{BASE_URL}/fixtures"
    params = {"date": date_str}
    data = safe_request(url, params)
    matches = data.get("response", [])
    fixture_cache[date_str] = matches
    print(f"{date_str} için çekilen maç sayısı:", len(matches))
    return matches

def get_all_relevant_matches():
    today, tomorrow = get_dates()
    print("Bugün tarihi:", today)
    print("Yarın tarihi:", tomorrow)

    today_matches = fetch_fixtures_by_date(today)
    tomorrow_matches = fetch_fixtures_by_date(tomorrow)

    print("Bugün maç sayısı:", len(today_matches))
    print("Yarın maç sayısı:", len(tomorrow_matches))

    all_matches = today_matches + tomorrow_matches
    filtered = []

    for m in all_matches:
        league_name = m["league"]["name"]
        country = m["league"]["country"]
        home_team = m["teams"]["home"]["name"]
        away_team = m["teams"]["away"]["name"]

        print("Lig filtresini geçti:", home_team, "vs", away_team, "|", country, "-", league_name)
        filtered.append(m)

    print("Filtre sonrası maç sayısı:", len(filtered))
    return filtered

def get_last5(team_id: int):
    if team_id in team_cache:
        print("Cache takım kullanıldı:", team_id)
        return team_cache[team_id]

    url = f"{BASE_URL}/fixtures"
    params = {"team": team_id, "last": 5}
    data = safe_request(url, params)
    matches = data.get("response", [])
    team_cache[team_id] = matches
    print(f"Takım {team_id} son 5 maç sayısı:", len(matches))
    return matches

def analyze_team_stats(team_id: int, matches: list):
    if len(matches) < 5:
        print("Yetersiz son 5 verisi:", team_id, "->", len(matches))
        return None

    scored_total = 0
    conceded_total = 0
    scored_count = 0
    conceded_count = 0
    over25_count = 0
    under25_count = 0
    wins = 0
    draws = 0
    losses = 0

    for m in matches:
        home_id = m["teams"]["home"]["id"]
        away_id = m["teams"]["away"]["id"]
        home_goals = m["goals"]["home"]
        away_goals = m["goals"]["away"]

        if home_goals is None or away_goals is None:
            print("Gol verisi eksik:", team_id)
            return None

        if team_id == home_id:
            scored = home_goals
            conceded = away_goals
        elif team_id == away_id:
            scored = away_goals
            conceded = home_goals
        else:
            print("Takım maç içinde bulunamadı:", team_id)
            return None

        total_goals = home_goals + away_goals

        scored_total += scored
        conceded_total += conceded

        if scored > 0:
            scored_count += 1
        if conceded > 0:
            conceded_count += 1

        if total_goals >= 3:
            over25_count += 1
        else:
            under25_count += 1

        if scored > conceded:
            wins += 1
        elif scored == conceded:
            draws += 1
        else:
            losses += 1

    stats = {
        "avg_scored": scored_total / 5,
        "avg_conceded": conceded_total / 5,
        "scored_count": scored_count,
        "conceded_count": conceded_count,
        "over25_count": over25_count,
        "under25_count": under25_count,
        "wins": wins,
        "draws": draws,
        "losses": losses
    }

    print(f"Team {team_id} stats:", stats)
    return stats

def score_btts(home_stats, away_stats):
    score = 0

    if home_stats["scored_count"] >= 4:
        score += 20
    if away_stats["scored_count"] >= 4:
        score += 20
    if home_stats["conceded_count"] >= 4:
        score += 20
    if away_stats["conceded_count"] >= 4:
        score += 20

    if home_stats["avg_scored"] >= 1.2:
        score += 10
    if away_stats["avg_scored"] >= 1.2:
        score += 10

    return min(score, 100)

def score_over25(home_stats, away_stats):
    score = 0

    if home_stats["over25_count"] >= 4:
        score += 25
    if away_stats["over25_count"] >= 4:
        score += 25

    if home_stats["avg_scored"] >= 1.4:
        score += 10
    if away_stats["avg_scored"] >= 1.4:
        score += 10

    if home_stats["avg_conceded"] >= 1.2:
        score += 15
    if away_stats["avg_conceded"] >= 1.2:
        score += 15

    return min(score, 100)

def score_under25(home_stats, away_stats):
    score = 0

    if home_stats["under25_count"] >= 4:
        score += 25
    if away_stats["under25_count"] >= 4:
        score += 25

    if home_stats["avg_scored"] <= 1.0:
        score += 10
    if away_stats["avg_scored"] <= 1.0:
        score += 10

    if home_stats["avg_conceded"] <= 1.0:
        score += 15
    if away_stats["avg_conceded"] <= 1.0:
        score += 15

    return min(score, 100)

def score_ms(home_stats, away_stats):
    home_score = 0
    away_score = 0

    home_score += home_stats["wins"] * 12
    home_score += max(0, (home_stats["avg_scored"] - away_stats["avg_conceded"])) * 10
    home_score += max(0, (away_stats["losses"] - home_stats["losses"])) * 4

    away_score += away_stats["wins"] * 12
    away_score += max(0, (away_stats["avg_scored"] - home_stats["avg_conceded"])) * 10
    away_score += max(0, (home_stats["losses"] - away_stats["losses"])) * 4

    home_score = min(int(home_score), 100)
    away_score = min(int(away_score), 100)

    if home_score >= away_score:
        return "MS1", home_score
    return "MS2", away_score

def choose_best_market(home_stats, away_stats):
    btts_score = score_btts(home_stats, away_stats)
    over_score = score_over25(home_stats, away_stats)
    under_score = score_under25(home_stats, away_stats)
    ms_market, ms_score = score_ms(home_stats, away_stats)

    markets = [
        ("BTTS VAR", btts_score),
        ("2.5 ÜST", over_score),
        ("2.5 ALT", under_score),
        (ms_market, ms_score),
    ]

    markets.sort(key=lambda x: x[1], reverse=True)
    return markets[0], markets

def format_match_time(iso_time: str):
    try:
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        dt = dt + timedelta(hours=1)
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return iso_time

def analyze_matches():
    global team_cache, fixture_cache
    team_cache = {}
    fixture_cache = {}

    matches = get_all_relevant_matches()
    print("Analize giren maç sayısı:", len(matches))

    results = []

    for m in matches:
        home_team = m["teams"]["home"]["name"]
        away_team = m["teams"]["away"]["name"]
        home_id = m["teams"]["home"]["id"]
        away_id = m["teams"]["away"]["id"]
        league_name = m["league"]["name"]
        country = m["league"]["country"]
        match_time = format_match_time(m["fixture"]["date"])

        print("Analiz edilen maç:", home_team, "vs", away_team)

        home_last5 = get_last5(home_id)
        away_last5 = get_last5(away_id)

        print("Last5 sayıları:", home_team, len(home_last5), "|", away_team, len(away_last5))

        home_stats = analyze_team_stats(home_id, home_last5)
        away_stats = analyze_team_stats(away_id, away_last5)

        best_market, all_scores = choose_best_market(home_stats, away_stats)
        market_name, market_score = best_market

        print("Market sonuçları:", home_team, "vs", away_team, "|", all_scores)
        print("Seçilen market:", market_name, "| Puan:", market_score)

        results.append({
            "match": f"{home_team} vs {away_team}",
            "time": match_time,
            "league": f"{country} - {league_name}",
            "market": market_name,
            "score": market_score,
            "all_scores": all_scores
        })

        print("Listeye eklendi:", home_team, "vs", away_team, "|", market_name, "|", market_score)

    results.sort(key=lambda x: x["score"], reverse=True)
    print("Toplam sonuç sayısı:", len(results))

    if len(results) > 0:
        print("İlk 5 sonuç:", results[:5])

    return results[:5]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Bugün + gece maçları analiz ediliyor...")

    results = analyze_matches()

    if not results:
        await update.message.reply_text("❌ Uygun maç bulunamadı.")
        return

    message = "🔥 BUGÜN + GECE EN İYİ MAÇLAR\n\n"

    for i, item in enumerate(results, start=1):
        message += (
            f"{i}️⃣ {item['match']}\n"
            f"🕒 {item['time']}\n"
            f"🏆 {item['league']}\n"
            f"🎯 Market: {item['market']}\n"
            f"📊 Güven: {item['score']}/100\n\n"
        )

    await update.message.reply_text(message)

def main():
    if not API_KEY or not BOT_TOKEN:
        print("API_KEY veya BOT_TOKEN eksik.")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    print("Bot aktif. /start komutu bekleniyor...")
          
app.run_polling()
if __name__ == "__main__":
    main()
