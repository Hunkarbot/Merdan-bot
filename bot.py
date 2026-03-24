from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
from datetime import datetime

API_KEY = "9d815aaf3a5947e681eda9a895a281b5"
BOT_TOKEN = "8747036915:AAES-UKrjW3xU891kX9s36sNn5gdaNlgaz8"

BASE_URL = "https://v3.football.api-sports.io"

headers = {
    "x-apisports-key": API_KEY
}

# Gollü ligler
GOLLU_LIGLER = ["Eredivisie", "Bundesliga", "Belgium", "MLS", "A-League"]

# Son 5 maç verisi
def get_last5(team_id):
    url = f"{BASE_URL}/fixtures?team={team_id}&last=5"
    res = requests.get(url, headers=headers).json()
    return res.get("response", [])

# BTTS kontrol (5/5 kuralı)
def btts_kontrol(maclar):
    sayac = 0
    for mac in maclar:
        ev = mac["goals"]["home"]
        dep = mac["goals"]["away"]
        if ev > 0 and dep > 0:
            sayac += 1
    return sayac == 5

# ANALİZ
def analiz():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"{BASE_URL}/fixtures?date={today}"
    res = requests.get(url, headers=headers).json()
    maclar = res.get("response", [])

    secilen = []

    for mac in maclar:
        lig = mac["league"]["name"]

        if lig not in GOLLU_LIGLER:
            continue

        home = mac["teams"]["home"]
        away = mac["teams"]["away"]

        home_last5 = get_last5(home["id"])
        away_last5 = get_last5(away["id"])

        if len(home_last5) < 5 or len(away_last5) < 5:
            continue

        if btts_kontrol(home_last5) and btts_kontrol(away_last5):
            secilen.append(f"{home['name']} vs {away['name']}")

    return secilen

# /start KOMUTU
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Analiz yapılıyor...")

    maclar = analiz()

    if not maclar:
        await update.message.reply_text("❌ Uygun BTTS maçı bulunamadı")
        return

    mesaj = "🔥 BUGÜNÜN BTTS MAÇLARI:\n\n"
    for m in maclar:
        mesaj += f"• {m}\n"

    await update.message.reply_text(mesaj)

# BOT
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))

app.run_polling()
