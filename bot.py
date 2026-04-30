import os
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

API_KEY = os.getenv("API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BASE_URL = "https://api.oddalerts.com/api"
TZ = ZoneInfo("Europe/Berlin")

def tg_send(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }, timeout=20)

def check_env():
    missing = []
    if not API_KEY:
        missing.append("API_KEY")
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not CHAT_ID:
        missing.append("CHAT_ID")

    if missing:
        print("Eksik ENV:", missing)
        return False
    return True

def oddalerts_get(path, params=None):
    params = params or {}
    params["api_token"] = API_KEY

    url = f"{BASE_URL}{path}"
    r = requests.get(url, params=params, timeout=30)

    print("URL:", r.url)
    print("STATUS:", r.status_code)

    if r.status_code != 200:
        print("API ERROR:", r.text[:500])
        return None

    try:
        return r.json()
    except Exception as e:
        print("JSON ERROR:", e)
        return None

def get_fixtures():
    today = datetime.now(TZ).date()
    tomorrow = today + timedelta(days=1)

    data = oddalerts_get("/fixtures", {
        "from": str(today),
        "to": str(tomorrow)
    })

    if not data:
        return []

    if isinstance(data, dict):
        if "data" in data:
            return data["data"]
        if "fixtures" in data:
            return data["fixtures"]

    if isinstance(data, list):
        return data

    return []

def safe_get(obj, keys, default=""):
    for k in keys:
        if isinstance(obj, dict) and k in obj:
            return obj[k]
    return default

def analyse_fixture(f):
    home = safe_get(f, ["home_name", "home", "home_team", "localteam_name"], "Home")
    away = safe_get(f, ["away_name", "away", "away_team", "visitorteam_name"], "Away")
    league = safe_get(f, ["league_name", "league", "competition_name"], "Lig yok")
    date = safe_get(f, ["date", "start_time", "kickoff", "time"], "")

    btts = safe_get(f, ["btts", "btts_percentage", "btts_percent"], None)
    over25 = safe_get(f, ["over_25", "over25", "over_25_percentage"], None)

    score = 0

    try:
        if btts is not None and float(btts) >= 70:
            score += 40
    except:
        pass

    try:
        if over25 is not None and float(over25) >= 65:
            score += 25
    except:
        pass

    good_leagues = [
        "Eredivisie", "Bundesliga", "Belgium", "MLS",
        "A-League", "Norway", "Sweden", "Iceland",
        "Switzerland", "Austria"
    ]

    if any(x.lower() in str(league).lower() for x in good_leagues):
        score += 20

    if score >= 50:
        return {
            "home": home,
            "away": away,
            "league": league,
            "date": date,
            "btts": btts,
            "over25": over25,
            "score": score
        }

    return None

def run_analysis():
    fixtures = get_fixtures()

    if not fixtures:
        tg_send("⚠️ OddAlerts çalıştı ama maç verisi boş döndü.")
        return

    picks = []

    for f in fixtures:
        pick = analyse_fixture(f)
        if pick:
            picks.append(pick)

    msg = []
    msg.append("🔥 <b>Merdan Bot BTTS Analiz</b>")
    msg.append(f"📅 {datetime.now(TZ).strftime('%d.%m.%Y %H:%M')}")
    msg.append(f"✅ Toplam maç: {len(fixtures)}")
    msg.append(f"🎯 Filtre geçen: {len(picks)}")
    msg.append("")

    if not picks:
        msg.append("Bugün kral filtresinden geçen sağlam maç yok.")
    else:
        for i, p in enumerate(picks[:10], 1):
            msg.append(
                f"{i}) <b>{p['home']} - {p['away']}</b>\n"
                f"🏆 {p['league']}\n"
                f"⏰ {p['date']}\n"
                f"BTTS: {p['btts']} | Üst 2.5: {p['over25']}\n"
                f"🔥 Skor: {p['score']}/100\n"
            )

    tg_send("\n".join(msg))

def main():
    print("Merdan bot başlıyor...")

    if not check_env():
        return

    tg_send("✅ Merdan Bot aktif kral.")

    run_analysis()

    while True:
        print("Bot ayakta:", datetime.now(TZ))
        time.sleep(60)

if __name__ == "__main__":
    main()
