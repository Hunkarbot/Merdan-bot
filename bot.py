import os
import sys
import time
import uuid
import requests
import datetime
import traceback
from zoneinfo import ZoneInfo

# =========================
# TEK ÇALIŞMA KİLİDİ
# =========================
LOCK_FILE = "/tmp/hunkar_bot.lock"

if os.path.exists(LOCK_FILE):
    print("Bot zaten çalışıyor, çıkıyorum.", flush=True)
    sys.exit()

with open(LOCK_FILE, "w") as f:
    f.write("running")

# =========================
# AYARLAR
# =========================
API_KEY = os.getenv("API_KEY", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()

BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}
TZ = ZoneInfo("Europe/Berlin")

COMP_CODES = ["BL1", "BL2", "PL", "ELC", "DED", "PPL", "SA", "PD"]

REQUEST_SLEEP_SECONDS = 1.5
RUN_ID = str(uuid.uuid4())[:8]

def cleanup_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception as e:
        print(f"Lock silinemedi: {e}", flush=True)

def log(msg):
    now = datetime.datetime.now(TZ).strftime("%d.%m %H:%M:%S")
    print(f"[{now}] [RUN:{RUN_ID}] {msg}", flush=True)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text[:4000],
    }
    try:
        r = requests.post(url, data=payload, timeout=20)
        log(f"Telegram status: {r.status_code}")
        if r.status_code != 200:
            log(f"Telegram raw: {r.text[:300]}")
        return r.status_code == 200
    except Exception as e:
        log(f"Telegram hata: {e}")
        return False

def validate_env():
    if not API_KEY:
        raise ValueError("API_KEY boş")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN boş")
    if not CHAT_ID:
        raise ValueError("CHAT_ID boş")

def env_fingerprint():
    api_part = API_KEY[:4] if API_KEY else "BOS"
    bot_part = BOT_TOKEN[:8] if BOT_TOKEN else "BOS"
    return f"api={api_part} bot={bot_part}"

def get_matches_for_comp(comp_code, date_from, date_to):
    url = f"{BASE_URL}/competitions/{comp_code}/matches"
    params = {
        "dateFrom": date_from,
        "dateTo": date_to,
    }

    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        log(f"{comp_code} status: {r.status_code}")

        if r.status_code == 200:
            data = r.json()
            matches = data.get("matches", [])
            log(f"{comp_code} maç sayısı: {len(matches)}")
            return matches, None

        log(f"{comp_code} raw: {r.text[:200]}")
        return [], f"{comp_code}: HTTP {r.status_code}"

    except requests.RequestException as e:
        log(f"{comp_code} istek hatası: {e}")
        return [], f"{comp_code}: istek hatası"

    except Exception as e:
        log(f"{comp_code} bilinmeyen hata: {e}")
        return [], f"{comp_code}: bilinmeyen hata"

def deduplicate_matches(matches):
    seen = set()
    unique = []

    for m in matches:
        key = m.get("id") or (
            m.get("utcDate", ""),
            m.get("homeTeam", {}).get("name", ""),
            m.get("awayTeam", {}).get("name", "")
        )

        if key not in seen:
            seen.add(key)
            unique.append(m)

    return unique

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
        validate_env()

        log(f"START | {env_fingerprint()}")

        today = datetime.datetime.now(TZ).date()
        tomorrow = today + datetime.timedelta(days=1)

        date_from = today.strftime("%Y-%m-%d")
        date_to = tomorrow.strftime("%Y-%m-%d")

        all_matches = []
        errors = []

        for code in COMP_CODES:
            matches, error = get_matches_for_comp(code, date_from, date_to)

            if matches:
                all_matches.extend(matches)

            if error:
                errors.append(error)

            time.sleep(REQUEST_SLEEP_SECONDS)

        all_matches = deduplicate_matches(all_matches)
        all_matches.sort(key=lambda x: x.get("utcDate", ""))

        if not all_matches and errors:
            send_telegram_message(
                f"RUN:{RUN_ID}\n"
                f"❌ Maç listesi alınamadı.\n"
                f"Aralık: {date_from} → {date_to}\n"
                f"Hatalar:\n- " + "\n- ".join(errors[:8])
            )
            return

        if not all_matches:
            send_telegram_message(
                f"RUN:{RUN_ID}\n"
                f"⚠️ Seçilen liglerde bugün/yarın maç bulunamadı.\n"
                f"Aralık: {date_from} → {date_to}"
            )
            return

        msg = (
            f"RUN:{RUN_ID}\n"
            f"✅ Toplam {len(all_matches)} maç bulundu\n"
            f"Aralık: {date_from} → {date_to}\n"
            f"Ligler: {', '.join(COMP_CODES)}\n\n"
            f"{format_matches(all_matches, 20)}"
        )

        if errors:
            msg += "\n\n⚠️ Bazı liglerde hata oldu:\n- " + "\n- ".join(errors[:5])

        send_telegram_message(msg)

    except Exception as e:
        err = (
            f"RUN:{RUN_ID}\n"
            f"❌ HATA: {e}\n\n"
            f"{traceback.format_exc()}"
        )
        log(err)
        send_telegram_message(err[:4000])

    finally:
        cleanup_lock()

if __name__ == "__main__":
    main()
