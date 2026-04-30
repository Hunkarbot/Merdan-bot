import os
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

API_KEY = os.getenv("API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

TZ = ZoneInfo("Europe/Berlin")

ODD_BASE = "https://data.oddalerts.com/api"
TG_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

LAST_UPDATE_ID = None


TIPICO_LIGLER = [
    "Bundesliga", "2. Bundesliga",
    "Premier League", "Championship",
    "La Liga", "Serie A", "Ligue 1",
    "Eredivisie", "Eerste Divisie",
    "Belgium", "Pro League",
    "Austria", "Switzerland",
    "Super League",
    "Portugal", "MLS", "A-League",
    "Norway", "Sweden", "Denmark",
    "Turkey", "Super Lig"
]

KISIR_LIGLER = [
    "Ethiopia", "Kenya", "Tanzania",
    "Morocco", "Tunisia", "Algeria",
    "Egypt", "Uganda", "Rwanda"
]


def tg_send(text):
    try:
        requests.post(
            f"{TG_BASE}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            },
            timeout=20
        )
    except Exception as e:
        print("Telegram hata:", e)


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


def odd_get(path, params=None):
    params = params or {}
    params["api_token"] = API_KEY

    try:
        r = requests.get(f"{ODD_BASE}{path}", params=params, timeout=30)

        print("ODD URL:", r.url)
        print("ODD STATUS:", r.status_code)

        if r.status_code != 200:
            print("ODD ERROR:", r.text[:500])
            return None

        return r.json()

    except Exception as e:
        print("OddAlerts hata:", e)
        return None


def get_value(obj, keys, default=""):
    if not isinstance(obj, dict):
        return default

    for key in keys:
        if key in obj and obj[key] is not None:
            return obj[key]

    return default


def to_float(x):
    try:
        if x is None or x == "":
            return None
        return float(str(x).replace("%", "").strip())
    except:
        return None


def lig_tipico_uygun_mu(league):
    league = str(league)

    if any(x.lower() in league.lower() for x in KISIR_LIGLER):
        return False

    if any(x.lower() in league.lower() for x in TIPICO_LIGLER):
        return True

    return False


def get_btts_trends():
    data = odd_get(
        "/trends/btts",
        {
            "minStat": 70,
            "maxStat": 100,
            "duration": 86400,
            "sort": "time"
        }
    )

    if not data:
        return []

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        return data.get("data") or data.get("results") or data.get("trends") or []

    return []


def analiz_et(match):
    home = get_value(match, ["home_name", "home", "home_team", "localteam_name"], "Home")
    away = get_value(match, ["away_name", "away", "away_team", "visitorteam_name"], "Away")
    league = get_value(match, ["league_name", "league", "competition_name"], "Lig yok")
    start = get_value(match, ["start_time", "kickoff", "date", "time"], "")

    if not lig_tipico_uygun_mu(league):
        return None

    btts = to_float(get_value(match, ["stat", "btts", "btts_percentage", "percentage"], None))
    over25 = to_float(get_value(match, ["over_25", "over25", "over25_percentage"], None))

    score = 0
    reasons = []

    if btts is not None:
        if btts >= 90:
            score += 45
            reasons.append(f"BTTS çok güçlü: %{btts}")
        elif btts >= 80:
            score += 35
            reasons.append(f"BTTS güçlü: %{btts}")
        elif btts >= 70:
            score += 25
            reasons.append(f"BTTS uygun: %{btts}")

    if over25 is not None and over25 >= 65:
        score += 15
        reasons.append(f"2.5 üst desteği: %{over25}")

    if any(x.lower() in str(league).lower() for x in [
        "Eredivisie", "Bundesliga", "Belgium",
        "Austria", "Switzerland", "MLS", "A-League"
    ]):
        score += 20
        reasons.append("Gollü lig bonusu")

    if score < 45:
        return None

    if score >= 80:
        market = "BTTS JA güçlü"
    elif score >= 60:
        market = "BTTS JA aday"
    else:
        market = "BTTS izlenir"

    return {
        "home": home,
        "away": away,
        "league": league,
        "start": start,
        "btts": btts,
        "over25": over25,
        "score": score,
        "market": market,
        "reasons": reasons[:4]
    }


def maclari_analiz_et():
    matches = get_btts_trends()

    if not matches:
        tg_send("⚠️ OddAlerts BTTS trend verisi boş döndü kral.")
        return

    picks = []

    for m in matches:
        analiz = analiz_et(m)
        if analiz:
            picks.append(analiz)

    picks = sorted(picks, key=lambda x: x["score"], reverse=True)

    msg = []
    msg.append("🔥 <b>MERDAN BOT — TIPICO BTTS ADAYLARI</b>")
    msg.append(f"🕒 {datetime.now(TZ).strftime('%d.%m.%Y %H:%M')}")
    msg.append(f"📊 Taranan trend: {len(matches)}")
    msg.append(f"🎯 Filtre geçen: {len(picks)}")
    msg.append("")

    if not picks:
        msg.append("Bugün Tipico aday liglerden güçlü BTTS çıkmadı kral.")
    else:
        for i, p in enumerate(picks[:12], 1):
            msg.append(
                f"{i}) <b>{p['home']} - {p['away']}</b>\n"
                f"🏆 {p['league']}\n"
                f"⏰ {p['start']}\n"
                f"🎯 <b>{p['market']}</b>\n"
                f"🔥 Güç: {p['score']}/100\n"
                f"📌 {' | '.join(p['reasons'])}\n"
            )

    tg_send("\n".join(msg))


def handle_message(text):
    text = text.strip().lower()

    if text in ["/start", "start"]:
        tg_send(
            "✅ Merdan Bot aktif kral.\n\n"
            "Komutlar:\n"
            "/maclar — BTTS aday maçları getirir\n"
            "/test — bot testi"
        )

    elif text in ["/test", "test"]:
        tg_send("✅ Test başarılı kral. Bot ayakta.")

    elif text in ["/maclar", "maclar", "/analiz", "analiz"]:
        tg_send("⏳ Maçları tarıyorum kral...")
        maclari_analiz_et()

    else:
        tg_send("Kral komut: /maclar")


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
        updates = get_updates()

        for update in updates:
            msg = update.get("message", {})
            chat_id = str(msg.get("chat", {}).get("id", ""))
            text = msg.get("text", "")

            if chat_id != str(CHAT_ID):
                continue

            if text:
                print("Komut geldi:", text)
                handle_message(text)

        time.sleep(2)


if __name__ == "__main__":
    main()
