import requests
from datetime import datetime

API_KEY = "9d815aaf3a5947e681eda9a895a281b5"
BOT_TOKEN = "BURAYA_BOT_TOKEN"
CHAT_ID = "BURAYA_CHAT_ID"

BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY.strip()
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
        return []

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        requests.post(url, data=payload, timeout=20)
        print("Telegram gonderildi")
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
    print(message)
    send_telegram(message)
