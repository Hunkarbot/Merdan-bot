import requests
import datetime
import os
import time
from zoneinfo import ZoneInfo

# ==============================
# AYARLAR
# ==============================
API_KEY = os.getenv("API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

TIMEZONE = "Europe/Berlin"
REQUEST_SLEEP = 0.5
MAX_MATCHES_TO_ANALYZE = 100
MAX_TELEGRAM_MATCHES = 10

# 🔥 FULL GOLLÜ LİGLER
GOLLU_LIGLER = [
    "Eredivisie","Bundesliga","2. Bundesliga","Belgian Pro League",
    "Swiss Super League","Austrian Bundesliga","MLS","A-League",
    "Championship","League One","League Two","Scottish Premiership",
    "Superliga","Eliteserien","Allsvenskan","Czech Liga",
    "Ekstraklasa","Slovakia Super Liga","Hungary NB I",
    "Süper Lig","Liga Portugal","Serie B","Ligue 2",
    "Spain Segunda","Croatia HNL","Slovenia PrvaLiga",
    "Romania Liga I","Bulgaria First League",
    "Brazil Serie A","Brazil Serie B","Colombia Primera A",
    "Chile Primera Division","Uruguay Primera Division",
    "Paraguay Division Profesional",
    "Japan J1 League","Japan J2 League","K League 1",
    "China Super League","India Super League",
    "South Africa Premier Division"
]

TEAM_CACHE = {}
ERRORS = []

# ==============================
# YARDIMCI
# ==============================
def now():
    return datetime.datetime.now(ZoneInfo(TIMEZONE))

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

def api(url):
    try:
        time.sleep(REQUEST_SLEEP)
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            ERRORS.append(f"API {r.status_code}")
            return None
        return r.json()
    except Exception as e:
        ERRORS.append(str(e))
        return None

# ==============================
# MAÇLAR
# ==============================
def get_matches():
    t = now().date()
    dates = [
        t.strftime("%Y-%m-%d"),
        (t + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    ]

    all_matches = []

    for d in dates:
        data = api(f"{BASE_URL}/fixtures?date={d}")
        if data:
            all_matches += data.get("response", [])

    return all_matches

# ==============================
# CACHE LAST5
# ==============================
def last5(team_id):
    if team_id in TEAM_CACHE:
        return TEAM_CACHE[team_id]

    data = api(f"{BASE_URL}/fixtures?team={team_id}&last=5")

    if not data:
        TEAM_CACHE[team_id] = []
        return []

    TEAM_CACHE[team_id] = data.get("response", [])
    return TEAM_CACHE[team_id]

# ==============================
# GOL ANALİZ
# ==============================
def stats(team_id, matches):
    scored = 0
    conceded = 0

    for m in matches:
        h = m["teams"]["home"]["id"]
        a = m["teams"]["away"]["id"]
        gh = m["goals"]["home"]
        ga = m["goals"]["away"]

        if gh is None or ga is None:
            continue

        if team_id == h:
            if gh > 0: scored += 1
            if ga > 0: conceded += 1
        elif team_id == a:
            if ga > 0: scored += 1
            if gh > 0: conceded += 1

    return scored, conceded

# ==============================
# ANALİZ
# ==============================
def analyze(matches):
    res = []
    checked = 0

    for m in matches:
        if checked >= MAX_MATCHES_TO_ANALYZE:
            break

        try:
            league = m["league"]["name"]

            if not any(x.lower() in league.lower() for x in GOLLU_LIGLER):
                continue

            home = m["teams"]["home"]
            away = m["teams"]["away"]

            h_id, a_id = home["id"], away["id"]

            h5 = last5(h_id)
            a5 = last5(a_id)

            if len(h5) < 5 or len(a5) < 5:
                continue

            hs, hc = stats(h_id, h5)
            as_, ac = stats(a_id, a5)

            # 🔥 ANA SORU
            if hs >= 3 and hc >= 3 and as_ >= 3 and ac >= 3:

                dt = datetime.datetime.fromisoformat(
                    m["fixture"]["date"].replace("Z","+00:00")
                ).astimezone(ZoneInfo(TIMEZONE))

                res.append({
                    "match": f"{home['name']} - {away['name']}",
                    "time": dt.strftime("%d-%m %H:%M"),
                    "league": m["league"]["country"] + " - " + league,
                    "hs": hs, "hc": hc,
                    "as": as_, "ac": ac
                })

            checked += 1

        except:
            continue

    return res, checked

# ==============================
# RAPOR (FINAL FORMAT)
# ==============================
def report(matches, checked, picks):
    now_str = now().strftime("%d-%m %H:%M")

    lines = []
    lines.append("🔥 HÜNKAR BTTS 🔥")
    lines.append(f"🕒 {now_str}")
    lines.append("📅 Bugün + Yarın")
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

            avg = (p["hs"] + p["hc"] + p["as"] + p["ac"]) / 4

            if avg >= 4:
                guc = "YÜKSEK"
            elif avg >= 3.5:
                guc = "ORTA-YÜKSEK"
            else:
                guc = "ORTA"

            lines.append(f"{i}. {p['match']}")
            lines.append(f"⏰ {p['time']} | {p['league']}")
            lines.append(f"A: {p['hs']}/5 atmış | {p['hc']}/5 yemiş")
            lines.append(f"B: {p['as']}/5 atmış | {p['ac']}/5 yemiş")
            lines.append(f"💪 {guc}")
            lines.append("")

    if ERRORS:
        lines.append("❌ Hata:")
        for e in ERRORS[:2]:
            lines.append(f"- {e}")

    return "\n".join(lines)

# ==============================
# MAIN
# ==============================
def main():
    print("BOT BASLADI")

    if not API_KEY:
        send("❌ API KEY YOK")
        return

    matches = get_matches()
    picks, checked = analyze(matches)

    text = report(matches, checked, picks)

    print(text)
    send(text)

if __name__ == "__main__":
    main()
