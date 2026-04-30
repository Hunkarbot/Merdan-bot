import os
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

API_KEY = os.getenv("API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

TZ = ZoneInfo("Europe/Berlin")
ODD_BASE = "https://api.oddalerts.com/api"
TG_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

LAST_UPDATE_ID = None

TIPICO_LEAGUE_KEYWORDS = [
    "Bundesliga", "2. Bundesliga",
    "Premier League", "Championship",
    "La Liga", "Serie A", "Ligue 1",
    "Eredivisie", "Eerste Divisie",
    "Belgium", "Pro League",
    "Austria", "Switzerland",
    "Super League", "Challenge League",
    "Portugal", "Primeira",
    "MLS", "A-League",
    "Norway", "Sweden", "Denmark",
    "Turkey", "Super Lig"
]

BAD_LEAGUE_KEYWORDS = [
    "Ethiopia", "Kenya", "Tanzania",
    "Uganda", "Rwanda",
    "Morocco", "Tunisia", "Algeria",
    "Egypt"
]


def tg_send(text):
    url = f"{TG_BASE}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }, timeout=20)
    except Exception as e:
        print("Telegram send error:", e)


def tg_updates():
    global LAST_UPDATE_ID

    params = {"timeout": 25}
    if LAST_UPDATE_ID is not None:
        params["offset"] = LAST_UPDATE_ID + 1

    try:
        r = requests.get(f"{TG_BASE}/getUpdates", params=params, timeout=35)
        data = r.json()
    except Exception as e:
        print("Update error:", e)
        return []

    updates = data.get("result", [])

    if updates:
        LAST_UPDATE_ID = updates[-1]["update_id"]

    return updates


def odd_get(path, params=None):
    params = params or {}
    params["api_token"] = API_KEY

    try:
        r = requests.get(f"{ODD_BASE}{path}", params=params, timeout=30)
        print("ODD:", r.url, r.status_code)

        if r.status_code != 200:
            print("OddAlerts error:", r.text[:300])
            return None

        return r.json()
    except Exception as e:
        print("OddAlerts request error:", e)
        return None


def pick_value(obj, keys, default=None):
    if not isinstance(obj, dict):
        return default

    for key in keys:
        if key in obj:
            return obj[key]

    return default


def to_float(x):
    try:
        if x is None:
            return None
        return float(str(x).replace("%", "").strip())
    except:
        return None


def league_ok(league):
    league = str(league)

    if any(x.lower() in league.lower() for x in BAD_LEAGUE_KEYWORDS):
        return False

    if any(x.lower() in league.lower() for x in TIPICO_LEAGUE_KEYWORDS):
        return True

    return False


def get_fixtures():
    today = datetime.now(TZ).date()
    tomorrow = today + timedelta(days=1)

    data = odd_get("/fixtures", {
        "from": str(today),
        "to": str(tomorrow)
    })

    if not data:
        return []

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        return data.get("data") or data.get("fixtures") or []

    return []


def analyse_match(f):
    home = pick_value(f, ["home_name", "home", "home_team", "localteam_name"], "Home")
    away = pick_value(f, ["away_name", "away", "away_team", "visitorteam_name"], "Away")
    league = pick_value(f, ["league_name", "league", "competition_name"], "Lig yok")
    start = pick_value(f, ["start_time", "kickoff", "date", "time"], "")

    if not league_ok(league):
        return None

    btts = to_float(pick_value(f, [
        "btts", "btts_percentage", "btts_percent", "btts_yes_percentage"
    ]))

    over25 = to_float(pick_value(f, [
        "over_25", "over25", "over_25_percentage", "over25_percentage"
    ]))

    home_scored = to_float(pick_value(f, [
        "home_scored_percentage", "home_scored_percent"
    ]))

    away_scored = to_float(pick_value(f, [
        "away_scored_percentage", "away_scored_percent"
    ]))

    home_conceded = to_float(pick_value(f, [
        "home_conceded_percentage", "home_conceded_percent"
    ]))

    away_conceded = to_float(pick_value(f, [
        "away_conceded_percentage", "away_conceded_percent"
    ]))

    score = 0
    reasons = []

    if btts is not None and btts >= 70:
        score += 30
        reasons.append(f"BTTS güçlü: %{btts}")

    if over25 is not None and over25 >= 65:
        score += 20
        reasons.append(f"2.5 üst desteği: %{over25}")

    if home_scored is not None and home_scored >= 80:
        score += 10
        reasons.append("Ev sahibi gol buluyor")

    if away_scored is not None and away_scored >= 80:
        score += 10
        reasons.append("Deplasman gol buluyor")

    if home_conceded is not None and home_conceded >= 80:
        score += 10
        reasons.append("Ev sahibi gol yiyor")

    if away_conceded is not None and away_conceded >= 80:
        score += 10
        reasons.append("Deplasman gol yiyor")

    if any(x.lower() in str(league).lower() for x in [
        "Eredivisie", "Bundesliga", "Belgium", "Austria", "Switzerland", "MLS", "A-League"
    ]):
        score += 10
        reasons.append("Gollü lig bonusu")

    if score >= 55:
        if score >= 75:
            market = "BTTS JA güçlü aday"
        elif over25 is not None and over25 >= 70:
            market = "2.5 ÜST aday"
        else:
            market = "BTTS izlenir"

        return {
            "home": home,
            "away": away,
            "league": league,
            "start": start,
            "score": score,
            "market": market,
            "reasons": reasons[:4],
            "btts": btts,
            "over25": over25
        }

    return None


def run_analysis():
    fixtures = get_fixtures()

    if not fixtures:
        tg_send("⚠️ OddAlerts maç verisi boş döndü kral.")
        return

    picks = []

    for f in fixtures:
        result = analyse_match(f)
        if result:
            picks.append(result)

    picks = sorted(picks, key=lambda x: x["score"], reverse=True)

    msg = []
    msg.append("🔥 <b>MERDAN BOT — TIPICO ADAY MAÇLAR</b>")
    msg.append(f"🕒 {datetime.now(TZ).strftime('%d.%m.%Y %H:%M')}")
    msg.append(f"📊 Taranan maç: {len(fixtures)}")
    msg.append(f"🎯 Filtre geçen: {len(picks)}")
    msg.append("")

    if not picks:
        msg.append("Bugün Tipico aday liglerden kral filtresini geçen net maç yok.")
    else:
        for i, p in enumerate(picks[:12], 1):
            msg.append(
                f"{i}) <b>{p['home']} - {p['away']}</b>\n"
                f"🏆 {p['league']}\n"
                f"⏰ {p['start']}\n"
                f"🎯 <b>{p['market']}</b>\n"
                f"🔥 Güç: {p['score']}/100\n"
                f"📌 " + " | ".join(p["reasons"]) + "\n"
            )

    tg_send("\n".join(msg))


def handle_message(text):
    text = text.strip().lower()

    if text in ["/start", "start"]:
        tg_send(
            "✅ Merdan Bot aktif kral.\n\n"
            "Komutlar:\n"
            "/maclar — bugünkü Tipico aday maçları analiz eder\n"
            "/test — bot bağlantı testi"
        )

    elif text in ["/test", "test"]:
        tg_send("✅ Test başarılı kral. Bot ayakta.")

    elif text in ["/maclar", "maclar", "/analiz", "analiz"]:
        tg_send("⏳ Maçları tarıyorum kral...")
        run_analysis()

    else:
        tg_send("Komut: /maclar yaz kral.")


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


def main():
    print("Merdan Bot başlıyor...")

    if not check_env():
        return

    print("Bot hazır. Spam yok. Komut bekleniyor.")

    while True:
        updates = tg_updates()

        for update in updates:
            msg = update.get("message", {})
            chat_id = str(msg.get("chat", {}).get("id"))

            if chat_id != str(CHAT_ID):
                continue

            text = msg.get("text", "")
            if text:
                print("Komut:", text)
                handle_message(text)

        time.sleep(2)


if __name__ == "__main__":
    main()
