import os
import time
import requests
import datetime
import traceback
from zoneinfo import ZoneInfo

API_KEY = os.getenv("API_KEY", "").strip() or "c8f938501ce71a7c49814d19848bd858"
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip() or "8484634033:AAFh84p9869S4v2-g8tCDxYVjMG6ALTBgog"
CHAT_ID = os.getenv("CHAT_ID", "").strip() or "6878869943"

BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}
TZ = ZoneInfo("Europe/Berlin")

# İstediğin ligler
COMP_CODES = ["BL1", "BL2", "PL", "ELC", "DED", "PPL", "SA", "PD"]

# API dostu küçük bekleme
REQUEST_SLEEP_SECONDS = 1.2

# Aynı çalışmayı ayırt etmek için
RUN_ID = str(uuid.uuid4())[:8]


# =========================
# YARDIMCI FONKSİYONLAR
# =========================
def log(msg: str):
    now = datetime.datetime.now(TZ).strftime("%d.%m %H:%M:%S")
    print(f"[{now}] [RUN:{RUN_ID}] {msg}", flush=True)


def send_telegram_message(text: str) -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text[:4000],
    }

    try:
        r = requests.post(url, data=payload, timeout=20)
        log(f"Telegram status: {r.status_code}")
        if r.status_code != 200:
            log(f"Telegram raw: {r.text[:500]}")
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


def get_matches_for_comp(comp_code: str, date_from: str, date_to: str) -> tuple[list, str | None]:
    """
    Dönen değer:
    - matches: liste
    - error: None ise sorun yok, string ise hata özeti
    """
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

        # API hatası varsa "maç yok" gibi davranma
        raw = r.text[:300]
        log(f"{comp_code} raw: {raw}")
        return [], f"{comp_code}: HTTP {r.status_code}"

    except requests.RequestException as e:
        log(f"{comp_code} istek hatası: {e}")
        return [], f"{comp_code}: istek hatası"
    except Exception as e:
        log(f"{comp_code} bilinmeyen hata: {e}")
        return [], f"{comp_code}: bilinmeyen hata"


def format_match(m: dict) -> str:
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

    return f"{local_dt} | {comp} | {home} - {away} | {status}"


def format_matches(matches: list, limit: int = 20) -> str:
    return "\n".join(format_match(m) for m in matches[:limit])


def deduplicate_matches(matches: list) -> list:
    """
    Aynı maçı iki kez eklememek için.
    football-data match id varsa onu baz alıyoruz.
    """
    seen = set()
    unique = []

    for m in matches:
        match_id = m.get("id")
        key = match_id if match_id is not None else (
            m.get("utcDate", ""),
            m.get("homeTeam", {}).get("name", ""),
            m.get("awayTeam", {}).get("name", "")
        )

        if key not in seen:
            seen.add(key)
            unique.append(m)

    return unique


# =========================
# ANA AKIŞ
# =========================
def main():
    try:
        validate_env()

        today = datetime.datetime.now(TZ).date()
        tomorrow = today + datetime.timedelta(days=1)

        date_from = today.strftime("%Y-%m-%d")
        date_to = tomorrow.strftime("%Y-%m-%d")

        log(f"Başladı. Aralık: {date_from} -> {date_to}")
        log(f"Ligler: {', '.join(COMP_CODES)}")

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

        # 1) Hiç maç yok + hata da yok => gerçekten maç yok
        if not all_matches and not errors:
            msg = (
                f"RUN:{RUN_ID}\n"
                f"⚠️ Seçilen liglerde bugün/yarın maç bulunamadı.\n"
                f"Aralık: {date_from} → {date_to}\n"
                f"Ligler: {', '.join(COMP_CODES)}"
            )
            send_telegram_message(msg)
            return

        # 2) Hiç maç yok + hata var => API / erişim sorunu
        if not all_matches and errors:
            msg = (
                f"RUN:{RUN_ID}\n"
                f"❌ Maç listesi alınamadı.\n"
                f"Aralık: {date_from} → {date_to}\n"
                f"Hatalar:\n- " + "\n- ".join(errors[:8])
            )
            send_telegram_message(msg)
            return

        # 3) Maç var => özet mesaj
        summary = (
            f"RUN:{RUN_ID}\n"
            f"✅ Toplam {len(all_matches)} maç bulundu\n"
            f"Aralık: {date_from} → {date_to}\n"
            f"Ligler: {', '.join(COMP_CODES)}\n\n"
            f"{format_matches(all_matches, 20)}"
        )

        # İstersen ufak hata özetini alta ekleriz
        if errors:
            summary += "\n\n⚠️ Bazı liglerde hata oldu:\n- " + "\n- ".join(errors[:5])

        send_telegram_message(summary)

    except Exception as e:
        err = (
            f"RUN:{RUN_ID}\n"
            f"❌ HATA: {e}\n\n"
            f"{traceback.format_exc()}"
        )
        log(err)
        send_telegram_message(err[:4000])


if __name__ == "__main__":
    main()
