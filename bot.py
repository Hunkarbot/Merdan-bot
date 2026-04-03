import os
import time
import requests
import datetime
import traceback
from zoneinfo import ZoneInfo

API_KEY = os.getenv("API_KEY", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()

BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}
TZ = ZoneInfo("Europe/Berlin")

COMP_CODES = ["BL1", "PL", "ELC", "PPL", "SA", "PD"]  # BL2 403 veriyorsa şimdilik çıkardım

REQUEST_SLEEP_SECONDS = 2.0
POLL_SLEEP_SECONDS = 3
LAST_UPDATE_ID = None


def log(msg):
    now = datetime.datetime.now(TZ).strftime("%d.%m %H:%M:%S")
    print(f"[{now}] {msg}", flush=True)


def validate_env():
    if not API_KEY:
        raise ValueError("API_KEY boş")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN boş")
    if not CHAT_ID:
        raise ValueError("CHAT_ID boş")


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


def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 20}
    if offset is not None:
        params["offset"] = offset

    try:
        r = requests.get(url, params=params, timeout=30)
        if r.status_code != 200:
            log(f"getUpdates hata: {r.status_code} | {r.text[:300]}")
            return []
        data = r.json()
        return data.get("result", [])
    except Exception as e:
        log(f"getUpdates exception: {e}")
        return []


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
            return data.get("matches", []), None

        return [], f"{comp_code}: HTTP {r.status_code}"

    except Exception as e:
        return [], f"{comp_code}: {e}"


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


def build_matches_message():
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
        return (
            f"❌ Maç listesi alınamadı.\n"
            f"Aralık: {date_from} → {date_to}\n"
            f"Hatalar:\n- " + "\n- ".join(errors[:8])
        )

    if not all_matches:
        return (
            f"⚠️ Seçilen liglerde bugün/yarın maç bulunamadı.\n"
            f"Aralık: {date_from} → {date_to}"
        )

    msg = (
        f"✅ Toplam {len(all_matches)} maç bulundu\n"
        f"Aralık: {date_from} → {date_to}\n"
        f"Ligler: {', '.join(COMP_CODES)}\n\n"
        f"{format_matches(all_matches, 20)}"
    )

    if errors:
        msg += "\n\n⚠️ Bazı liglerde hata oldu:\n- " + "\n- ".join(errors[:5])

    return msg


def handle_message(text, chat_id):
    text = (text or "").strip().lower()

    if str(chat_id) != CHAT_ID:
        return

    if text == "/start":
        send_telegram_message(
            "✅ Hünkar bot hazır.\n"
            "Komutlar:\n"
            "/maclar - bugün/yarın maçları getir\n"
            "/test - bot çalışıyor mu kontrol et"
        )

    elif text == "/maclar":
        send_telegram_message("⏳ Maçlar hazırlanıyor...")
        msg = build_matches_message()
        send_telegram_message(msg)

    elif text == "/test":
        send_telegram_message("✅ Bot çalışıyor kral.")

    else:
        send_telegram_message(
            "Komut tanınmadı.\n"
            "Kullan:\n"
            "/start\n"
            "/maclar\n"
            "/test"
        )


def main():
    global LAST_UPDATE_ID

    validate_env()
    log("Bot komut bekliyor...")

    # Eski birikmiş mesajları temizle
    updates = get_updates()
    if updates:
        LAST_UPDATE_ID = updates[-1]["update_id"] + 1
        log(f"Eski update'ler temizlendi. Yeni offset: {LAST_UPDATE_ID}")

    while True:
        try:
            updates = get_updates(LAST_UPDATE_ID)

            for update in updates:
                LAST_UPDATE_ID = update["update_id"] + 1

                message = update.get("message", {})
                text = message.get("text", "")
                chat_id = message.get("chat", {}).get("id")

                log(f"Gelen mesaj: {text} | chat_id={chat_id}")

                handle_message(text, chat_id)

            time.sleep(POLL_SLEEP_SECONDS)

        except Exception as e:
            log(f"Ana döngü hatası: {e}")
            log(traceback.format_exc())
            time.sleep(5)


if __name__ == "__main__":
    main()
