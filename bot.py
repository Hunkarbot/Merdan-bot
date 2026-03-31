import os
import requests
import datetime
import traceback
from zoneinfo import ZoneInfo

API_KEY = os.getenv("API_KEY", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
TZ = ZoneInfo("Europe/Berlin")

def log(msg):
    print(msg, flush=True)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text[:3900]}
    try:
        r = requests.post(url, data=data, timeout=20)
        log(f"Telegram status: {r.status_code}")
    except Exception as e:
        log(f"Telegram hata: {e}")

def get_matches_by_date(date_str):
    url = f"{BASE_URL}/fixtures?date={date_str}"
    log(f"Tarih deneniyor: {date_str}")
    log(f"URL: {url}")

    r = requests.get(url, headers=HEADERS, timeout=30)

    log(f"Fixtures status: {r.status_code}")
    raw_text = r.text[:1200]
    log(f"Fixtures raw: {raw_text}")

    if r.status_code != 200:
        return [], f"HTTP {r.status_code}\n{raw_text}"

    try:
        data = r.json()
    except Exception:
        return [], f"JSON parse hatası\n{raw_text}"

    results = data.get("results")
    errors = data.get("errors")
    response = data.get("response", [])

    debug = (
        f"Tarih: {date_str}\n"
        f"Status: {r.status_code}\n"
        f"Results: {results}\n"
        f"Errors: {errors}\n"
        f"Raw: {str(data)[:1200]}"
    )

    return response, debug

def format_matches(matches, limit=10):
    lines = []
    for m in matches[:limit]:
        league = m["league"]["name"]
        home = m["teams"]["home"]["name"]
        away = m["teams"]["away"]["name"]
        date_raw = m["fixture"]["date"]
        lines.append(f"{league} | {home} - {away} | {date_raw}")
    return "\n".join(lines)

def main():
    try:
        log("BOT BASLADI")

        if not API_KEY:
            raise ValueError("API_KEY boş")
        if not BOT_TOKEN:
            raise ValueError("BOT_TOKEN boş")
        if not CHAT_ID:
            raise ValueError("CHAT_ID boş")

        now_local = datetime.datetime.now(TZ).date()
        dates = [
            now_local.strftime("%Y-%m-%d"),
            (now_local + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            (now_local - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        ]

        send_telegram_message(
            f"✅ DEBUG TEST\nYerel tarih: {now_local}\nDenenen tarihler: {', '.join(dates)}"
        )

        found_matches = []
        found_date = None

        for d in dates:
            matches, debug = get_matches_by_date(d)
            send_telegram_message("📡 DEBUG\n" + debug)

            if matches:
                found_matches = matches
                found_date = d
                break

        if not found_matches:
            send_telegram_message("⚠️ Bugün/yarın/dün için response boş geldi.")
            return

        send_telegram_message(f"✅ Maç bulundu ({found_date})\n\n{format_matches(found_matches, 10)}")

    except Exception as e:
        err = f"❌ HATA: {e}\n\n{traceback.format_exc()}"
        log(err)
        send_telegram_message(err[:3900])

if __name__ == "__main__":
    main()
