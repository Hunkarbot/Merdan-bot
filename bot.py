import requests
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- 🔑 SADECE BU İKİSİNİ YAPIŞTIR VE ARANA BAKMA ---
TELEGRAM_TOKEN = '8747036915:AAES-UKrjW3xU891kX9s36sNn5gdaNlgaz8'
FOOTBALL_API_KEY = '9d815aaf3a5947e681eda9a895a281b5'
class MerdanBeyin:
    def __init__(self):
        self.headers = {'x-rapidapi-key': FOOTBALL_API_KEY, 'x-rapidapi-host': 'v3.football.api-sports.io'}
        self.tz = pytz.timezone('Europe/Istanbul')
        
        # Analiz edilecek ligler
        self.GOLLU = ["Bundesliga", "Eredivisie", "A-League", "Regionalliga", "MLS", "Super League"]
        self.KISIR = ["NPFL", "Egypt Premier League", "Segunda Division", "Ligue 2", "Serie B"]
        self.GUC = ["Premier League", "La Liga", "Serie A", "Ligue 1", "Süper Lig", "Champions League"]

    def veri_cek(self):
        bugun = datetime.now(self.tz).strftime('%Y-%m-%d')
        url = "https://v3.football.api-sports.io"
        try:
            res = requests.get(url, headers=self.headers, params={"date": bugun}, timeout=15)
            data = res.json().get('response', [])
            return data if (isinstance(data, list) and len(data) > 0) else "BOŞ"
        except: return "HATA"

    def analiz_et(self, mac):
        lig = mac['league']['name']
        ev, dep = mac['teams']['home']['name'], mac['teams']['away']['name']
        zaman = datetime.fromisoformat(mac['fixture']['date'].replace('Z', '+00:00')).astimezone(self.tz).strftime('%H:%M')

        # ANALİZ MOTORU (Senin Orijinal Metinlerin)
        if any(l.lower() in lig.lower() for l in self.GOLLU):
            return f"🚀 **ELİT GOLLÜ MAÇ**\n⏰ {zaman} | 🏆 {lig}\n⚽️ *{ev} - {dep}*\n🎯 Tahmin: `BTTS & 2.5 ÜST` 🔥\n📊 Puan: `90/100` 🟢\n━━━━━━━━━━━━━━━\n\n"
        elif any(l.lower() in lig.lower() for l in self.KISIR):
            return f"🛡️ **ELİT KISIR MAÇ**\n⏰ {zaman} | 🏆 {lig}\n⚽️ *{ev} - {dep}*\n🎯 Tahmin: `BTTS YOK & 2.5 ALTI` 📉\n📊 Puan: `95/100` 💰\n━━━━━━━━━━━━━━━\n\n"
        elif any(l.lower() in lig.lower() for l in self.GUC):
            return f"🚩 **BANKO MS ADAYI**\n⏰ {zaman} | 🏆 {lig}\n⚽️ *{ev} - {dep}*\n🎯 Tahmin: `MS 1 / MS 2` 💎\n🧐 Sorgu: Güç Dengesi Onaylandı ✅\n━━━━━━━━━━━━━━━\n\n"
        return None

merdan = MerdanBeyin()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("📡 **MERDAN BEYİN DEVREYE GİRDİ...**\nBülten taranıyor...")
    sonuc = merdan.veri_cek()
    
    if sonuc == "HATA":
        await msg.edit_text("❌ **API BAĞLANTI HATASI!**\nAnahtarını kontrol et veya limitin dolmuş olabilir.")
        return
    if sonuc == "BOŞ":
        await msg.edit_text("⚠️ **BÜLTEN BOŞ!**\nŞu an çekilecek maç verisi bulunamadı.")
        return

    r_ms, r_gol, r_kisir = "", "", ""
    bulunan = 0
    toplam = len(sonuc)
    
    for m in sonuc:
        res = merdan.analiz_et(m)
        if res:
            if "BANKO MS" in res: r_ms += res
            elif "ELİT GOLLÜ" in res: r_gol += res
            else: r_kisir += res
            bulunan += 1

    # Raporu Gönder
    rapor = (f"✅ **TARAMA TAMAMLANDI!**\n\n"
             f"📊 **İstatistik:**\n"
             f"🔹 Taranan Toplam Maç: **{toplam}**\n"
             f"🔹 Senin Kriterlerine Uyan: **{bulunan}**\n"
             f"🔹 Elenen Maç Sayısı: **{toplam - bulunan}**")
    
    await msg.edit_text(rapor)

    if r_ms: await update.message.reply_text(f"🏆 **BANKO MS ADAYLARI**\n\n{r_ms[:4000]}", parse_mode='Markdown')
    if r_gol: await update.message.reply_text(f"🚀 **ELİT GOLLÜ MAÇLAR**\n\n{r_gol[:4000]}", parse_mode='Markdown')
    if r_kisir: await update.message.reply_text(f"🛡️ **ELİT KISIR MAÇLAR**\n\n{r_kisir[:4000]}", parse_mode='Markdown')
    
    if bulunan == 0:
        await update.message.reply_text("📭 Maalesef bugün senin o sert kriterlerine uyan elit bir maç çıkmadı.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Merdan Bot Yayında! Telegram'dan /start yazarak beyin fırtınasını başlat.")
    app.run_polling()

