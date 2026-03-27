import requests
import datetime
import os
import time
from zoneinfo import ZoneInfo

API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BASE_URL = "https://api.football-data.org/v4"

HEADERS = {
    "X-Auth-Token": API_KEY
}

BERLIN_TZ = ZoneInfo("Europe/Berlin")

# Aynı takımı tekrar tekrar çekmemek için cache
TEAM_CACHE = {}

# Sadece gollü ligler
GOLLU_LIGLER = {
    "Bundesliga",
    "2. Bundesliga",
    "Eredivisie",
    "Championship",
    "Primeira Liga",
    "Belgian Pro League",
    "Austrian Bundesliga",
    "Swiss Super League",
    "Super Lig",
    "Süper Lig",
    "Eliteserien",
    "Allsvenskan",
    "Danish Superliga"
}


def telegram_gonder(mesaj):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    # Telegram mesaj limiti için parçalama
    parcalar = []
    while len(mesaj) > 3900:
        kes = mesaj[:3900]
        son_satir = kes.rfind("\n")
        if son_satir == -1:
            son_satir = 3900
        parcalar.append(mesaj[:son_satir])
        mesaj = mesaj[son_satir:].lstrip()
    parcalar.append(mesaj)

    for parca in parcalar:
        data = {
            "chat_id": CHAT_ID,
            "text": parca
        }
        r = requests.post(url, data=data, timeout=30)
        print("TELEGRAM STATUS:", r.status_code)
        print("TELEGRAM CEVAP:", r.text)
        time.sleep(1)


def lig_uygun_mu(competition_name):
    return competition_name in GOLLU_LIGLER


def format_tarih_saat(utc_date_str):
    try:
        dt_utc = datetime.datetime.fromisoformat(utc_date_str.replace("Z", "+00:00"))
        dt_local = dt_utc.astimezone(BERLIN_TZ)
        return dt_local.strftime("%d-%m-%Y | %H:%M")
    except Exception:
        return utc_date_str


def maclari_cek():
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    url = f"{BASE_URL}/matches"
    params = {
        "dateFrom": today.strftime("%Y-%m-%d"),
        "dateTo": tomorrow.strftime("%Y-%m-%d")
    }

    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    print("MAC CEKME STATUS:", r.status_code)
    data = r.json()
    print("MAC SAYISI:", data.get("count", 0))
    return data.get("matches", [])


def takim_last5(team_id):
    if team_id in TEAM_CACHE:
        return TEAM_CACHE[team_id]

    url = f"{BASE_URL}/teams/{team_id}/matches"
    params = {
        "status": "FINISHED",
        "limit": 5
    }

    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    print(f"TEAM {team_id} STATUS:", r.status_code)
    data = r.json()

    matches = data.get("matches", [])
    TEAM_CACHE[team_id] = matches

    time.sleep(0.7)  # API dostu küçük bekleme
    return matches


def takim_formu(last_matches, team_name):
    scored = 0
    conceded = 0
    valid_matches = 0

    for m in last_matches:
        home = m.get("homeTeam", {}).get("name")
        away = m.get("awayTeam", {}).get("name")

        full = m.get("score", {}).get("fullTime", {})
        hg = full.get("home")
        ag = full.get("away")

        if hg is None or ag is None:
            continue

        if team_name == home:
            valid_matches += 1
            if hg > 0:
                scored += 1
            if ag > 0:
                conceded += 1

        elif team_name == away:
            valid_matches += 1
            if ag > 0:
                scored += 1
            if hg > 0:
                conceded += 1

    return {
        "valid": valid_matches,
        "scored": scored,
        "conceded": conceded
    }


def btts_puani(home_form, away_form):
    # 5 maç üstünden puan
    hs = home_form["scored"]
    hc = home_form["conceded"]
    as_ = away_form["scored"]
    ac = away_form["conceded"]

    # Ana mantık:
    # ev sahibi gol atar mı + yer mi
    # deplasman gol atar mı + yer mi
    toplam = hs + hc + as_ + ac   # max 20

    puan = int((toplam / 20) * 100)

    # 5/5 bonusları
    if hs == 5:
        puan += 5
    if hc == 5:
        puan += 5
    if as_ == 5:
        puan += 5
    if ac == 5:
        puan += 5

    if puan > 100:
        puan = 100

    return puan


def btts_aday_mi(home_form, away_form):
    # Daha güvenli filtre: iki takım da en az 4/5 gol atmış ve 4/5 gol yemiş olsun
    return (
        home_form["valid"] >= 5 and
        away_form["valid"] >= 5 and
        home_form["scored"] >= 4 and
        home_form["conceded"] >= 4 and
        away_form["scored"] >= 4 and
        away_form["conceded"] >= 4
    )


def main():
    if not API_KEY:
        print("FOOTBALL_DATA_API_KEY eksik")
        return

    if not BOT_TOKEN:
        print("BOT_TOKEN eksik")
        return

    if not CHAT_ID:
        print("CHAT_ID eksik")
        return

    matches = maclari_cek()

    adaylar = []

    for m in matches:
        try:
            status = m.get("status", "")
            if status not in ["SCHEDULED", "TIMED"]:
                continue

            competition = m.get("competition", {}).get("name", "")
            if not lig_uygun_mu(competition):
                continue

            home = m.get("homeTeam", {}).get("name", "Bilinmiyor")
            away = m.get("awayTeam", {}).get("name", "Bilinmiyor")
            home_id = m.get("homeTeam", {}).get("id")
            away_id = m.get("awayTeam", {}).get("id")
            utc_date = m.get("utcDate", "")

            if not home_id or not away_id:
                continue

            home_last = takim_last5(home_id)
            away_last = takim_last5(away_id)

            home_form = takim_formu(home_last, home)
            away_form = takim_formu(away_last, away)

            if not btts_aday_mi(home_form, away_form):
                continue

            puan = btts_puani(home_form, away_form)

            adaylar.append({
                "match": f"{home} - {away}",
                "competition": competition,
                "datetime": format_tarih_saat(utc_date),
                "score": puan,
                "home_stats": f"{home_form['scored']}/5 atar, {home_form['conceded']}/5 yer",
                "away_stats": f"{away_form['scored']}/5 atar, {away_form['conceded']}/5 yer"
            })

        except Exception as e:
            print("MAC ANALIZ HATASI:", e)
            continue

    adaylar = sorted(adaylar, key=lambda x: x["score"], reverse=True)

    mesaj = "🔥 BTTS ADAYLARI | GÜNDÜZ + GECE\n\n"

    if adaylar:
        for i, a in enumerate(adaylar[:10], start=1):
            mesaj += (
                f"{i}. {a['match']}\n"
                f"Lig: {a['competition']}\n"
                f"Tarih/Saat: {a['datetime']}\n"
                f"BTTS Puanı: {a['score']}/100\n"
                f"Ev: {a['home_stats']}\n"
                f"Dep: {a['away_stats']}\n\n"
            )
    else:
        mesaj += "Uygun BTTS maçı bulunamadı."

    print(mesaj)
    telegram_gonder(mesaj)


if __name__ == "__main__":
    main()
