import os
import requests
from datetime import datetime

API_KEY = os.getenv("API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": (API_KEY or "")
}

def test_api():
    print("API TEST BASLIYOR...")

    r = requests.get(
        f"{BASE_URL}/fixtures",
        headers=HEADERS,
        params={"date": datetime.now().strftime("%Y-%m-%d")},
        timeout=20
    )

    print("STATUS:", r.status_code)

    data = r.json()

    print("ERROR:", data.get("errors"))
    print("MAC SAYISI:", len(data.get("response", [])))

    if data.get("response"):
        print("API CALISIYOR")
        return data["response"]
    else:
        print("API VERI DONMUYOR")
        print(data)
        return []

def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("BOT_TOKEN veya CHAT_ID eksik")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        resp = requests.post(url, data=payload, timeout=20)
        print("TELEGRAM STATUS:", resp.status_code)
        print("TELEGRAM CEVAP:", resp.text)
    except Exception as e:
        print("TELEGRAM HATA:", e)

def simple_analyze(matches):
    if not matches:
        return "API veri cekemedi"

    msg = "HUNKAR BOT TEST\n\n"
    msg += f"Toplam mac: {len(matches)}\n\n"
    msg += "Ilk 5 mac:\n"

    for m in matches[:5]:
        home = m["teams"]["home"]["name"]
        away = m["teams"]["away"]["name"]
        msg += f"- {home} vs {away}\n"

    return msg

if __name__ == "__main__":
    matches = test_api()
    message = simple_analyze(matches)
    print("MESAJ:")
    print(message)
    send_telegram(message)
