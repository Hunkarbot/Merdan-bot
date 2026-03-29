import os
import requests
import datetime
import traceback
from zoneinfo import ZoneInfo

# =========================
# AYARLAR
# =========================
API_KEY = os.getenv("API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY
}

TZ = ZoneInfo("Europe/Berlin")


# =========================
# TELEGRAM
# =========================
def send_telegram(message: str):
    try:
        if not BOT_TOKEN or not CHAT_ID:
            print("TELEGRAM HATA: BOT_TOKEN veya CHAT_ID eksik")
            return

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message
        }
        r = requests.post(url, data=payload, timeout=30)
        print("Telegram status:", r.status_code, r.text[:300])
    except Exception as e:
        print("Telegram gönderme hatası:", e)


# =========================
# TARİH
# =========================
def get_dates():
    now = datetime.datetime.now(TZ)
    today = now.date()
    tomorrow = today + datetime.timedelta(days=1)
    return [
        today.strftime("%Y-%m-%d"),
        tomorrow.strftime("%Y-%m-%d")
    ]


# =========================
# API
# =========================
def api_get(endpoint, params=None):
    try:
        if not API_KEY:
            raise ValueError("API_KEY eksik")

        url = f"{BASE_URL}{endpoint}"
        r = requests.get(url, headers=HEADERS, params=params, timeout=30)

        print("API URL:", r.url)
        print("API Status:", r.status_code)

        # Ham cevabı biraz göster
        raw_text = r.text[:1000]
        print("API Raw:", raw_text)

        data = r.json()

        # API hata döndürdüyse
        if r.status_code != 200:
            raise Exception(f"API HTTP HATA {r.status_code} | {raw_text}")

        # Bazı durumlarda API errors alanı dolu gelir
        api_errors = data.get("errors")
        if api_errors:
            raise Exception(f"API errors: {api_errors}")

        return data

    except Exception as e:
        err = f"API_GET HATA\nEndpoint: {endpoint}\nParams: {params}\nHata: {e}"
        print(err)
        print(traceback.format_exc())
        send_telegram(err)
        return None


# =========================
# TEST
# =========================
def test_api_and_key():
    try:
        send_telegram("Test başladı: API key ve fixtures kontrol ediliyor.")

        if not API_KEY:
            raise ValueError("API_KEY ortam değişkeni boş")
        if not BOT_TOKEN:
            raise ValueError("BOT_TOKEN ortam değişkeni boş")
        if not CHAT_ID:
            raise ValueError("CHAT_ID ortam değişkeni boş")

        # Önce basit bir endpoint ile key testi
        status_data = api_get("/status")
        if not status_data:
            raise Exception("/status endpoint boş döndü")

        send_telegram("API key geçerli görünüyor. Şimdi fixtures test ediliyor.")

        dates = get_dates()
        total_all = 0
        lines = []

        for date in dates:
            data = api_get("/fixtures", {"date": date})
            if not data:
                lines.append(f"{date}: veri alınamadı")
                continue

            results = data.get("results", 0)
            response = data.get("response", [])
            total_all += len(response)

            lines.append(f"{date}: {len(response)} maç")

            if len(response) > 0:
                first = response[0]
                home = first["teams"]["home"]["name"]
                away = first["teams"]["away"]["name"]
                league = first["league"]["name"]
                lines.append(f"Örnek: {home} - {away} | {league}")

        final_msg = "API TEST SONUCU\n\n" + "\n".join(lines) + f"\n\nToplam çekilen maç: {total_all}"
        print(final_msg)
        send_telegram(final_msg)

    except Exception as e:
        err_text = f"GENEL TEST HATASI\n{e}\n\n{traceback.format_exc()}"
        print(err_text)
        send_telegram(err_text)


if __name__ == "__main__":
    test_api_and_key()
