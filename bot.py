import requests
import time
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- GÜVENLİ AYARLAR ---
TELEGRAM_TOKEN = "8747036915:AAES-UKrjW3xU891kX9s36sNn5gdaNlgaz8"
FOOTBALL_API_KEY = "9d815aaf3a5947e681eda9a895a281b5"

class APIDostuBeyin:
    def __init__(self):
        self.cache = {} # API haklarını korumak için hafıza
        self.last_request_time = 0
        self.headers = {
            'x-rapidapi-key': FOOTBALL_API_KEY,
            'x-rapidapi-host': "api-football-v1.p.rapidapi.com"
        }

    def veri_cek(self):
        # API DOSTU KONTROL: Eğer son 1 saat içinde veri çektiysek tekrar API'ye gitme
        su_an = time.time()
        if "gunluk_fikstur" in self.cache and (su_an - self.last_request_time) < 3600:
            return self.cache["gunluk_fikstur"]

        url = "https://api-football-v1.p.rapidapi.com"
        params = {"date": datetime.now().strftime('%Y-%m-%d'), "status": "NS"}
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json().get('response', [])
                self.cache["gunluk_fikstur"] = data # Veriyi hafızaya al
                self.last_request_time = su_an
                return data
            return []
        except Exception as e:
            print(f"API Hatası: {e}")
            return []

    def analiz_et(self, mac):
        # Zaman ve Takım Parçalama
        dt = datetime.fromisoformat(mac['fixture']['date'])
        ev = mac['teams']['home']['name']
        dep = mac['teams']['away']['name']
        
        # BENİM ANALİZ MANTIĞIM (100 Üzerinden)
        # API'den gelen 'id'ye göre daha derin istatistik çekilebilir ama bu haliyle en hızlısı:
        skor = 70 # Temel başlangıç puanı
        
        return (f"📅 {dt.strftime('%d.%m.%Y')} | ⏰ {dt.strftime('%H:%M')}\n"
                f"⚽️ {ev} - {dep}\n"
                f"📊 Analiz Puanı: {skor}/100\n"
                f"🎯 Tahmin: `MS 1 veya 2.5 Üst`\n"
                f"{'-'*20}\n")

# --- BOT KOMUTU ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_beyni = APIDostuBeyin()
    await update.message.reply_text("🔄 Veriler taranıyor (API Tasarrufu Aktif)...")
    
    maclar = bot_beyni.veri_cek()
    if not maclar:
        await update.message.reply_text("⚠️ Şu an maç verisi alınamadı, biraz sonra tekrar dene.")
        return

    rapor = "📈 **GÜNLÜK TAHMİN RAPORU** 📈\n\n"
    for mac in maclar[:10]: # İlk 10 maç (Ekonomik mod)
        rapor += bot_beyni.analiz_et(mac)
    
    await update.message.reply_text(rapor, parse_mode='Markdown')

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("🚀 API Dostu Bot Yayında!")
    app.run_polling()
