import requests
import datetime
import os
import time
from zoneinfo import ZoneInfo

# ==============================
# AYARLAR
# ==============================
API_KEY = "958a48f672744800bed3aeea11efcc5f"
BOT_TOKEN = "BURAYA_BOT_TOKEN_YAZ"
CHAT_ID = "BURAYA_CHAT_ID_YAZ"

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY
}

TIMEZONE = "Europe/Berlin"
REQUEST_SLEEP = 0.5
MAX_MATCHES_TO_ANALYZE = 100
MAX_TELEGRAM_MATCHES = 10

# ==============================
# GOLLÜ LİGLER
# ==============================
GOLLU_LIGLER = [
    "Eredivisie",
    "Bundesliga",
    "2. Bundesliga",
    "Belgian Pro League",
    "Swiss Super League",
    "Austrian Bundesliga",
    "MLS",
    "A-League",
    "Championship",
    "League One",
    "League Two",
    "Scottish Premiership",
    "Superliga",
    "Eliteserien",
    "Allsvenskan",
    "Czech Liga",
    "Ekstraklasa",
    "Slovakia Super Liga",
    "Hungary NB I",
    "Süper Lig",
    "Liga Portugal",
    "Serie B",
    "Ligue 2",
    "Spain Segunda",
    "Croatia HNL",
    "Slovenia PrvaLiga",
    "Romania Liga I",
    "Bulgaria First League",
    "Brazil Serie A",
    "Brazil Serie B",
    "Colombia Primera A",
    "Chile Primera Division",
    "Uruguay Primera Division",
    "Paraguay Division Profesional",
    "Japan J1 League",
    "Japan J2 League",
    "K League 1",
    "China Super League",
    "India Super League",
    "South Africa Premier Division"
]

# ==============================
# GLOBAL DEĞİŞKENLER
# ==============================
TEAM_CACHE = {}
ERRORS = []


# ==============================
# YARDIMCI
# ==============================
def now_berlin():
    return datetime.datetime.now(ZoneInfo(TIMEZONE))


def add_error(msg):
    print("HATA:", msg)
    ERRORS.append(msg)


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
        print("TELEGRAM CEVAP:", res.text[:300])
    except Exception as e:
        print("TELEGRAM GONDERME HATA:", str(e))


def api_get(url):
    try:
        time.sleep(REQUEST_SLEEP)
        res = requests.get(url, headers=HEADERS, timeout=30)

        print("GET URL:", url)
        print("STATUS:", res.status_code)
        print("RESP:", res.text[:300])

        if res.status_code != 200:
            add_error(f"API hata kodu: {res.status_code}")
            return None

        data = res.json()

        if data.get("errors"):
            add_error(f"API errors: {data.get('errors')}")
            return None

        return data

    except Exception as e:
        add_error(f"Baglanti hatasi: {str(e)}")
        return None


def lig_uygun_mu(league_name):
    league_name = (league_name or "").lower()

    for lig in GOLLU_LIGLER:
        if lig.lower() in league_name:
            return True

    return False


def format_saat(iso_date):
    try:
        dt = datetime.datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        dt_local = dt.astimezone(ZoneInfo(TIMEZONE))
        return dt_local.strftime("%d-%m %H:%M")
    except Exception:
        return iso_date


# ==============================
# MAÇLARI ÇEK
# ==============================
def get_matches():
    data = api_get(f"{BASE_URL}/fixtures?next=100")

    if not data:
        return []

    matches = data.get("response", [])
    return matches


# ==============================
# SON 5 MAÇ (CACHE)
# ==============================
def get_last5(team_id):
    if team_id in TEAM_CACHE:
        return TEAM_CACHE[team_id]

    data = api_get(f"{BASE_URL}/fixtures?team={team_id}&last=5")

    if not data:
        TEAM_CACHE[team_id] = []
        return []

    response = data.get("response", [])
    TEAM_CACHE[team_id] = response
    return response


# ==============================
# TAKIM GOL ATAR MI / YER Mİ
# ==============================
def get_team_stats(team_id, matches):
    scored = 0
    conceded = 0

    for m in matches:
        teams = m.get("teams", {})
        goals = m.get("goals", {})

        home_id = teams.get("home", {}).get("id")
        away_id = teams.get("away", {}).get("id")

        home_goals = goals.get("home")
        away_goals = goals.get("away")

        if home_goals is None or away_goals is None:
            continue

        if team_id == home_id:
            if home_goals > 0:
                scored += 1
            if away_goals > 0:
                conceded += 1

        elif team_id == away_id:
            if away_goals > 0:
                scored += 1
            if home_goals > 0:
                conceded += 1

    return scored, conceded


# ==============================
# ANALİZ
# ==============================
def analyze_btts(matches):
    candidates = []
    checked = 0

    for match in matches:
        if checked >= MAX_MATCHES_TO_ANALYZE:
            break

        try:
            league_name = match.get("league", {}).get("name", "")
            league_country = match.get("league", {}).get("country", "")
            league_full = f"{league_country} - {league_name}"

            if not lig_uygun_mu(league_name) and not lig_uygun_mu(league_full):
                continue

            home = match.get("teams", {}).get("home", {})
            away = match.get("teams", {}).get("away", {})

            home_id = home.get("id")
            away_id = away.get("id")
            home_name = home.get("name", "Home")
            away_name = away.get("name", "Away")

            if not home_id or not away_id:
                continue

            checked += 1

            home_last5 = get_last5(home_id)
            away_last5 = get_last5(away_id)

            if len(home_last5) < 5 or len(away_last5) < 5:
                continue

            home_scored, home_conceded = get_team_stats(home_id, home_last5)
            away_scored, away_conceded = get_team_stats(away_id, away_last5)

            home_ok = home_scored >= 3 and home_conceded >= 3
            away_ok = away_scored >= 3 and away_conceded >= 3

            if not (home_ok and away_ok):
                continue

            avg = (home_scored + home_conceded + away_scored + away_conceded) / 4

            if avg >= 4:
                guc = "YÜKSEK"
            elif avg >= 3.5:
                guc = "ORTA-YÜKSEK"
            else:
                guc = "ORTA"

            fixture_date = match.get("fixture", {}).get("date", "")
            saat = format_saat(fixture_date)

            candidates.append({
                "match": f"{home_name} - {away_name}",
                "time": saat,
                "league": league_full,
                "home_scored": home_scored,
                "home_conceded": home_conceded,
                "away_scored": away_scored,
                "away_conceded": away_conceded,
                "guc": guc
            })

        except Exception as e:
            add_error(f"Analiz hatasi: {str(e)}")
            continue

    return candidates, checked


# ==============================
# RAPOR
# ==============================
def build_report(matches, checked, picks):
    now_str = now_berlin().strftime("%d-%m %H:%M")

    lines = []
    lines.append("🔥 HÜNKAR BTTS 🔥")
    lines.append(f"🕒 {now_str}")
    lines.append("📅 Gündüz + Gece")
    lines.append("")
    lines.append(f"📊 Toplam: {len(matches)} | İncelenen: {checked} | Aday: {len(picks)}")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━")
    lines.append("🔥 BTTS ADAYLARI")
    lines.append("━━━━━━━━━━━━━━━")
    lines.append("")

    if not picks:
        lines.append("❌ Uygun BTTS bulunamadı")
    else:
        for i, p in enumerate(picks[:MAX_TELEGRAM_MATCHES], 1):
            lines.append(f"{i}. {p['match']}")
            lines.append(f"⏰ {p['time']} | {p['league']}")
            lines.append(f"A: {p['home_scored']}/5 atmış | {p['home_conceded']}/5 yemiş")
            lines.append(f"B: {p['away_scored']}/5 atmış | {p['away_conceded']}/5 yemiş")
            lines.append(f"💪 {p['guc']}")
            lines.append("")

    if ERRORS:
        lines.append("❌ Hata:")
        for err in ERRORS[:3]:
            lines.append(f"- {err}")

    return "\n".join(lines)


# ==============================
# MAIN
# ==============================
def main():
    print("BOT BASLADI")

    if not API_KEY or API_KEY == "BURAYA_API_KEY_YAZ":
        telegram_gonder("❌ API KEY YOK")
        return

    if not BOT_TOKEN or BOT_TOKEN == "BURAYA_BOT_TOKEN_YAZ":
        print("BOT TOKEN eksik")
        return

    if not CHAT_ID or CHAT_ID == "BURAYA_CHAT_ID_YAZ":
        print("CHAT_ID eksik")
        return

    matches = get_matches()
    print("TOPLAM MAC:", len(matches))

    picks, checked = analyze_btts(matches)

    report = build_report(matches, checked, picks)

    print(report)
    telegram_gonder(report)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("KRITIK HATA:", str(e))
        try:
            telegram_gonder(f"❌ KRITIK HATA\n{str(e)}")
        except Exception:
            pass
