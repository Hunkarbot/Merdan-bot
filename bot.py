import os
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# =========================
# AYARLAR
# =========================
API_KEY = os.getenv("API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY
}

TIMEZONE = "Europe/Berlin"

# Gollü ligler -> BTTS YES
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

# Kısır ligler -> UNDER 2.5
KISIR_LIGLER = [
    "Botola Pro",
    "Ligue 1",
    "Ligue 1 Algeria",
    "Ligue 1 Tunisia",
    "Premier League Tanzania",
    "Premier League Kenya",
    "Premier League Ethiopia",
    "Premier League Somalia",
    "Premier League Burundi"
]

# API dostu cache
team_last5_cache = {}

# =========================
# TARİH
# =========================
def get_dates():
    now_local = datetime.now(ZoneInfo(TIMEZONE))
    today = now_local.date()
    tomorrow = today + timedelta(days=1)
    return today.strftime("%Y-%m-%d"), tomorrow.strftime("%Y-%m-%d")

TODAY_STR, TOMORROW_STR = get_dates()

# =========================
# ORTAK API FONKSİYONU
# =========================
def safe_get(endpoint, params=None, sleep_sec=0.8):
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            params=params,
            timeout=20
        )
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

# =========================
# MAÇLARI ÇEK
# =========================
def get_matches_by_date(date_str):
    return safe_get("fixtures", {"date": date_str}, sleep_sec=1.0)

def get_all_matches():
    matches_today = get_matches_by_date(TODAY_STR)
    matches_tomorrow = get_matches_by_date(TOMORROW_STR)
    return matches_today + matches_tomorrow

# =========================
# TAKIM SON 5 MAÇ
# =========================
def get_team_last5(team_id):
    if team_id in team_last5_cache:
        return team_last5_cache[team_id]

    matches = safe_get(
        "fixtures",
        {"team": team_id, "last": 5},
        sleep_sec=1.0
    )

    team_last5_cache[team_id] = matches
    return matches

# =========================
# MAÇ TİPİ KONTROLLERİ
# =========================
def is_btts_match(match):
    try:
        h = match["goals"]["home"]
        a = match["goals"]["away"]
        return h is not None and a is not None and h > 0 and a > 0
    except Exception:
        return False

def is_under25_match(match):
    try:
        h = match["goals"]["home"]
        a = match["goals"]["away"]
        return h is not None and a is not None and (h + a) <= 2
    except Exception:
        return False

# =========================
# TAKIM FORM FİLTRELERİ
# =========================
def team_btts_5of5(last5_matches):
    if len(last5_matches) < 5:
        return False
    return sum(1 for m in last5_matches if is_btts_match(m)) == 5

def team_under25_4of5(last5_matches):
    if len(last5_matches) < 5:
        return False
    return sum(1 for m in last5_matches if is_under25_match(m)) >= 4

# =========================
# SKORLAMA
# =========================
def calc_btts_score(home_last5, away_last5):
    home_score = sum(1 for m in home_last5 if is_btts_match(m))
    away_score = sum(1 for m in away_last5 if is_btts_match(m))
    return home_score + away_score

def calc_under_score(home_last5, away_last5):
    home_score = sum(1 for m in home_last5 if is_under25_match(m))
    away_score = sum(1 for m in away_last5 if is_under25_match(m))
    return home_score + away_score

# =========================
# SAAT DÜZENLE
# =========================
def to_local_datetime_str(fixture_date_str):
    try:
        # API tarihi genelde ISO formatında gelir
        dt_utc = datetime.fromisoformat(fixture_date_str.replace("Z", "+00:00"))
        dt_local = dt_utc.astimezone(ZoneInfo(TIMEZONE))
        return dt_local.strftime("%Y-%m-%d"), dt_local.strftime("%H:%M")
    except Exception:
        # fallback
        return fixture_date_str[:10], fixture_date_str[11:16]

# =========================
# ANALİZ
# =========================
def analyze_matches():
    fixtures = get_all_matches()

    filtered_fixtures = []
    needed_team_ids = set()

    # 1) Önce sadece istediğimiz ligleri ayır
    for match in fixtures:
        try:
            league_name = match["league"]["name"]

            if league_name in GOLLU_LIGLER or league_name in KISIR_LIGLER:
                filtered_fixtures.append(match)
                needed_team_ids.add(match["teams"]["home"]["id"])
                needed_team_ids.add(match["teams"]["away"]["id"])
        except Exception:
            continue

    # 2) Sadece gerekli takımların son 5 maçını çek
    for team_id in needed_team_ids:
        get_team_last5(team_id)

    btts_candidates = []
    under_candidates = []

    # 3) Cache'den analiz et
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

            # Gollü lig -> BTTS YES
            if league_name in GOLLU_LIGLER:
                if team_btts_5of5(home_last5) and team_btts_5of5(away_last5):
                    score = calc_btts_score(home_last5, away_last5)
                    btts_candidates.append({
                        "score": score,
                        "text": f"{match_day} {match_time} - {home_team} vs {away_team} | {league_name} | BTTS YES"
                    })

            # Kısır lig -> UNDER 2.5
            if league_name in KISIR_LIGLER:
                if team_under25_4of5(home_last5) and team_under25_4of5(away_last5):
                    score = calc_under_score(home_last5, away_last5)
                    under_candidates.append({
                        "score": score,
                        "text": f"{match_day} {match_time} - {home_team} vs {away_team} | {league_name} | UNDER 2.5"
                    })

        except Exception as e:
            print(f"ANALİZ HATASI -> {e}")
            continue

    # En iyileri sırala
    btts_candidates.sort(key=lambda x: x["score"], reverse=True)
    under_candidates.sort(key=lambda x: x["score"], reverse=True)

    # Top seçimler
    top_btts = btts_candidates[:3]
    top_under = under_candidates[:2]

    return top_btts, top_under

# =========================
# TELEGRAM
# =========================
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

# =========================
# MESAJ OLUŞTUR
# =========================
def build_message(top_btts, top_under):
    msg = f"🔥 HÜNKAR BOT V3 ({TODAY_STR} + {TOMORROW_STR}) 🔥\n\n"

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

# =========================
# ANA ÇALIŞMA
# =========================
if __name__ == "__main__":
    if not API_KEY:
        print("API_KEY eksik")
    else:
        top_btts, top_under = analyze_matches()
        final_message = build_message(top_btts, top_under)
        print(final_message)
        send_telegram(final_message)

