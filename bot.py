import os
import requests
import datetime
import traceback

API_KEY = os.getenv("API_KEY", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

def log(msg):
    print(msg, flush=True)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    try:
        r = requests.post(url, data=data, timeout=20)
        log(f"Telegram status: {r.status_code}")
        log(f"Telegram cevap: {r.text[:500]}")
    except Exception as e:
        log(f"Telegram hata: {e}")

def get_matches_by_date(date_str):
    url = f"{BASE_URL}/fixtures?date={date_str}"
    log(f"Tarih deneniyor: {date_str}")
    log(f"URL: {url}")

    r = requests.get(url, headers=HEADERS, timeout=30)

    log(f"Fixtures status: {r.status_code}")
    log(f"Fixtures cevap: {r.text[:1000]}")

    if r.status_code != 200:
        return []

    data = r.json()

    if data.get("errors"):
        log(f"API errors: {data['errors']}")

    log(f"Results: {data.get('results')}")
    return data.get("response", [])

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

        send_telegram_message("✅ Bot aktif. Maç verisi test ediliyor.")

        today = datetime.datetime.utcnow().date()
        dates = [
            today.strftime("%Y-%m-%d"),
            (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        ]

        matches = []
        used_date = None

        for d in dates:
            matches = get_matches_by_date(d)
            if matches:
                used_date = d
                break

        if not matches:
            send_telegram_message("⚠️ API çalıştı ama bugün/yarın/dün için maç verisi boş döndü. Deploy loguna bak.")
            return

        msg = f"✅ Maç bulundu ({used_date})\n\n{format_matches(matches, 10)}"
        send_telegram_message(msg)

    except Exception as e:
        err = f"❌ HATA: {e}\n\n{traceback.format_exc()}"
        log(err)
        send_telegram_message(err[:3500])

if __name__ == "__main__":
    main()
