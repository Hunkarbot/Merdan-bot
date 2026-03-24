import os
import requests
import datetime
import time
import schedule

API_KEY = "9d815aaf3a5947e681eda9a895a281b5"
BOT_TOKEN = "8747036915:AAES-UKrjW3xU891kX9s36sNn5gdaNlgaz8"
CHAT_ID = os.getenv("CHAT_ID")

BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

# Sadece gollü ligler
GOLLU_LIGLER = [
    "Eredivisie",
    "Bundesliga",
    "Belgium",
    "MLS",
    "A-League",
    "Austria",
    "Switzerland",
    "Denmark",
    "Czech",
    "Norway",
    "Sweden"
]

# Takım verisini tekrar tekrar çekmemek için hafıza
team_cache = {}

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text
    }
    try:
        requests.post(url, data=data, timeout=20)
    except Exception as e:
        print("Telegram gönderme hatası:", e)

def get_today():
    return datetime.datetime.now().strftime("%Y-%m-%d")

def get_today_matches():
    url = f"{BASE_URL}/fixtures"
    params = {"date": get_today()}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        data = r.json()
        return data.get("response", [])
    except Exception as e:
        print("Bugünkü maçlar alınamadı:", e)
        return []

def get_last5(team_id):
    if team_id in team_cache:
        return team_cache[team_id]

    url = f"{BASE_URL}/fixtures"
    params = {
        "team": team_id,
        "last": 5
    }

    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        data = r.json()
        matches = data.get("response", [])
        team_cache[team_id] = matches
        time.sleep(1.2)  # API koruma
        return matches
    except Exception as e:
        print(f"Takım {team_id} son 5 maç hatası:", e)
        return []

def team_btts_5of5(team_id, matches):
    if len(matches) < 5:
        return False

    count = 0

    for m in matches:
        home_id = m["teams"]["home"]["id"]
        away_id = m["teams"]["away"]["id"]
        home_goals = m["goals"]["home"]
        away_goals = m["goals"]["away"]

        if home_goals is None or away_goals is None:
            return False

        # Takım hem gol atmış hem gol yemiş olmalı
        if team_id == home_id:
            scored = home_goals
            conceded = away_goals
        elif team_id == away_id:
            scored = away_goals
            conceded = home_goals
        else:
            return False

        if scored > 0 and conceded > 0:
            count += 1

    return count == 5

def is_gollu_lig(league_name):
    league_lower = league_name.lower()
    for lig in GOLLU_LIGLER:
        if lig.lower() in league_lower:
            return True
    return False

def analyze_btts():
    global team_cache
    team_cache = {}

    send_telegram("🔥 Günün BTTS taraması başladı...")

    matches = get_today_matches()
    results = []

    for m in matches:
        league_name = m["league"]["name"]
        country = m["league"]["country"]
        league_text = f"{country} - {league_name}"

        if not is_gollu_lig(league_name) and not is_gollu_lig(country):
            continue

        home_team = m["teams"]["home"]["name"]
        away_team = m["teams"]["away"]["name"]
        home_id = m["teams"]["home"]["id"]
        away_id = m["teams"]["away"]["id"]
        match_time = m["fixture"]["date"]

        home_last5 = get_last5(home_id)
        away_last5 = get_last5(away_id)

        home_ok = team_btts_5of5(home_id, home_last5)
        away_ok = team_btts_5of5(away_id, away_last5)

        if home_ok and away_ok:
            dt = datetime.datetime.fromisoformat(match_time.replace("Z", "+00:00"))
            saat = dt.strftime("%d.%m.%Y %H:%M")

            results.append(
                f"✅ {home_team} - {away_team}\n"
                f"🕒 {saat}\n"
                f"🏆 {league_text}\n"
                f"📌 Market: BTTS"
            )

        if len(results) >= 3:
            break

    if results:
        msg = "🔥 BUGÜNÜN EN SAĞLAM BTTS MAÇLARI\n\n" + "\n\n".join(results)
    else:
        msg = "❌ Bugün 5/5 kuralına uyan sağlam BTTS maçı bulunamadı."

    send_telegram(msg)

# Her gün sabah 09:00
schedule.every().day.at("09:00").do(analyze_btts)

print("Bot çalışıyor... Sadece BTTS sistemi aktif.")

while True:
    schedule.run_pending()
    time.sleep(30)
