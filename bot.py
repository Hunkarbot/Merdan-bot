8import requests
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TELEGRAM_TOKEN = "8747036915:AAHHheO6dgLnqCoc8YSFaQJUDmDZjN7rJo0"
FOOTBALL_API_KEY = "9d815aaf3a5947e681eda9a895a281b5"
class MerdanBeyin:
    def __init__(self):
        self.headers = {
            "x-apisports-key": FOOTBALL_API_KEY
        }
        self.tz = pytz.timezone("Europe/Berlin")

    def veri_cek(self):
        bugun = datetime.now(self.tz).strftime('%Y-%m-%d')
        url = "https://v3.football.api-sports.io/fixtures"

        try:
            res = requests.get(
                url,
                headers=self.headers,
                params={
                    "date": bugun,
                    "timezone": "Europe/Berlin"
                },
                timeout=10
            )

            # 🔥 DEBUG
            if res.status_code != 200:
                return f"HATA_STATUS_{res.status_code}"

            data = res.json()

            if "errors" in data and data["errors"]:
                return f"HATA_API_{data['errors']}"

            maclar = data.get("response", [])

            if not maclar:
                return "BOS_VERI"

            return maclar

        except Exception as e:
            return f"HATA_EXCEPTION_{str(e)}"


merdan = MerdanBeyin()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("📡 Almanya sistemi tarıyor...")

    sonuc = merdan.veri_cek()

    # 🔥 HATA YAKALAMA
    if isinstance(sonuc, str):

        if "HATA_STATUS" in sonuc:
            await msg.edit_text(f"❌ STATUS HATASI:\n{sonuc}")
            return

        if "HATA_API" in sonuc:
            await msg.edit_text(f"❌ API HATASI:\n{sonuc}")
            return

        if sonuc == "BOS_VERI":
            await msg.edit_text("⚠️ API çalışıyor ama bugün maç yok")
            return

        if "HATA_EXCEPTION" in sonuc:
            await msg.edit_text(f"❌ SİSTEM HATASI:\n{sonuc}")
            return

    # ✅ BAŞARILI
    toplam = len(sonuc)
    await msg.edit_text(f"✅ {toplam} maç bulundu")

    liste = ""
    for mac in sonuc[:20]:
        ev = mac["teams"]["home"]["name"]
        dep = mac["teams"]["away"]["name"]
        saat = datetime.fromisoformat(
            mac["fixture"]["date"].replace("Z", "+00:00")
        ).astimezone(merdan.tz).strftime("%H:%M")

        liste += f"{saat} | {ev} - {dep}\n"

    await update.message.reply_text(liste if liste else "Liste boş")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    print("BOT ALMANYA MODDA 🇩🇪")
    app.run_polling()

