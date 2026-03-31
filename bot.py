import os
import requests
import datetime
import traceback

# =========================
# AYARLAR
# =========================
API_KEY = os.getenv("API_KEY", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY
}

# =========================
# YARDIMCI
# =========================
def log(msg):
    print(msg, flush=True)

def send_telegram_message(text):
    if not BOT_TOKEN or not CHAT_ID:
        log("❌ BOT_TOKEN veya CHAT_ID boş")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text
    }

    try:
        r = requests.post(url, data=data, timeout=20)
        log(f"📨 Telegram status: {r.status_code}")
        log(f"📨 Telegram cevap: {r.text[:500]}")
        return r.status_code == 200
    except Exception as e:
        log(f"❌ Telegram gönderim hatası: {e}")
        return False

def test_api():
    if not API_KEY:
        raise ValueError("API_KEY ortam değişkeni boş")

    url = f"{BASE_URL}/status"
    r = requests.get(url, headers=HEADERS, timeout=20)
    log(f"🌐 API status code: {r.status_code}")
    log(f"🌐 API cevap: {r.text[:500]}")

    if r.status_code != 200:
        raise ValueError(f"API test başarısız: {r.status_code}")

def get_matches():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    url = f"{BASE_URL}/fixtures?date={today}"

    r = requests.get(url, headers=HEADERS, timeout=30)
    log(f"📅 Fixtures status: {r.status_code}")
    log(f"📅 Fixtures cevap ilk 500 karakter: {r.text[:500]}")

    if r.status_code != 200:
        raise ValueError(f"Fixtures çekilemedi: {r.status_code}")

    data = r.json()
    return data.get("response", [])

def format_matches(matches, limit=10):
    lines = []
    for m in matches[:limit]:
        league = m["league"]["name"]
        home = m["teams"]["home"]["name"]
        away = m["teams"]["away"]["name"]
        date_raw = m["fixture"]["date"]
        lines.append(f"{league} | {home} - {away} | {date_raw}")
    return "\n".join(lines)

# =========================
# ANA AKIŞ
# =========================
def main():
    log("🚀 BOT BAŞLADI")

    try:
        log("1) API test başlıyor...")
        test_api()
        log("✅ API test tamam")

        log("2) Telegram test başlıyor...")
        send_telegram_message("✅ Bot aktif. Test mesajı başarıyla gönderildi.")
        log("✅ Telegram test tamam")

        log("3) Bugünün maçları çekiliyor...")
        matches = get_matches()
        log(f"✅ Toplam maç sayısı: {len(matches)}")

        if not matches:
            send_telegram_message("⚠️ Bugün için maç bulunamadı veya API veri döndürmedi.")
            return

        summary = format_matches(matches, limit=10)
        message = f"📋 Bugünün ilk 10 maçı:\n\n{summary}"
        send_telegram_message(message)

        log("✅ Her şey tamamlandı")

    except Exception as e:
        hata = f"❌ HATA: {str(e)}\n\n{traceback.format_exc()}"
        log(hata)
        send_telegram_message(hata[:3500])

if __name__ == "__main__":
    main()
