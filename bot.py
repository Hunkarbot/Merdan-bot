import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "8747036915:AAG9c4MRd6Fx-EDQOCpcxmFNGdRCAu995GE"
API_KEY = "db7395bc22c960b4acc60f71083c8f19"

# 🔥 TAKIM SON 5 MAÇ VERİSİ
def get_team_stats(team_id):
    url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=5"
    headers = {"x-apisports-key": API_KEY}

    response = requests.get(url, headers=headers)
    data = response.json()

    scored = 0
    conceded = 0
    btts = 0

    for m in data["response"]:
        home_id = m["teams"]["home"]["id"]
        away_id = m["teams"]["away"]["id"]

        hg = m["goals"]["home"]
        ag = m["goals"]["away"]

        if team_id == home_id:
            scored += hg
            conceded += ag
            if hg > 0 and ag > 0:
                btts += 1
        else:
            scored += ag
            conceded += hg
            if hg > 0 and ag > 0:
                btts += 1

    return {"scored": scored, "conceded": conceded, "btts": btts}


# 🚀 /maclar KOMUTU
async def maclar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    url = "https://v3.football.api-sports.io/fixtures?date=2026-03-23"
    headers = {"x-apisports-key": API_KEY}

    res = requests.get(url, headers=headers)
    data = res.json()

    matches = []

    for m in data["response"]:

        home = m["teams"]["home"]["name"]
        away = m["teams"]["away"]["name"]

        home_id = m["teams"]["home"]["id"]
        away_id = m["teams"]["away"]["id"]

        home_stats = get_team_stats(home_id)
        away_stats = get_team_stats(away_id)

        score = 0

        # 🔥 GOL GÜCÜ
        if home_stats["scored"] >= 7:
            score += 15
        if away_stats["scored"] >= 7:
            score += 15

        # 🔥 SAVUNMA
        if home_stats["conceded"] >= 5:
            score += 10
        if away_stats["conceded"] >= 5:
            score += 10

        # 🔥 BTTS
        if home_stats["btts"] >= 4 and away_stats["btts"] >= 4:
            score += 30

        # 🔥 OVER
        total_goals = home_stats["scored"] + away_stats["scored"]
        if total_goals >= 14:
            score += 20

        # 🎯 MARKET SEÇİMİ
        if home_stats["btts"] >= 4 and away_stats["btts"] >= 4:
            market = "BTTS"
        elif total_goals >= 14:
            market = "Over 2.5"
        else:
            market = "Favori"

        # 🧠 ANALİZ
        analysis = (
            f"- {home} son 5 maç gol: {home_stats['scored']}\n"
            f"- {away} son 5 maç gol: {away_stats['scored']}\n"
            f"- BTTS: {home_stats['btts']} & {away_stats['btts']}\n"
        )

        matches.append({
            "home": home,
            "away": away,
            "score": score,
            "market": market,
            "analysis": analysis
        })

    # 🔥 SIRALA
    matches = sorted(matches, key=lambda x: x["score"], reverse=True)

    # 🎯 90+ varsa al
    best = [m for m in matches if m["score"] >= 90]

    # 💣 yoksa en iyi 3
    if not best:
        best = matches[:3]

    # 📩 MESAJ
    msg = "🔥 BUGÜNÜN EN İYİ MAÇLARI\n\n"

    for m in best:
        msg += f"⚔️ {m['home']} vs {m['away']}\n"
        msg += f"Puan: {m['score']}/100\n\n"
        msg += "Analiz:\n"
        msg += m["analysis"] + "\n"
        msg += f"Öneri:\n👉 {m['market']}\n"
        msg += "----------------------\n\n"

    await update.message.reply_text(msg)


# 🚀 BOT START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot aktif kral ✅ /maclar yaz")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("maclar", maclar))

    print("Bot çalışıyor...")

    app.run_polling()


if __name__ == "__main__":
    main()
