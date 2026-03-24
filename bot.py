import requests
import time
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- 🔑 ANAHTARLARIN (Tırnakları silmeden içine yapıştır!) ---
# BotFather'dan aldığın kod:
TELEGRAM_TOKEN = '8747036915:AAES-UKrjW3xU891kX9s36sNn5gdaNlgaz8'
# Dashboard'daki "API Key" kısmındaki uzun kod:
FOOTBALL_API_KEY = '9d815aaf3a5947e681eda9a895a281b5'

class MerdanProfesyonelBeyin:
    def __init__(self):
        # ⚠️ GÜNCELLEME: API-SPORTS Dashboard için doğru başlık
        self.headers = {
            'x-apisports-key': FOOTBALL_API_KEY
        }
        self.almanya_tz = pytz.timezone('Europe/Berlin')
        self.cache = {} # 1 saatlik koruma hafızası
        self.last_sync = 0
        
        # --- 📊 LİG DNA VERİ TABANI ---
        self.GOLLU_LIGLER = ["Bundesliga", "Eredivisie", "Super League", "Premier League"]
        self.KISIR_LIGLER = ["Serie B", "Segunda Division", "Ligue 2", "Super League 1"]

    def veri_cek(self):
        """API-SPORTS Uyumlu: 1 saatte bir veri çeker, kotanı (100 hak) korur."""
        simdi = time.time()
        if "fikstur" in self.cache and (simdi - self.last_sync) < 3600:
            return self.cache["fikstur"]

        bugun = datetime.now(self.almanya_tz).strftime('%Y-%m-%d')
        
        # ⚠️ GÜNCELLEME: API-SPORTS Dashboard için doğru URL
        url = "https://v3.football.api-sports.io"
        params = {"date": bugun, "status": "NS"} # Henüz başlamamış maçlar
        
        try:
            res = requests.get(url, headers=self.headers, params=params, timeout=15)
            
            # Yetki veya limit hatalarını kontrol et
            if res.status_code == 403: return "HATA: API Key Geçersiz veya Abone Olunmamış!"
            if res.status_code == 429: return "HATA: Günlük 100 İstek Limitine Ulaşıldı!"
            
            data = res.json().get('response', [])
            self.cache["fikstur"] = data
            self.last_sync = simdi
            return data
        except Exception as e:
            return f"HATA_BAGLANTI: {str(e)}"

    def elit_analiz_et(self, mac):
        try:
            lig = mac['league']['name']
            ev = mac['teams']['home']['name']
            dep = mac['teams']['away']['name']
            
            # API'den gelen UTC saati Almanya saatine çeviriyoruz
            utc_dt = datetime.fromisoformat(mac['fixture']['date'].replace('Z', '+00:00'))
            al_dt = utc_dt.astimezone(self.almanya_tz)
            
            puan = 70 # Analiz başlangıç puanı
            notum = "✅ Standart Filtre."

            # Lig DNA Analizi
            if any(l in lig for l in self.GOLLU_LIGLER):
                puan += 20
                notum = "🔥 GOL POTANSİYELİ: Ligin DNA'sı gollü geçmeye müsait."
            elif any(l in lig for l in self.KISIR_LIGLER):
                puan -= 25
                notum = "⚠️ KISIR LİG UYARISI: Takımlar formda olsa da lig defansif."

            # Sert Filtre: Sadece %80 ve üzeri güvenli maçları göster
            if puan < 80: return None

            return (f"📅 {al_dt.strftime('%d.%m.%Y')} | ⏰ *{al_dt.strftime('%H:%M')}* (DE)\n"
                    f"🏆 {lig}\n"
                    f"⚽️ *{ev} - {dep}*\n"
                    f"📊 **GÜVEN PUANI: {min(puan, 100)}/100**\n"
                    f"💡 **Analiz:** {notum}\n"
                    f"🎯 Tahmin: `MS 1 / KG VAR / 2.5 ÜST`\n"
                    f"━━━━━━━━━━━━━━━\n\n")
        except:
            return None

# Global beyin nesnesi (Cache'in her startta sıfırlanmaması için)
beyin_merdan = MerdanProfesyonelBeyin()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📡 **ALMANYA ANALİZ İSTASYONU AKTİF!**\nBugünkü elit maçlar taranıyor...")
    
    sonuc = beyin_merdan.veri_cek()
    
    if isinstance(sonuc, str) and "HATA" in sonuc:
        await update.message.reply_text(f"❌ {sonuc}")
        return

    rapor = "💎 **ELİT ANALİZ RAPORU (%80+ GÜVEN)** 💎\n\n"
    bulunan = 0
    for mac in sonuc:
        metin = beyin_merdan.elit_analiz_et(mac)
        if metin:
            rapor += metin
            bulunan += 1

    if bulunan == 0:
        await update.message.reply_text("📭 Bugün senin sert şartlarına ve Lig DNA'sına uyan elit maç bulunamadı.")
    else:
        await update.message.reply_text(rapor, parse_mode='Markdown')

if __name__ == '__main__':
    # Tokenlerin boş olup olmadığını kontrol et
    if 'BURAYA_' in TELEGRAM_TOKEN or 'BURAYA_' in FOOTBALL_API_KEY:
        print("❌ HATA: Lütfen kodun başındaki TOKEN ve API KEY kısımlarını doldur!")
    else:
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        print("🚀 Merdan Bey, Bot Almanya'da Komut Bekliyor!")
        app.run_polling()
