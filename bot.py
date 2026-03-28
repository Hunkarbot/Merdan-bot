import requests
import os
import time
import datetime
from zoneinfo import ZoneInfo

# ==============================
# AYARLAR
# ==============================
API_KEY = os.getenv("FOOTBALL_API_KEY") or "958a48f672744800bed3aeea11efcc5f"
BOT_TOKEN = os.getenv("BOT_TOKEN") or "BURAYA_BOT_TOKEN"
CHAT_ID = os.getenv("CHAT_ID") or "BURAYA_CHAT_ID"

BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

TZ = ZoneInfo("Europe/Berlin")

# ==============================
# GOLLÜ LİGLER (ANA FİLTRE)
# ==============================
GOLLU_LIGLER = [
    "Eredivisie","Bundesliga","2. Bundesliga","Belgium","Pro League",
    "Jupiler","Switzerland","Swiss","Austria","Austrian",
    "MLS","A-League","Allsvenskan","Eliteserien",
    "Championship","League One","Netherlands","Germany"
]

def is_gollu_lig(league, country):
    text = f"{league} {country}".lower()
    return any(l.lower() in text for l in GOLLU_LIGLER)

# ==============================
# TELEGRAM
# ==============================
def send_telegram(msg):
    if "BURAYA" in BOT_TOKEN:
        print(msg)
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=20)
    except:
        pass

# ==============================
# API
# ==============================
def api_get(endpoint, params=None):
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params, timeout=30)
        data = r.json()
        time.sleep(1.0)  # API dostu
        return data.get("response", [])
    except:
        return []

# ==============================
# TARİHLER
# ==============================
def get_dates():
    now = datetime.datetime.now(TZ)
    today = now.date()
    tomorrow = today + datetime.timedelta(days=1)
    return [today.strftime("%Y-%m-%d"), tomorrow.strftime("%Y-%m-%d")]

# ==============================
# CACHE
# ==============================
team_cache = {}

def get_last5(team_id):
    if team_id in team_cache:
        return team_cache[team_id]

    data = api_get("/fixtures", {"team": team_id, "last": 5})
    team_cache[team_id] = data
    return data

# ==============================
# TAKIM ANALİZ
# ==============================
def analyze_team(team_id):
    matches = get_last5(team_id)

    scored = conceded = btts = played = 0

    for m in matches:
        hg = m["goals"]["home"]
        ag = m["goals"]["away"]

        if hg is None or ag is None:
            continue

        played += 1

        if m["teams"]["home"]["id"] == team_id:
            gf, ga = hg, ag
        else:
            gf, ga = ag, hg

        if gf > 0: scored += 1
        if ga > 0: conceded += 1
        if gf > 0 and ga > 0: btts += 1

    return {
        "played": played,
        "scored": scored,
        "conceded": conceded,
        "btts": btts
    }

# ==============================
# BTTS KARAR
# ==============================
def is_btts_candidate(home, away):
    # ana mantık
    if home["scored"] < 4: return False
    if away["scored"] < 4: return False
    if home["conceded"] < 3: return False
    if away["conceded"] < 3: return False

    return True

# ==============================
# PUAN
# ==============================
def score(home, away):
    s = 0

    s += home["scored"] * 5
    s += away["scored"] * 5
    s += home["conceded"] * 4
    s += away["conceded"] * 4
    s += home["btts"] * 2
    s += away["btts"] * 2

    return min(s, 100)

# ==============================
# ANA
# ==============================
def main():
    dates = get_dates()
    matches = []

    for d in dates:
        matches = api_get("/fixtures", {"next": 50})

    print("Toplam maç:", len(matches))

    results = []

    for m in matches:
        league = m["league"]["name"]
        country = m["league"]["country"]

        # 🔥 EN ÖNEMLİ FİLTRE (API KURTARIR)
        if not is_gollu_lig(league, country):
            continue

        home_id = m["teams"]["home"]["id"]
        away_id = m["teams"]["away"]["id"]

        home_stats = analyze_team(home_id)
        away_stats = analyze_team(away_id)

        if home_stats["played"] < 5 or away_stats["played"] < 5:
            continue

        if not is_btts_candidate(home_stats, away_stats):
            continue

        puan = score(home_stats, away_stats)

        if puan < 70:
            continue

        dt = datetime.datetime.fromisoformat(m["fixture"]["date"].replace("Z","+00:00")).astimezone(TZ)

        results.append({
            "match": f"{m['teams']['home']['name']} vs {m['teams']['away']['name']}",
            "league": f"{country} - {league}",
            "time": dt.strftime("%d.%m %H:%M"),
            "score": puan
        })

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    print("BTTS aday:", len(results))

    if not results:
        send_telegram("Bugün güçlü BTTS adayı yok.")
        return

    msg = "🔥 BTTS ADAYLARI\n\n"

    for i, r in enumerate(results[:10], 1):
        msg += f"{i}) {r['match']}\n{r['league']}\n🕒 {r['time']}\n📈 {r['score']}/100\n\n"

    send_telegram(msg)

if __name__ == "__main__":
    main()
