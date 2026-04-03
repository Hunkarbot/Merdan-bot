import os
import time
import logging
import requests

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# =========================
# AYARLAR
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY
}

# Gollü / uygun gördüğün ligler
LEAGUES = [
    39,   # Premier League
    78,   # Bundesliga
    140,  # La Liga
    135,  # Serie A
    61,   # Ligue 1
    94,   # Primeira Liga
    88,   # Eredivisie
    203,  # Championship
]

# Sadece yaklaşan maçlar
VALID_STATUSES = {"NS", "TBD", "TIMED", "SCHEDULED"}

# API dostu limitler
MAX_MATCHES_TO_ANALYZE = 12     # /btts için en fazla kaç maç analiz edilsin
REQUEST_SLEEP = 0.7             # istekler arası bekleme
RETRY_429_SLEEP = 2.5           # 429 olursa bekleme
HTTP_TIMEOUT = 20

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

session = requests.Session()
session.headers.update(HEADERS)


# =========================
# YARDIMCI
# =========================
def safe_get(endpoint: str, params: dict | None = None, retries: int = 2):
    """
    API dostu GET.
    429 olursa kısa bekleyip tekrar dener.
    """
    url = f"{BASE_URL}{endpoint}"

    for attempt in range(retries + 1):
        try:
            resp = session.get(url, params=params, timeout=HTTP_TIMEOUT)

            if resp.status_code == 429:
                if attempt < retries:
                    time.sleep(RETRY_429_SLEEP)
                    continue
                return None, "HTTP 429"

            resp.raise_for_status()
            return resp.json(), None

        except requests.RequestException as e:
            if attempt < retries:
                time.sleep(1.5)
                continue
            return None, str(e)

    return None, "Bilinmeyen hata"


def format_match_time(fixture: dict) -> tuple[str, str]:
    """
    API-Sports fixture date -> DD.MM ve HH:MM
    UTC döner; çok sorun değil, önce sistemi oturtalım.
    """
    date_str = fixture.get("date", "")
    if len(date_str) >= 16:
        tarih = f"{date_str[8:10]}.{date_str[5:7]}"
        saat = date_str[11:16]
        return tarih, saat
    return "--.--", "--:--"


def get_fixtures_by_date_and_league(target_date: str, league_id: int):
    """
    Belirli tarih + lig için maçlar.
    """
    data, err = safe_get("/fixtures", params={
        "date": target_date,
        "league": league_id,
        "season": 2025 if target_date.startswith("2025") else 2026
    })

    if err:
        return [], err

    return data.get("response", []), None


def get_upcoming_matches():
    """
    Bugün + yarın maçları çeker.
    """
    from datetime import datetime, timedelta

    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)

    dates = [today.isoformat(), tomorrow.isoformat()]

    all_matches = []
    errors = []

    for d in dates:
        for league_id in LEAGUES:
            fixtures, err = get_fixtures_by_date_and_league(d, league_id)

            if err:
                errors.append(f"- Lig {league_id}: {err}")
                time.sleep(REQUEST_SLEEP)
                continue

            for item in fixtures:
                fixture = item.get("fixture", {})
                league = item.get("league", {})
                teams = item.get("teams", {})

                status_short = fixture.get("status", {}).get("short", "")
                if status_short not in VALID_STATUSES:
                    continue

                tarih, saat = format_match_time(fixture)

                all_matches.append({
                    "fixture_id": fixture.get("id"),
                    "league_id": league.get("id"),
                    "league_name": league.get("name", "Lig"),
                    "date": tarih,
                    "time": saat,
                    "status": status_short,
                    "home_id": teams.get("home", {}).get("id"),
                    "home_name": teams.get("home", {}).get("name", "Ev Sahibi"),
                    "away_id": teams.get("away", {}).get("id"),
                    "away_name": teams.get("away", {}).get("name", "Deplasman"),
                })

            time.sleep(REQUEST_SLEEP)

    # aynı fixture birkaç kez gelmesin
    uniq = {}
    for m in all_matches:
        uniq[m["fixture_id"]] = m

    sorted_matches = sorted(
        uniq.values(),
        key=lambda x: (x["date"], x["time"], x["league_name"], x["home_name"])
    )

    return sorted_matches, errors


def get_last_five_matches(team_id: int):
    """
    Takımın son 5 maçını alır.
    """
    data, err = safe_get("/fixtures", params={
        "team": team_id,
        "last": 5
    })

    if err:
        return [], err

    return data.get("response", []), None


def takim_form_analizi(son_maclar: list, takim_id: int):
    """
    Son 5 maçta:
    - kaçında gol attı?
    - kaçında gol yedi?
    """
    atti = 0
    yedi = 0
    toplam = 0

    for mac in son_maclar:
        try:
            teams = mac.get("teams", {})
            goals = mac.get("goals", {})

            home = teams.get("home", {})
            away = teams.get("away", {})

            home_id = home.get("id")
            away_id = away.get("id")

            home_goals = goals.get("home")
            away_goals = goals.get("away")

            if home_goals is None or away_goals is None:
                continue

            if takim_id == home_id:
                kendi_gol = home_goals
                rakip_gol = away_goals
            elif takim_id == away_id:
                kendi_gol = away_goals
                rakip_gol = home_goals
            else:
                continue

            toplam += 1

            if kendi_gol > 0:
                atti += 1
            if rakip_gol > 0:
                yedi += 1

        except Exception:
            continue

    return {
        "oynanan": toplam,
        "atti": atti,
        "yedi": yedi,
        "atti_oran": round(atti / toplam, 2) if toplam else 0,
        "yedi_oran": round(yedi / toplam, 2) if toplam else 0,
    }


def btts_atti_yedi_sistemi(ev_form: dict, dep_form: dict):
    """
    Ana sistem:
    A atar mı?
    A yer mi?
    B atar mı?
    B yer mi?
    """
    skor = 0
    nedenler = []

    # Ev atar mı?
    if ev_form["atti"] >= 4:
        skor += 25
        nedenler.append(f"Ev sahibi son 5 maçta {ev_form['atti']}/5 gol atmış")
    elif ev_form["atti"] == 3:
        skor += 10
        nedenler.append("Ev sahibi gol bulma gücü orta")

    # Ev yer mi?
    if ev_form["yedi"] >= 4:
        skor += 25
        nedenler.append(f"Ev sahibi son 5 maçta {ev_form['yedi']}/5 gol yemiş")
    elif ev_form["yedi"] == 3:
        skor += 10
        nedenler.append("Ev sahibi gol yeme riski orta")

    # Dep atar mı?
    if dep_form["atti"] >= 4:
        skor += 25
        nedenler.append(f"Deplasman son 5 maçta {dep_form['atti']}/5 gol atmış")
    elif dep_form["atti"] == 3:
        skor += 10
        nedenler.append("Deplasman gol bulma gücü orta")

    # Dep yer mi?
    if dep_form["yedi"] >= 4:
        skor += 25
        nedenler.append(f"Deplasman son 5 maçta {dep_form['yedi']}/5 gol yemiş")
    elif dep_form["yedi"] == 3:
        skor += 10
        nedenler.append("Deplasman gol yeme riski orta")

    # Sert filtre
    uygun_mu = (
        ev_form["atti"] >= 4 and
        ev_form["yedi"] >= 4 and
        dep_form["atti"] >= 4 and
        dep_form["yedi"] >= 4
    )

    return {
        "btts_skor": skor,
        "uygun_mu": uygun_mu,
        "nedenler": nedenler
    }


def mac_btts_analiz(match_item: dict):
    """
    Tek maç için son 5 + attı mı yedi mi analizi
    """
    ev_id = match_item["home_id"]
    dep_id = match_item["away_id"]

    ev_son5, ev_err = get_last_five_matches(ev_id)
    time.sleep(REQUEST_SLEEP)

    dep_son5, dep_err = get_last_five_matches(dep_id)
    time.sleep(REQUEST_SLEEP)

    if ev_err or dep_err:
        return {
            "mac": f"{match_item['home_name']} - {match_item['away_name']}",
            "hata": f"Ev hata: {ev_err or '-'} | Dep hata: {dep_err or '-'}"
        }

    ev_form = takim_form_analizi(ev_son5, ev_id)
    dep_form = takim_form_analizi(dep_son5, dep_id)
    sistem = btts_atti_yedi_sistemi(ev_form, dep_form)

    return {
        "mac": f"{match_item['home_name']} - {match_item['away_name']}",
        "lig": match_item["league_name"],
        "saat": f"{match_item['date']} {match_item['time']}",
        "ev_form": ev_form,
        "dep_form": dep_form,
        "btts_skor": sistem["btts_skor"],
        "btts_aday": sistem["uygun_mu"],
        "nedenler": sistem["nedenler"],
        "hata": None
    }


def btts_mesaj_olustur(analizlar: list):
    """
    Telegram için kısa ve temiz çıktı
    """
    adaylar = [a for a in analizlar if not a.get("hata") and a.get("btts_aday")]
    adaylar = sorted(adaylar, key=lambda x: x["btts_skor"], reverse=True)

    if not adaylar:
        return "❌ Uygun BTTS adayı çıkmadı."

    lines = ["🔥 ATTİ MI / YEDİ Mİ BTTS ADAYLARI", ""]

    for a in adaylar[:8]:
        lines.append(f"⚽ {a['mac']}")
        lines.append(f"Lig: {a['lig']} | Saat: {a['saat']}")
        lines.append(f"Skor: {a['btts_skor']}/100")
        lines.append(
            f"Ev: attı {a['ev_form']['atti']}/5 | yedi {a['ev_form']['yedi']}/5"
        )
        lines.append(
            f"Dep: attı {a['dep_form']['atti']}/5 | yedi {a['dep_form']['yedi']}/5"
        )
        lines.append("✅ BTTS adayı")
        lines.append("")

    return "\n".join(lines).strip()


# =========================
# TELEGRAM KOMUTLARI
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Hünkar bot hazır.\n\n"
        "Komutlar:\n"
        "/test - bot çalışıyor mu\n"
        "/maclar - yaklaşan maçlar\n"
        "/btts - attı mı yedi mi BTTS adayları"
    )


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot çalışıyor kral.")


async def maclar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Maçlar hazırlanıyor...")

    matches, errors = get_upcoming_matches()

    if not matches:
        mesaj = "⚠️ Yaklaşan maç bulunamadı."
        if errors:
            mesaj += "\n\n⚠️ Hatalar:\n" + "\n".join(errors[:10])
        await update.message.reply_text(mesaj)
        return

    lines = [f"✅ Toplam {len(matches)} yaklaşan maç bulundu", ""]

    for m in matches[:35]:
        lines.append(
            f"{m['date']} {m['time']} | {m['league_name']} | "
            f"{m['home_name']} - {m['away_name']} | {m['status']}"
        )

    if errors:
        lines.append("")
        lines.append("⚠️ Bazı liglerde hata oldu:")
        lines.extend(errors[:10])

    await update.message.reply_text("\n".join(lines))


async def btts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Attı mı yedi mi sistemi çalışıyor...")

    matches, errors = get_upcoming_matches()

    if not matches:
        mesaj = "⚠️ Analiz için yaklaşan maç bulunamadı."
        if errors:
            mesaj += "\n\n⚠️ Hatalar:\n" + "\n".join(errors[:10])
        await update.message.reply_text(mesaj)
        return

    analizlar = []
    scan_list = matches[:MAX_MATCHES_TO_ANALYZE]

    for match_item in scan_list:
        analiz = mac_btts_analiz(match_item)
        analizlar.append(analiz)

    mesaj = btts_mesaj_olustur(analizlar)

    hata_olanlar = [a for a in analizlar if a.get("hata")]
    if hata_olanlar:
        mesaj += "\n\n⚠️ Analiz hataları:"
        for h in hata_olanlar[:5]:
            mesaj += f"\n- {h['mac']}: {h['hata']}"

    await update.message.reply_text(mesaj)


# =========================
# MAIN
# =========================
def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN yok")
    if not API_KEY:
        raise ValueError("API_KEY yok")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("maclar", maclar))
    app.add_handler(CommandHandler("btts", btts))

    app.run_polling()


if __name__ == "__main__":
    main()
