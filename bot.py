import os
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

API_KEY = os.getenv("API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

TZ = ZoneInfo("Europe/Berlin")
ODD_BASE = "https://data.oddalerts.com/api"
TG_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

LAST_UPDATE_ID = None


def tg_send(text):
    try:
        requests.post(
            f"{TG_BASE}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": text[:3900],
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            },
            timeout=20
        )
    except Exception as e:
        print("Telegram hata:", e)


def odd_get(path, params=None):
    params = params or {}
    params["api_token"] = API_KEY

    try:
        r = requests.get(f"{ODD_BASE}{path}", params=params, timeout=30)
        print("ODD URL:", r.url)
        print("ODD STATUS:", r.status_code)
        print("ODD TEXT:", r.text[:500])

        if r.status_code != 200:
            return None

        return r.json()
    except Exception as e:
        print("OddAlerts hata:", e)
        return None


def get_updates():
    global LAST_UPDATE_ID

    params = {"timeout": 25}
    if LAST_UPDATE_ID is not None:
        params["offset"] = LAST_UPDATE_ID + 1

    try:
        r = requests.get(f"{TG_BASE}/getUpdates", params=params, timeout=35)
        data = r.json()
    except Exception as e:
        print("Update hata:", e)
        return []

    updates = data.get("result", [])
    if updates:
        LAST_UPDATE_ID = updates[-1]["update_id"]

    return updates


def extract_list(data):
    if not data:
        return []

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ["data", "fixtures", "matches", "results", "trends", "predictions"]:
            val = data.get(key)
            if isinstance(val, list):
                return val

    return []


def val(obj, keys, default=""):
    if not isinstance(obj, dict):
        return default

    for k in keys:
        if k in obj and obj[k] not in [None, ""]:
            return obj[k]

    return default


def num(x):
    try:
        if x in [None, ""]:
            return None
        return float(str(x).replace("%", "").strip())
    except:
        return None


def get_team_names(m):
    home = val(m, ["home_name", "home", "home_team", "localteam_name", "homeTeam"], "Home")
    away = val(m, ["away_name", "away", "away_team", "visitorteam_name", "awayTeam"], "Away")
    league = val(m, ["league_name", "league", "competition_name", "competition"], "Lig yok")
    start = val(m, ["start_time", "kickoff", "date", "time", "starting_at"], "")
    return home, away, league, start


def goal_band_analysis(m):
    home, away, league, start = get_team_names(m)

    avg_goals = num(val(m, ["avg_goals", "average_goals", "goals_avg", "total_goals_avg"], None))
    over25 = num(val(m, ["over25", "over_25", "over25_percentage", "over_25_percentage"], None))
    btts = num(val(m, ["btts", "btts_percentage", "btts_yes_percentage", "stat", "percentage"], None))

    score = 0
    reasons = []

    if avg_goals is not None:
        if avg_goals >= 3.2:
            score += 35
            reasons.append(f"Gol ortalaması yüksek: {avg_goals}")
        elif avg_goals >= 2.6:
            score += 25
            reasons.append(f"Gol ortalaması iyi: {avg_goals}")
        elif avg_goals <= 2.0:
            score -= 20
            reasons.append(f"Gol ortalaması düşük: {avg_goals}")

    if over25 is not None:
        if over25 >= 75:
            score += 30
            reasons.append(f"2.5 üst güçlü: %{over25}")
        elif over25 >= 60:
            score += 18
            reasons.append(f"2.5 üst destekli: %{over25}")

    if btts is not None:
        if btts >= 75:
            score += 25
            reasons.append(f"BTTS güçlü: %{btts}")
        elif btts >= 60:
            score += 12
            reasons.append(f"BTTS destekli: %{btts}")

    gollu_ligler = ["Bundesliga", "Eredivisie", "Belgium", "Austria", "Switzerland", "MLS", "A-League"]
    kisir_ligler = ["Egypt", "Morocco", "Tunisia", "Algeria", "Kenya", "Tanzania", "Ethiopia"]

    if any(x.lower() in str(league).lower() for x in gollu_ligler):
        score += 15
        reasons.append("Gollü lig bonusu")

    if any(x.lower() in str(league).lower() for x in kisir_ligler):
        score -= 20
        reasons.append("Kısır lig riski")

    if score >= 75:
        band = "3-5 gol"
        market = "2.5 ÜST / BTTS+ÜST"
        scenario = "2-1 / 3-1 / 3-2"
    elif score >= 55:
        band = "2-4 gol"
        market = "1.5 ÜST ana, 2.5 ÜST aday"
        scenario = "1-1 / 2-1 / 2-2"
    elif score >= 30:
        band = "2-3 gol"
        market = "1.5 ÜST + 3.5 ALT"
        scenario = "1-1 / 2-0 / 2-1"
    else:
        band = "0-2 gol"
        market = "2.5 ALT / HT 0-0 izlenir"
        scenario = "0-0 / 1-0 / 1-1"

    return {
        "home": home,
        "away": away,
        "league": league,
        "start": start,
        "score": max(0, min(100, score)),
        "band": band,
        "market": market,
        "scenario": scenario,
        "reasons": reasons[:4]
    }


def debug_oddalerts():
    today = datetime.now(TZ).date()
    tomorrow = today + timedelta(days=1)

    tests = [
        ("/fixtures", {}),
        ("/fixtures", {"date": str(today)}),
        ("/fixtures", {"from": str(today), "to": str(tomorrow)}),
        ("/trends/btts", {"minStat": 1, "maxStat": 100, "duration": 604800}),
        ("/trends/over25", {"minStat": 1, "maxStat": 100, "duration": 604800}),
        ("/predictions", {}),
    ]

    lines = ["🧪 <b>OddAlerts API Debug</b>"]

    for path, params in tests:
        data = odd_get(path, params)
        items = extract_list(data)

        if isinstance(data, dict):
            keys = list(data.keys())[:8]
        elif isinstance(data, list) and data:
            keys = list(data[0].keys())[:8]
        else:
            keys = []

        lines.append(
            f"\n<b>{path}</b>\n"
            f"Count: {len(items)}\n"
            f"Keys: {keys}"
        )

    tg_send("\n".join(lines))


def get_matches():
    today = datetime.now(TZ).date()
    tomorrow = today + timedelta(days=1)

    endpoints = [
        ("/fixtures", {"from": str(today), "to": str(tomorrow)}),
        ("/fixtures", {"date": str(today)}),
        ("/trends/over25", {"minStat": 1, "maxStat": 100, "duration": 604800}),
        ("/trends/btts", {"minStat": 1, "maxStat": 100, "duration": 604800}),
        ("/predictions", {}),
    ]

    for path, params in endpoints:
        data = odd_get(path, params)
        items = extract_list(data)

        if items:
            print("DATA FOUND:", path, len(items))
            return items, path

    return [], "none"


def maclari_analiz_et():
    matches, source = get_matches()

    if not matches:
        tg_send("⚠️ OddAlerts veri boş döndü kral. /debug yaz, hangi endpoint veri veriyor görelim.")
        return

    analizler = []
    for m in matches:
        analizler.append(goal_band_analysis(m))

    analizler = sorted(analizler, key=lambda x: x["score"], reverse=True)

    msg = []
    msg.append("🔥 <b>MERDAN BOT — GOL BANDI ANALİZİ</b>")
    msg.append(f"🕒 {datetime.now(TZ).strftime('%d.%m.%Y %H:%M')}")
    msg.append(f"📡 Kaynak: {source}")
    msg.append(f"📊 Taranan maç: {len(matches)}")
    msg.append("")

    for i, p in enumerate(analizler[:12], 1):
        msg.append(
            f"{i}) <b>{p['home']} - {p['away']}</b>\n"
            f"🏆 {p['league']}\n"
            f"⏰ {p['start']}\n"
            f"⚽ Gol bandı: <b>{p['band']}</b>\n"
            f"🎯 Yön: <b>{p['market']}</b>\n"
            f"📌 Skor senaryosu: {p['scenario']}\n"
            f"🔥 Güç: {p['score']}/100\n"
            f"🧠 {' | '.join(p['reasons']) if p['reasons'] else 'Veri sınırlı'}\n"
        )

    tg_send("\n".join(msg))


def handle_message(text):
    text = text.strip().lower()

    if text in ["/start", "start"]:
        tg_send(
            "✅ Merdan Bot aktif kral.\n\n"
            "/maclar — gol bandı analiz\n"
            "/debug — OddAlerts endpoint test\n"
            "/test — bağlantı testi"
        )

    elif text in ["/test", "test"]:
        tg_send("✅ Test başarılı kral.")

    elif text in ["/debug", "debug"]:
        tg_send("🧪 OddAlerts endpointleri test ediliyor kral...")
        debug_oddalerts()

    elif text in ["/maclar", "maclar", "/analiz", "analiz"]:
        tg_send("⏳ Maçları tarıyorum kral...")
        maclari_analiz_et()

    else:
        tg_send("Komut: /maclar veya /debug")


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

    print("Bot hazır. Komut bekleniyor.")

    while True:
        updates = get_updates()

        for update in updates:
            msg = update.get("message", {})
            chat_id = str(msg.get("chat", {}).get("id", ""))
            text = msg.get("text", "")

            if chat_id != str(CHAT_ID):
                continue

            if text:
                print("Komut:", text)
                handle_message(text)

        time.sleep(2)


if __name__ == "__main__":
    main()
