import requests
import datetime
import os
import time
from zoneinfo import ZoneInfo

# =========================================
# AYARLAR
# =========================================
API_KEY = os.getenv("API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

TIMEZONE = "Europe/Berlin"

# API dostu küçük bekleme
REQUEST_SLEEP = 0.4

# Son 5 maçta BTTS için minimum maç sayısı
MIN_LAST_MATCHES = 5

# Çok fazla maç gelirse aşırı yük olmasın
MAX_MATCHES_TO_ANALYZE = 250

# Gollü ligler
GOLLU_LIGLER = [
    "Eredivisie",
    "Bundesliga",
    "2. Bundesliga",
    "Belgian Pro League",
    "Pro League",
    "Swiss Super League",
    "Austrian Bundesliga",
    "MLS",
    "A-League",
    "Championship",
    "League One",
    "Eliteserien",
    "Allsvenskan",
    "Superliga",
    "Super League",
    "Süper Lig",
    "Jupiler Pro League",
    "Denmark Superliga",
    "Norway Eliteserien",
    "Sweden Allsvenskan"
]

# Kısır / riskli ligler burada direkt elenir
DISALANAN_LIGLER = [
    "Egypt",
    "Algeria",
    "Morocco",
    "Tunisia",
    "Tanzania",
    "Ethiopia",
    "Kenya",
    "Primera Nacional"
]

# Cache
TEAM_LAST5_CACHE = {}
API_ERROR_LOGS = []


# =========================================
# YARDIMCI
# =========================================
def berlin_now():
    return datetime.datetime.now(ZoneInfo(TIMEZONE))


def log_error(msg):
    print("HATA:", msg)
    API_ERROR_LOGS.append(msg)


def telegram_gonder(mesaj):
    if not BOT_TOKEN or not CHAT_ID:
        print("TELEGRAM HATA: BOT_TOKEN veya CHAT_ID eksik")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": mesaj
    }

    try:
        res = requests.post(url, data=data, timeout=30)
        print("TELEGRAM STATUS:", res.status_code)
        print("TELEGRAM CEVAP:", res.text[:500])
    except Exception as e:
        print("TELEGRAM GONDERME HATA:", str(e))


def api_get(url):
    try:
        time.sleep(REQUEST_SLEEP)
        res = requests.get(url, headers=HEADERS, timeout=30)
        print("GET:", url)
        print("STATUS:", res.status_code)
        print("RESP:", res.text[:300])

        if res.status_code != 200:
            log_error(f"API hata kodu {res.status_code} | URL: {url}")
            return None

        data = res.json()

        if data.get("errors"):
            log_error(f"API errors: {data.get('errors')} | URL: {url}")
            return None

        return data

    except Exception as e:
        log_error(f"Baglanti hatasi: {str(e)} | URL: {url}")
        return None


def lig_gollu_mu(league_name):
    league_lower = (league_name or "").lower()

    for risk in DISALANAN_LIGLER:
        if risk.lower() in league_lower:
            return False

    for good in GOLLU_LIGLER:
        if good.lower() in league_lower:
            return True

    return False


def format_fixture_time(iso_date):
    try:
        dt = datetime.datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        local_dt = dt.astimezone(ZoneInfo(TIMEZONE))
        return local_dt.strftime("%d-%m %H:%M")
    except Exception:
        return iso_date


# =========================================
# MAÇLARI ÇEK
# =========================================
def get_matches_for_date(date_str):
    url = f"{BASE_URL}/fixtures?date={date_str}"
    data = api_get(url)

    if not data:
        return []

    return data.get("response", [])


def get_today_and_tomorrow_matches():
    now = berlin_now()
    today = now.date()
    tomorrow = today + datetime.timedelta(days=1)

    date1 = today.strftime("%Y-%m-%d")
    date2 = tomorrow.strftime("%Y-%m-%d")

    matches_1 = get_matches_for_date(date1)
    matches_2 = get_matches_for_date(date2)

    all_matches = matches_1 + matches_2

    # Aynı fixture iki kere gelirse temizle
    seen_ids = set()
    unique_matches = []

    for m in all_matches:
        fixture_id = m.get("fixture", {}).get("id")
        if fixture_id and fixture_id not in seen_ids:
            seen_ids.add(fixture_id)
            unique_matches.append(m)

    return unique_matches, date1, date2


# =========================================
# TAKIM SON 5 MAÇ
# =========================================
def get_last5(team_id):
    if team_id in TEAM_LAST5_CACHE:
        return TEAM_LAST5_CACHE[team_id]

    url = f"{BASE_URL}/fixtures?team={team_id}&last=5"
    data = api_get(url)

    if not data:
        TEAM_LAST5_CACHE[team_id] = []
        return []

    response = data.get("response", [])
    TEAM_LAST5_CACHE[team_id] = response
    return response


def team_scored_and_conceded_every_match(last5_matches):
    if len(last5_matches) < MIN_LAST_MATCHES:
        return False

    for m in last5_matches:
        teams = m.get("teams", {})
        goals = m.get("goals", {})

        home_id = teams.get("home", {}).get("id")
        away_id = teams.get("away", {}).get("id")
        home_goals = goals.get("home")
        away_goals = goals.get("away")

        if home_goals is None or away_goals is None:
            return False

        # Bu fonksiyonda takım kim onu bilmiyoruz diye dışarıda belirleyeceğiz
        # O yüzden burada kullanılmıyor
    return True


def team_btts_5of5_for_specific_team(team_id, last5_matches):
    if len(last5_matches) < MIN_LAST_MATCHES:
        return False

    for m in last5_matches:
        teams = m.get("teams", {})
        goals = m.get("goals", {})

        home_id = teams.get("home", {}).get("id")
        away_id = teams.get("away", {}).get("id")
        home_goals = goals.get("home")
        away_goals = goals.get("away")

        if home_goals is None or away_goals is None:
            return False

        if team_id == home_id:
            scored = home_goals
            conceded = away_goals
        elif team_id == away_id:
            scored = away_goals
            conceded = home_goals
        else:
            return False

        if scored <= 0 or conceded <= 0:
            return False

    return True


# =========================================
# BTTS PUANLAMA
# =========================================
def calculate_btts_score(home_last5, away_last5):
    score = 0

    # Ana ultra kural: iki takım da 5/5
    score += 50

    # toplam gol desteği
    def avg_total_goals(last5):
        totals = []
        for m in last5:
            gh = m.get("goals", {}).get("home")
            ga = m.get("goals", {}).get("away")
            if gh is not None and ga is not None:
                totals.append(gh + ga)
        if not totals:
            return 0
        return sum
