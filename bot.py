import os
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

API_KEY = os.getenv("API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY
}

TIMEZONE = "Europe/Berlin"

# Gollü ligler -> BTTS
GOLLU_LIGLER = [
    "Eredivisie",
    "Bundesliga",
    "2. Bundesliga",
    "Pro League",
    "Superliga",
    "Allsvenskan",
    "Eliteserien",
    "MLS",
    "A-League",
    "Championship",
    "Super League",
    "1. Liga"
]

# Kısır ligler -> Under 2.5
KISIR_LIGLER = [
    "Botola Pro",
    "Ligue 1 Algeria",
    "Ligue 1 Tunisia",
    "Premier League Tanzania",
    "Premier League Kenya",
    "Premier League Ethiopia",
    "Premier League Somalia",
    "Premier League Burundi"
]

team_last5_cache = {}

def get_dates():
    now_local = datetime.now(ZoneInfo(TIMEZONE))
    today = now_local.date()
    tomorrow = today + timedelta(days=1)
    return today.strftime("%Y-%m-%d"), tomorrow.strftime("%Y-%m-%d")

TODAY_STR, TOMORROW_STR = get_dates()

def safe_get(endpoint, params=None, sleep_sec=0.8):
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=20)
        time.sleep(sleep_sec)
        response.raise_for_status()
        data = response.json()

        if data.get("errors"):
            print(f"API ERROR -> {data['errors']}")
            return []

        return data.get("response", [])
    except requests.exceptions.RequestException as e:
        print(f"REQUEST HATASI -> {endpoint} | {params} | {e}")
        return []
    except Exception as e:
        print(f"GENEL HATA -> {endpoint} | {params} | {e}")
        return []

def get_matches_by_date(date_str):
    return safe_get("fixtures", {"date": date_str}, sleep_sec=1.0)

def get_all_matches():
    matches_today = get_matches_by_date(TODAY_STR)
    matches_tomorrow = get_matches_by_date(TOMORROW_STR)
    return matches_today + matches_tomorrow

def get_team_last5(team_id):
    if team_id in team_last5_cache:
        return team_last5_cache[team_id]

    matches = safe_get("fixtures", {"team": team_id, "last": 5}, sleep_sec=1.0)
    team_last5_cache[team_id] = matches
    return matches

def to_local_datetime_str(fixture_date_str):
    try:
        dt_utc = datetime.fromisoformat(fixture_date_str.replace("Z", "+00:00"))
        dt_local = dt_utc.astimezone(ZoneInfo(TIMEZONE))
        return dt_local.strftime("%Y-%m-%d"), dt_local.strftime("%H:%M")
    except Exception:
        return fixture_date_str[:10], fixture_date_str[11:16]

# -------------------------
# TAKIM SAYAÇLARI
# -------------------------
def count_scored(matches, team_id):
    count = 0
    for m in matches:
        try:
            if m["teams"]["home"]["id"] == team_id:
                goals = m["goals"]["home"]
            elif m["teams"]["away"]["id"] == team_id:
                goals = m["goals"]["away"]
            else:
                continue

            if goals is not None and goals > 0:
                count += 1
        except Exception:
            continue
    return count

def count_conceded(matches, team_id):
    count = 0
    for m in matches:
        try:
            if m["teams"]["home"]["id"] == team_id:
                opp_goals = m["goals"]["away"]
            elif m["teams"]["away"]["id"] == team_id:
                opp_goals = m["goals"]["home"]
            else:
                continue

            if opp_goals is not None and opp_goals > 0:
                count += 1
        except Exception:
            continue
    return count

def count_under25(matches):
    count = 0
    for m in matches:
        try:
            h = m["goals"]["home"]
            a = m["goals"]["away"]
            if h is not None and a is not None and (h + a) <= 2:
                count += 1
        except Exception:
            continue
    return count

# -------------------------
# BTTS MANTIĞI
# Soru:
# A, B'ye gol atar mı ve gol yer mi?
# B, A'ya gol atar mı ve gol yer mi?
# -------------------------
def is_btts_candidate(home_last5, away_last5, home_id, away_id):
    home_scored = count_scored(home_last5, home_id)
    home_conceded = count_conceded(home_last5, home_id)
    away_scored = count_scored(away_last5, away_id)
    away_conceded = count_conceded(away_last5, away_id)

    # A -> B'ye gol atar mı?
    home_can_score_vs_away = (home_scored + away_conceded) >= 8

    # B -> A'ya gol atar mı?
    away_can_score_vs_home = (away_scored + home_conceded) >= 8

    # A gol yer mi?
    home_will_concede = home_conceded >= 3

    # B gol yer mi?
    away_will_concede = away_conceded >= 3

    return (
        home_can_score_vs_away and
        away_can_score_vs_home and
        home_will_concede and
        away_will_concede
    )

def calc_btts_score(home_last5, away_last5, home_id, away_id):
    home_scored = count_scored(home_last5, home_id)
    home_conceded = count_conceded(home_last5, home_id)
    away_scored = count_scored(away_last5, away_id)
    away_conceded = count_conceded(away_last5, away_id)

    home_side = home_scored + away_conceded
    away_side = away_scored + home_conceded

    return home_side + away_side

# -------------------------
# UNDER 2.5 MANTIĞI
# Soru:
# A gol atamıyor mu ve B gol yemiyor mu?
# B gol atamıyor mu ve A gol yemiyor mu?
# -------------------------
def is_under25_candidate(home_last5, away_last5, home_id, away_id):
    home_scored = count_scored(home_last5, home_id)
    home_conceded = count_conceded(home_last5, home_id)
    away_scored = count_scored(away_last5, away_id)
    away_conceded = count_conceded(away_last5, away_id)

    home_under = count_under25(home_last5)
    away_under = count_under25(away_last5)

    # A gol atamıyor + B gol yemiyor
    home_goal_hard = home_scored <= 2 and away_conceded <= 2

    # B gol atamıyor + A gol yemiyor
    away_goal_hard = away_scored <= 2 and home_conceded <= 2

    return (
        home_goal_hard and
        away_goal_hard and
        home_under >= 4 and
        away_under >= 4
    )

def calc_under_score(home_last5, away_last5, home_id, away_id):
    home_scored = count_scored(home_last5, home_id)
    home_conceded = count_conceded(home_last5, home_id)
    away_scored = count_scored(away_last5, away_id)
    away_conceded = count_conceded(away_last5, away_id)

    home_under = count_under25(home_last5)
    away_under = count_under25(away_last5)

    # düşük skor daha iyi olduğu için ters mantıkla puanlıyoruz
    score = 0
    score += (5 - home_scored)
    score += (5 - away_scored)
    score += (5 - home_conceded)
    score += (5 - away_conceded)
    score += home_under
    score += away_under

    return score

# -------------------------
# ANALİZ
# -------------------------
def analyze_matches():
    fixtures = get_all_matches()

    filtered_fixtures = []
    needed_team_ids = set()

    # önce sadece istediğimiz ligleri ayır
    for match in fixtures:
        try:
            league_name = match["league"]["name"]

            if league_name in GOLLU_LIGLER or league_name in KISIR_LIGLER:
                filtered_fixtures.append(match)
                needed_team_ids.add(match["teams"]["home"]["id"])
                needed_team_ids.add(match["teams"]["away"]["id"])
        except Exception:
            continue

    # sadece gerekli takımların son 5 maçını çek
    for team_id in needed_team_ids:
        get_team_last5(team_id)

    btts_candidates = []
    under_candidates = []

    # cache içinden analiz et
    for match in filtered_fixtures:
        try:
            league_name = match["league"]["name"]
            home_team = match["teams"]["home"]["name"]
            away_team = match["teams"]["away"]["name"]
            home_id = match["teams"]["home"]["id"]
            away_id = match["teams"]["away"]["id"]

            fixture_date = match["fixture"]["date"]
            match_day, match_time = to_local_datetime_str(fixture_date)

            home_last5 = team_last5_cache.get(home_id, [])
            away_last5 = team_last5_cache.get(away_id, [])

            if len(home_last5) < 5 or len(away_last5) < 5:
                continue

            # BTTS
            if league_name in GOLLU_LIGLER:
                if is_btts_candidate(home_last5, away_last5, home_id, away_id):
                    score = calc_btts_score(home_last5, away_last5, home_id, away_id)
                    btts_candidates.append({
                        "score": score,
                        "text": f"{match_day} {match_time} - {home_team} vs {away_team} | {league_name} | BTTS YES"
                    })

            # UNDER
            if league_name in KISIR_LIGLER:
                if is_under25_candidate(home_last5, away_last5, home_id, away_id):
                    score = calc_under_score(home_last5, away_last5, home_id, away_id)
                    under_candidates.append({
                        "score": score,
                        "text": f"{match_day} {match_time} - {home_team} vs {away_team} | {league_name} | UNDER 2.5"
                    })

        except Exception as e:
            print(f"ANALİZ HATASI -> {e}")
            continue

    btts_candidates.sort(key=lambda x: x["score"], reverse=True)
    under_candidates.sort(key=lambda x: x["score"], reverse=True)

    top_btts = btts_candidates[:3]
    top_under = under_candidates[:2]

    return top_btts, top_under

# -------------------------
# TELEGRAM
# -------------------------
def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("BOT_TOKEN veya CHAT_ID eksik")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        response = requests.post(url, data=payload, timeout=20)
        response.raise_for_status()
        print("Telegram mesajı gönderildi.")
    except Exception as e:
        print(f"TELEGRAM HATASI -> {e}")

def build_message(top_btts, top_under):
    msg = f"🔥 HÜNKAR BOT ({TODAY_STR} + {TOMORROW_STR}) 🔥\n\n"

    if top_btts:
        msg += "🟩 EN İYİ BTTS YES:\n"
        for i, item in enumerate(top_btts, 1):
            msg += f"{i}) {item['text']}\n"
        msg += "\n"
    else:
        msg += "🟩 BTTS YES uygun maç yok\n\n"

    if top_under:
        msg += "🟥 EN İYİ UNDER 2.5:\n"
        for i, item in enumerate(top_under, 1):
            msg += f"{i}) {item['text']}\n"
    else:
        msg += "🟥 UNDER 2.5 uygun maç yok"

    return msg

if __name__ == "__main__":
    if not API_KEY:
        print("API_KEY eksik")
    else:
        top_btts, top_under = analyze_matches()
        final_message = build_message(top_btts, top_under)
        print(final_message)
        send_telegram(final_message)
