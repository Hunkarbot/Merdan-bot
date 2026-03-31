import os
import time
import requests
import datetime
import traceback
from zoneinfo import ZoneInfo

API_KEY = os.getenv("API_KEY", "").strip() or "BURAYA_FOOTBALL_DATA_TOKEN"
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip() or "BURAYA_TELEGRAM_BOT_TOKEN"
CHAT_ID = os.getenv("CHAT_ID", "").strip() or "BURAYA_CHAT_ID"

BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}
TZ = ZoneInfo("Europe/Berlin")

# İstediğin ligler
COMP_CODES = ["BL1", "BL2", "PL", "ELC", "DED", "PPL", "SA", "PD"]

def log(msg):
    print(msg, flush=True)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text[:4000]}
    try:
        r = requests.post(url, data=data, timeout=20)
        log(f"Telegram status: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        log(f"Telegram hata: {e}")
        return False

def get_matches_for_comp(comp_code, date_from, date_to):
    url = f"{BASE_URL}/competitions/{comp_code}/matches?dateFrom={date_from}&dateTo={date_to}"
    r = requests.get(url, headers=HEADERS, timeout=30)

    log(f"{comp_code} status: {r.status_code}")
    log(f"{comp_code} raw: {r.text[:700]}")

    if r.status_code != 200:
        return []

    data = r.json()
    return data.get("matches", [])

def format_matches(matches, limit=20):
    lines = []
    for m in matches[:limit]:
        comp = m.get("competition", {}).get("name", "Lig")
        home = m.get("homeTeam", {}).get("name", "Home")
        away = m.get("awayTeam", {}).get("name", "Away")
        utc_date = m.get("utcDate", "")
        status = m.get("status", "-")

        try:
            dt = datetime.datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
            local_dt = dt.astimezone(TZ).strftime("%d.%m %H:%M")
        except Exception:
            local_dt = utc_date

        lines.append(f"{local_dt} | {comp} | {home} - {away} | {status}")

    return "\n".join(lines)

def main():
    try:
        if not API_KEY or API_KEY == "BURAYA_FOOTBALL_DATA_TOKEN":
            raise ValueError("API_KEY boş")
        if not BOT_TOKEN or BOT_TOKEN == "BURAYA_TELEGRAM_BOT_TOKEN":
            raise ValueError("BOT_TOKEN boş")
        if not CHAT_ID or CHAT_ID == "BURAYA_CHAT_ID":
            raise ValueError("CHAT_ID boş")

        today = datetime.datetime.now(TZ).date()
        tomorrow = today + datetime.timedelta(days=1)

        date_from = today.strftime("%Y-%m-%d")
        date_to = tomorrow.strftime("%Y-%m-%d")

        send_telegram_message(
            f"✅ Hünkar bot aktif.\nAralık: {date_from} → {date_to}\nLigler: {', '.join(COMP_CODES)}"
        )

        all_matches = []

        for code in COMP_CODES:
            matches = get_matches_for_comp(code, date_from, date_to)
            if matches:
                all_matches.extend(matches)
            time.sleep(1)

        if not all_matches:
            send_telegram_message("⚠️ Seçilen liglerde bugün/yarın maç bulunamadı.")
            return

        # Tarihe göre sırala
        all_matches.sort(key=lambda x: x.get("utcDate", ""))

        send_telegram_message(
            f"✅ Toplam {len(all_matches)} maç bulundu\n\n{format_matches(all_matches, 20)}"
        )

    except Exception as e:
        err = f"❌ HATA: {e}\n\n{traceback.format_exc()}"
        log(err)
        send_telegram_message(err[:4000])

if __name__ == "__main__":
    main()
