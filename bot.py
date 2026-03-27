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
    r = requests.post(url, data=data, timeout=30)
    print("TELEGRAM STATUS:", r.status_code)
    print("TELEGRAM CEVAP:", r.text)

def api_test():
    url = f"{BASE_URL}/matches"
    today = datetime.date.today().strftime("%Y-%m-%d")
    params = {
        "dateFrom": today,
        "dateTo": today
    }

    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        print("API STATUS:", r.status_code)
        print("API CEVAP:", r.text[:1000])
        return r.status_code == 200
    except Exception as e:
        print("API HATA:", str(e))
        return False

def bugunun_maclari():
    today = datetime.date.today().strftime("%Y-%m-%d")

    url = f"{BASE_URL}/matches"
    params = {
        "dateFrom": today,
        "dateTo": today
    }

    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    print("MAC STATUS:", r.status_code)
    print("MAC CEVAP:", r.text[:1000])

    if r.status_code != 200:
        return []

    data = r.json()
    matches = data.get("matches", [])
    sonuc = []

    for m in matches:
        home = m.get("homeTeam", {}).get("name", "Bilinmiyor")
        away = m.get("awayTeam", {}).get("name", "Bilinmiyor")
        utc_date = m.get("utcDate", "")
        status = m.get("status", "")

        sonuc.append(f"{home} - {away} | {utc_date} | {status}")

    return sonuc

def main():
    if not API_KEY or not BOT_TOKEN or not CHAT_ID:
        print("ENV eksik")
        return

    if not api_test():
        telegram_gonder("❌ API çalışmıyor kral")
        return

    maclar = bugunun_maclari()

    if not maclar:
        telegram_gonder("Bugün maç bulunamadı kral.")
        return

    mesaj = "📅 BUGÜNÜN MAÇLARI\n\n" + "\n".join(maclar[:20])
    telegram_gonder(mesaj)

if __name__ == "__main__":
    main()
