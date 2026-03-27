import requests
import datetime
import os

API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BASE_URL = "https://api.football-data.org/v4"

HEADERS = {
    "X-Auth-Token": API_KEY
}


def telegram_gonder(mesaj):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": mesaj
    }

    try:
        r = requests.post(url, data=data, timeout=30)
        print("TELEGRAM STATUS:", r.status_code)
        print("TELEGRAM CEVAP:", r.text)
    except Exception as e:
        print("TELEGRAM HATASI:", e)


def api_test():
    try:
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)

        url = f"{BASE_URL}/matches"
        params = {
            "dateFrom": today.strftime("%Y-%m-%d"),
            "dateTo": tomorrow.strftime("%Y-%m-%d")
        }

        r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        print("API STATUS:", r.status_code)
        print("API CEVAP:", r.text[:1000])

        return r.status_code == 200
    except Exception as e:
        print("API TEST HATASI:", e)
        return False


def maclari_cek():
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    url = f"{BASE_URL}/matches"
    params = {
        "dateFrom": today.strftime("%Y-%m-%d"),
        "dateTo": tomorrow.strftime("%Y-%m-%d")
    }

    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        print("MAC CEKME STATUS:", r.status_code)

        data = r.json()
        matches = data.get("matches", [])
        sonuc = []

        for m in matches:
            home = m.get("homeTeam", {}).get("name", "Bilinmiyor")
            away = m.get("awayTeam", {}).get("name", "Bilinmiyor")
            utc_date = m.get("utcDate", "")
            status = m.get("status", "")
            competition = m.get("competition", {}).get("name", "Lig Yok")

            satir = f"{home} - {away} | {competition} | {utc_date} | {status}"
            sonuc.append(satir)

        return sonuc

    except Exception as e:
        print("MAC CEKME HATASI:", e)
        return []


def main():
    if not API_KEY:
        print("FOOTBALL_DATA_API_KEY eksik")
        return

    if not BOT_TOKEN:
        print("BOT_TOKEN eksik")
        return

    if not CHAT_ID:
        print("CHAT_ID eksik")
        return

    if not api_test():
        telegram_gonder("❌ API çalışmıyor kral")
        return

    maclar = maclari_cek()

    if not maclar:
        telegram_gonder("Bugün ve gece maçları bulunamadı kral.")
        return

    mesaj = "📅 BUGÜN + GECE MAÇLARI\n\n"
    mesaj += "\n".join(maclar[:40])

    telegram_gonder(mesaj)


if __name__ == "__main__":
    main()
