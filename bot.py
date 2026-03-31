import os
import time
import requests
import datetime
import traceback
from zoneinfo import ZoneInfo

# =========================
# AYARLAR
# =========================
# İstersen env'den oku, istersen aşağıya direkt token yapıştır.
API_KEY = os.getenv("API_KEY", "").strip() or "BURAYA_FOOTBALL_DATA_TOKEN"
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip() or "BURAYA_TELEGRAM_BOT_TOKEN"
CHAT_ID = os.getenv("CHAT_ID", "").strip() or "BURAYA_CHAT_ID"

BASE_URL = "https://api.football-data.org/v4"
HEADERS = {
    "X-Auth-Token": API_KEY
}

TZ = ZoneInfo("Europe/Berlin")

# =========================
# YARDIMCI FONKSİYONLAR
# =========================
def log(msg: str) -> None:
    print(msg, flush=True)

def send_telegram_message(text: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        log("❌ BOT_TOKEN veya CHAT_ID boş")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text[:4000]
    }

    try:
        r = requests.post(url, data=data, timeout=20)
        log(f"📨 Telegram status: {r.status_code}")
        log(f"📨 Telegram cevap: {r.text[:500]}")
        return r.status_code == 200
    except Exception as e:
        log(f"❌ Telegram hatası: {e}")
        return False

def test_api() -> None:
    if not API_KEY or API_KEY == "BURAYA_FOOTBALL_DATA_TOKEN":
        raise ValueError("API_KEY boş")

    # football-data docs'a göre /matches endpoint'i mevcut;
    # dateFrom/dateTo ile belirli gün aralığı çekilebilir.
    today = datetime.datetime.now(TZ).strftime("%Y-%m-%d")
    url = f"{BASE_URL}/matches?dateFrom={today}&dateTo={today}"

    r = requests.get(url, headers=HEADERS, timeout=30)

    log(f"🌐 API test status: {r.status_code}")
    log(f"🌐 API test cevap: {r.text[:1000]}")

    if r.status_code != 200:
        raise ValueError(f"API test başarısız: {r.status_code} | {r.text[:300]}")

def get_matches_by_date(date_str: str):
    url = f"{BASE_URL}/matches?dateFrom={date_str}&dateTo={date_str}"
    log(f"📅 Tarih deneniyor: {date_str}")
    log(f"📅 URL: {url}")

    r = requests.get(url, headers=HEADERS, timeout=30)

    log(f"📅 Matches status: {r.status_code}")
    log(f"📅 Matches cevap: {r.text[:1200]}")

    if r.status_code != 200:
        return [], f"HTTP {r.status_code} | {r.text[:500]}"

    try:
        data = r.json()
    except Exception:
        return [], f"JSON parse hatası | raw: {r.text[:500]}"

    matches = data.get("matches", [])
    count = data.get("count", len(matches))

    debug = (
        f"Tarih: {date_str}\n"
        f"Status: {r.status_code}\n"
        f"Count: {count}\n"
        f"İlk cevap: {str(data)[:1000]}"
    )
    return matches, debug

def format_matches(matches, limit=10) -> str:
    lines = []

    for m in matches[:limit]:
        comp = m.get("competition", {}).get("name", "Bilinmeyen Lig")
        home = m.get("homeTeam", {}).get("name", "Home")
        away = m.get("awayTeam", {}).get("name", "Away")
        utc_date = m.get("utcDate", "")

        try:
            dt = datetime.datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
            local_dt = dt.astimezone(TZ).strftime("%d.%m %H:%M")
        except Exception:
            local_dt = utc_date

        status = m.get("status", "UNKNOWN")
        score_home = m.get("score", {}).get("fullTime", {}).get("home")
        score_away = m.get("score", {}).get("fullTime", {}).get("away")

        if score_home is not None and score_away is not None:
            score_text = f"{score_home}-{score_away}"
        else:
            score_text = "-"

        lines.append(f"{local_dt} | {comp} | {home} - {away} | {status} | {score_text}")

    return "\n".join(lines)

# =========================
# ANA ÇALIŞMA
# =========================
def main() -> None:
    try:
        log("🚀 BOT BAŞLADI")

        if not API_KEY or API_KEY == "BURAYA_FOOTBALL_DATA_TOKEN":
            raise ValueError("API_KEY boş")
        if not BOT_TOKEN or BOT_TOKEN == "BURAYA_TELEGRAM_BOT_TOKEN":
            raise ValueError("BOT_TOKEN boş")
        if not CHAT_ID or CHAT_ID == "BURAYA_CHAT_ID":
            raise ValueError("CHAT_ID boş")

        test_api()
        send_telegram_message("✅ Hünkar bot aktif. football-data testi başarılı.")

        now_local = datetime.datetime.now(TZ).date()
        dates = [
            now_local.strftime("%Y-%m-%d"),
            (now_local + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            (now_local - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        ]

        found_matches = []
        found_date = None

        for d in dates:
            matches, debug = get_matches_by_date(d)
            log("📡 DEBUG\n" + debug)

            if matches:
                found_matches = matches
                found_date = d
                break

            time.sleep(1.0)  # nazik olalım

        if not found_matches:
            send_telegram_message("⚠️ football-data üzerinden bugün/yarın/dün için maç bulunamadı.")
            return

        msg = f"✅ Maç bulundu ({found_date})\n\n{format_matches(found_matches, 10)}"
        send_telegram_message(msg)
        log("✅ İşlem tamam")

    except Exception as e:
        err = f"❌ HATA: {e}\n\n{traceback.format_exc()}"
        log(err)
        send_telegram_message(err[:4000])

if __name__ == "__main__":
    main()
