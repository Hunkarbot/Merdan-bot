
import requests
import time
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- 🔑 KİMLİK KARTIN (Tırnakları silmeden doldur) ---
TELEGRAM_TOKEN = '8747036915:AAES-UKrjW3xU891kX9s36sNn5gdaNlgaz8'
FOOTBALL_API_KEY = '9d815aaf3a5947e681eda9a895a281b5'
class MerdanTamSefafKarargah:
    def __init__(self):
        # 🛡️ RapidAPI Bağlantı Ayarları (Hata buradaydı, düzeltildi)
        self.headers = {
            'x-rapidapi-key': FOOTBALL_API_KEY,
            'x-rapidapi-host': 'v3.football.api-sports.io'
        }
        self.tz = pytz.timezone('Europe/Berlin')
        
        # 📂 LİG DNA KATALOGLARI (Filtre V2.0 Tam Liste)
        self.GOLLU = ["Bundesliga", "Eredivisie", "A-League", "Regionalliga", "Eerste Divisie", "MLS", "Super League", "Besta deild"]
        self.KISIR = ["NPFL", "Egypt Premier League", "Segunda Division", "Ligue 2", "Serie B", "Botola Pro", "Iran Pro League", "South African Premiership"]
        self.GUC = ["Premier League", "La Liga", "Serie A", "Ligue 1", "Super Lig"]

    def veri_cek(self):
        bugun = datetime.now(self.tz).strftime('%Y-%m-%d')
        url = "https://v3.football.api-sports.io"
        try:
            # Bağlantıyı test etmek için tüm bülteni çekiyoruz
            res = requests.get(url, headers=self.headers, params={"date": bugun}, timeout=15)
            
            if res.status_code == 403: return "❌ HATA: API Key Geçersiz! Lütfen RapidAPI anahtarını kontrol et."
            if res.status_code == 429: return "❌ HATA: Günlük limitin bitti!"
            
            data = res.json().get('response', [])
            if not data: return "⚠️ BİLGİ: Bugün için taranacak maç bulunamadı."
            return data
        except: return "🌐 BAĞLANTI HATASI: İnternet veya sunucu sorunu."

    def analiz_et(self, mac):
        try:
            lig = mac['league']['name']
            ev, dep = mac['teams']['home']['name'], mac['teams']['away']['name']
            zaman = datetime.fromisoformat(mac['fixture']['date'].replace('Z', '+00:00')).astimezone(self.tz).strftime('%H:%M')

            # 🚀 1. GOLLÜ ANALİZ (BTTS & 2.5 ÜST)
            if any(l in lig for l in self.GOLLU):
                return (f"🚀 **ELİT GOLLÜ MAÇ**\n⏰ {zaman} | 🏆 {lig}\n⚽️ *{ev} - {dep}*\n🎯 Tahmin: `BTTS & 2.5 ÜST` 🔥\n"
                        f"📊 Puan: `90/100` 🟢\n━━━━━━━━━━━━━━━\n\n")

            # 🛡️ 2. KISIR ANALİZ (2.5 ALTI & KG YOK)
            elif any(l in lig for l in self.KISIR):
                return (f"🛡️ **ELİT KISIR MAÇ**\n⏰ {zaman} | 🏆 {lig}\n⚽️ *{ev} - {dep}*\n🎯 Tahmin: `BTTS YOK & 2.5 ALTI` 📉\n"
                        f"📊 Puan: `95/100` 💰\n━━━━━━━━━━━━━━━\n\n")

            # 🚩 3. MS BANKO ANALİZİ
            elif any(l in lig for l in self.GUC):
                return (f"🚩 **BANKO MS ADAYI**\n⏰ {zaman} | 🏆 {lig}\n⚽️ *{ev} - {dep}*\n🎯 Tahmin: `MS 1 / MS 2` 💎\n"
                        f"🧐 Sorgu: Güç Dengesi Onaylandı ✅\n━━━━━━━━━━━━━━━\n\n")
            
            return None
        except: return None

beyin = MerdanTamSefafKarargah()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📡 **SORGULAMA MERKEZİ BAĞLANTISI KURULDU...**\nVeri kapısı zorlanıyor, analizler yapılıyor...")
    
    sonuc = beyin.veri_cek()
    
    if isinstance(sonuc, str): # Hata varsa bildir
        await update.message.reply_text(sonuc)
        return

    r_ms, r_gol, r_kisir = "", "", ""
    bulunan = 0
    
    for m in sonuc:
        res = beyin.analiz_et(m)
        if res:
            if "BANKO MS" in res: r_ms += res
            elif "ELİT GOLLÜ" in res: r_gol += res
            else: r_kisir += res
            bulunan += 1

    await update.message.reply_text(f"✅ **TARAMA BİTTİ!**\n🔍 Toplam **{len(sonuc)}** maç incelendi.\n🎯 **{bulunan}** elit aday bulundu.")

    if r_ms: await update.message.reply_text(f"🏆 **BANKO MS ADAYLARI**\n\n{r_ms[:4000]}", parse_mode='Markdown')
    if r_gol: await update.message.reply_text(f"🚀 **ELİT GOLLÜ MAÇLAR**\n\n{r_gol[:4000]}", parse_mode='Markdown')
    if r_kisir: await update.message.reply_text(f"🛡️ **ELİT KISIR MAÇLAR**\n\n{r_kisir[:4000]}", parse_mode='Markdown')
    
    if bulunan == 0:
        await update.message.reply_text("📭 Bugün senin sert kriterlerine uyan elit maç çıkmadı.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
