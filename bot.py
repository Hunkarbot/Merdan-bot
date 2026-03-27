import os
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

API_KEY = "9d815aaf3a5947e681eda9a895a281b5"
BOT_TOKEN = os . getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY
}

TIMEZONE = "Europe/Berlin"

# BTTS için gollü ligler
GOLLU_LIG_KEYWORDS = [
    "eredivisie",
    "bundesliga",
    "2. bundesliga",
    "pro league",
    "superliga",
    "allsvenskan",
    "eliteserien",
    "mls",
    "a-league",
    "championship",
    "super league",
    "1. liga"
]

# Under 2.5 için kısır ligler
KISIR_LIG_KEYWORDS = [
    "botola",
    "algeria",
    "tunisia",
    "tanzania",
    "kenya",
    "ethiopia",
    "somalia",
    "burundi"
]

team_last5_cache = {}


# -------------------------
# TARİH / SAAT
# -------------------------
def get_local_now():
    return datetime.now(ZoneInfo(TIMEZONE))


def get_dates():
    now_local = get_local_now()
    today = now_local.date()
    tomorrow = today + timedelta(days=1)
    return today.strftime("%Y-%m-%d"), tomorrow.strftime("%Y-%m-%d")


TODAY_STR, TOMORROW_STR = get_dates()


def to_local_datetime_str(fixture_date_str):
    try:
        dt_utc = datetime.fromisoformat(fixture_date_str.replace("Z", "+00:00"))
        dt_local = dt_utc.astimezone(ZoneInfo(TIMEZONE))
        return dt_local.strftime("%Y-%m-%d"), dt_local.strftime("%H:%M")
    except Exception:
        return fixture_date_str[:10], fixture_date_str[11:16]


# -------------------------
# API
# -------------------------
def safe_get(endpoint, params=None, sleep_sec=0.9):
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=20)
        time.sleep(sleep_sec)  # API dostu bekleme
        response.raise_for_status()
        data = response.json()

        if data.get("errors"):
            print(f"API ERROR -> {data['errors']}")
            return []

        return data.get("response", [])
    except requests.exceptions.RequestException as e:
        print(f"REQUEST HATASI -> {endpoint} | {params} | {e}")
        return []
    except Exception as e:
        print(f"GENEL HATA -> {endpoint} | {params} | {e}")
        return []


def get_matches_by_date(date_str):
    return safe_get("fixtures", {"date": date_str}, sleep_sec=1.0)


def get_all_matches():
    matches_today = get_matches_by_date(TODAY_STR)
    matches_tomorrow = get_matches_by_date(TOMORROW_STR)
    print(f"BUGÜN MAÇ: {len(matches_today)} | YARIN MAÇ: {len(matches_tomorrow)}")
    return matches_today + matches_tomorrow


def get_team_last5(team_id):
    if team_id in team_last5_cache:
        return team_last5_cache[team_id]

    matches = safe_get("fixtures", {"team": team_id, "last": 5}, sleep_sec=1.0)
    team_last5_cache[team_id] = matches
    return matches


# -------------------------
# LİG KONTROL
# -------------------------
def normalize_text(text):
    return str(text).strip().lower()


def is_gollu_lig(league_name):
    league_name = normalize_text(league_name)
    return any(k in league_name for k in GOLLU_LIG_KEYWORDS)


def is_kisir_lig(league_name):
    league_name = normalize_text(league_name)
    return any(k in league_name for k in KISIR_LIG_KEYWORDS)


# -------------------------
# TAKIM SAYAÇLARI
# -------------------------
def count_scored(matches, team_id):
    count = 0
    for m in matches:
        try:
            if m["teams"]["home"]["id"] == team_id:
                goals = m["goals"]["home"]
            elif m["teams"]["away"]["id"] == team_id:
                goals = m["goals"]["away"]
            else:
                continue

            if goals is not None and goals > 0:
                count += 1
        except Exception:
            continue
    return count


def count_conceded(matches, team_id):
    count = 0
    for m in matches:
        try:
            if m["teams"]["home"]["id"] == team_id:
                opp_goals = m["goals"]["away"]
            elif m["teams"]["away"]["id"] == team_id:
                opp_goals = m["goals"]["home"]
            else:
                continue

            if opp_goals is not None and opp_goals > 0:
                count += 1
        except Exception:
            continue
    return count


def count_under25(matches):
    count = 0
    for m in matches:
        try:
            h = m["goals"]["home"]
            a = m["goals"]["away"]
            if h is not None and a is not None and (h + a) <= 2:
                count += 1
        except Exception:
            continue
    return count


# -------------------------
# BTTS
# 4/5 ana filtre, 3/5 fallback
# -------------------------
def is_btts_candidate(home_last5, away_last5, home_id, away_id, strict_level=4):
    home_scored = count_scored(home_last5, home_id)
    home_conceded = count_conceded(home_last5, home_id)
    away_scored = count_scored(away_last5, away_id)
    away_conceded = count_conceded(away_last5, away_id)

    return (
        home_scored >= strict_level and
        home_conceded >= strict_level and
        away_scored >= strict_level and
        away_conceded >= strict_level
    )


def calc_btts_score(home_last5, away_last5, home_id, away_id):
    home_scored = count_scored(home_last5, home_id)
    home_conceded = count_conceded(home_last5, home_id)
    away_scored = count_scored(away_last5, away_id)
    away_conceded = count_conceded(away_last5, away_id)

    return home_scored + home_conceded + away_scored + away_conceded


# -------------------------
# UNDER 2.5
# 4/5 ana filtre, 3/5 fallback
# -------------------------
def is_under25_candidate(home_last5, away_last5, home_id, away_id, strict_under=4, strict_goal_cap=2):
    home_scored = count_scored(home_last5, home_id)
    home_conceded = count_conceded(home_last5, home_id)
    away_scored = count_scored(away_last5, away_id)
    away_conceded = count_conceded(away_last5, away_id)

    home_under = count_under25(home_last5)
    away_under = count_under25(away_last5)

    return (
        home_scored <= strict_goal_cap and
        away_scored <= strict_goal_cap and
        home_conceded <= strict_goal_cap and
        away_conceded <= strict_goal_cap and
        home_under >= strict_under and
        away_under >= strict_under
    )


def calc_under_score(home_last5, away_last5, home_id, away_id):
    home_scored = count_scored(home_last5, home_id)
    home_conceded = count_conceded(home_last5, home_id)
    away_scored = count_scored(away_last5, away_id)
    away_conceded = count_conceded(away_last5, away_id)

    home_under = count_under25(home_last5)
    away_under = count_under25(away_last5)

    score = 0
    score += (5 - home_scored)
    score += (5 - away_scored)
    score += (5 - home_conceded)
    score += (5 - away_conceded)
    score += home_under
    score += away_under
    return score


# -------------------------
# SİSTEM PUANI
# -------------------------
def calc_system_score(total_analyzed, total_selected):
    if total_analyzed <= 0:
        return 0, 0.0

    hit_rate = (total_selected / total_analyzed) * 100

    if hit_rate <= 5:
        system_score = 90
    elif hit_rate <= 10:
        system_score = 100
    elif hit_rate <= 20:
        system_score = 80
    else:
        system_score = 60

    return system_score, hit_rate


# -------------------------
# ANALİZ
# -------------------------
def analyze_matches():
    fixtures = get_all_matches()
    print(f"TOPLAM ÇEKİLEN MAÇ: {len(fixtures)}")

    btts_fixtures = []
    under_fixtures = []
    needed_team_ids = set()

    for match in fixtures:
        try:
            league_name = match["league"]["name"]
            home_id = match["teams"]["home"]["id"]
            away_id = match["teams"]["away"]["id"]

            if is_gollu_lig(league_name):
                btts_fixtures.append(match)
                needed_team_ids.add(home_id)
                needed_team_ids.add(away_id)

            elif is_kisir_lig(league_name):
                under_fixtures.append(match)
                needed_team_ids.add(home_id)
                needed_team_ids.add(away_id)

        except Exception:
            continue

    print(f"BTTS İÇİN BAKILAN MAÇ: {len(btts_fixtures)}")
    print(f"UNDER İÇİN BAKILAN MAÇ: {len(under_fixtures)}")
    print(f"SON 5 ÇEKİLECEK TAKIM SAYISI: {len(needed_team_ids)}")

    for team_id in needed_team_ids:
        get_team_last5(team_id)

    btts_candidates = []
    under_candidates = []

    # SADECE GOLLÜ LİGLERDEN BTTS
    for match in btts_fixtures:
        try:
            league_name = match["league"]["name"]
            home_team = match["teams"]["home"]["name"]
            away_team = match["teams"]["away"]["name"]
            home_id = match["teams"]["home"]["id"]
            away_id = match["teams"]["away"]["id"]

            fixture_date = match["fixture"]["date"]
            match_day, match_time = to_local_datetime_str(fixture_date)

            home_last5 = team_last5_cache.get(home_id, [])
            away_last5 = team_last5_cache.get(away_id, [])

            if len(home_last5) < 5 or len(away_last5) < 5:
                continue

            if is_btts_candidate(home_last5, away_last5, home_id, away_id, strict_level=4):
                score = calc_btts_score(home_last5, away_last5, home_id, away_id)
                btts_candidates.append({
                    "score": score,
                    "text": f"{match_day} {match_time} - {home_team} vs {away_team} | {league_name} | BTTS YES"
                })

        except Exception as e:
            print(f"BTTS ANALİZ HATASI -> {e}")
            continue

    # BTTS fallback
    if not btts_candidates:
        print("BTTS fallback 3/5 çalıştı")
        for match in btts_fixtures:
            try:
                league_name = match["league"]["name"]
                home_team = match["teams"]["home"]["name"]
                away_team = match["teams"]["away"]["name"]
                home_id = match["teams"]["home"]["id"]
                away_id = match["teams"]["away"]["id"]

                fixture_date = match["fixture"]["date"]
                match_day, match_time = to_local_datetime_str(fixture_date)

                home_last5 = team_last5_cache.get(home_id, [])
                away_last5 = team_last5_cache.get(away_id, [])

                if len(home_last5) < 5 or len(away_last5) < 5:
                    continue

                if is_btts_candidate(home_last5, away_last5, home_id, away_id, strict_level=3):
                    score = calc_btts_score(home_last5, away_last5, home_id, away_id)
                    btts_candidates.append({
                        "score": score,
                        "text": f"{match_day} {match_time} - {home_team} vs {away_team} | {league_name} | BTTS YES (fallback 3/5)"
                    })

            except Exception:
                continue

    # SADECE KISIR LİGLERDEN UNDER
    for match in under_fixtures:
        try:
            league_name = match["league"]["name"]
            home_team = match["teams"]["home"]["name"]
            away_team = match["teams"]["away"]["name"]
            home_id = match["teams"]["home"]["id"]
            away_id = match["teams"]["away"]["id"]

            fixture_date = match["fixture"]["date"]
            match_day, match_time = to_local_datetime_str(fixture_date)

            home_last5 = team_last5_cache.get(home_id, [])
            away_last5 = team_last5_cache.get(away_id, [])

            if len(home_last5) < 5 or len(away_last5) < 5:
                continue

            if is_under25_candidate(home_last5, away_last5, home_id, away_id, strict_under=4, strict_goal_cap=2):
                score = calc_under_score(home_last5, away_last5, home_id, away_id)
                under_candidates.append({
                    "score": score,
                    "text": f"{match_day} {match_time} - {home_team} vs {away_team} | {league_name} | UNDER 2.5"
                })

        except Exception as e:
            print(f"UNDER ANALİZ HATASI -> {e}")
            continue

    # UNDER fallback
    if not under_candidates:
        print("UNDER fallback 3/5 çalıştı")
        for match in under_fixtures:
            try:
                league_name = match["league"]["name"]
                home_team = match["teams"]["home"]["name"]
                away_team = match["teams"]["away"]["name"]
                home_id = match["teams"]["home"]["id"]
                away_id = match["teams"]["away"]["id"]

                fixture_date = match["fixture"]["date"]
                match_day, match_time = to_local_datetime_str(fixture_date)

                home_last5 = team_last5_cache.get(home_id, [])
                away_last5 = team_last5_cache.get(away_id, [])

                if len(home_last5) < 5 or len(away_last5) < 5:
                    continue

                if is_under25_candidate(home_last5, away_last5, home_id, away_id, strict_under=3, strict_goal_cap=3):
                    score = calc_under_score(home_last5, away_last5, home_id, away_id)
                    under_candidates.append({
                        "score": score,
                        "text": f"{match_day} {match_time} - {home_team} vs {away_team} | {league_name} | UNDER 2.5 (fallback 3/5)"
                    })

            except Exception:
                continue

    btts_candidates.sort(key=lambda x: x["score"], reverse=True)
    under_candidates.sort(key=lambda x: x["score"], reverse=True)

    total_analyzed = len(btts_fixtures) + len(under_fixtures)
    total_selected = len(btts_candidates) + len(under_candidates)
    system_score, hit_rate = calc_system_score(total_analyzed, total_selected)

    print(f"TOPLAM BAKILAN MAÇ: {total_analyzed}")
    print(f"TOPLAM VERİLEN MAÇ: {total_selected}")
    print(f"BTTS VERİLEN: {len(btts_candidates)}")
    print(f"UNDER VERİLEN: {len(under_candidates)}")
    print(f"HIT RATE: %{hit_rate:.2f}")
    print(f"SİSTEM PUANI: {system_score}/100")

    top_btts = btts_candidates[:5]
    top_under = under_candidates[:5]

    stats = {
        "total_fixtures_api": len(fixtures),
        "btts_analyzed": len(btts_fixtures),
        "under_analyzed": len(under_fixtures),
        "total_analyzed": total_analyzed,
        "btts_selected": len(btts_candidates),
        "under_selected": len(under_candidates),
        "total_selected": total_selected,
        "hit_rate": hit_rate,
        "system_score": system_score
    }

    return top_btts, top_under, stats


# -------------------------
# TELEGRAM
# -------------------------
def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("BOT_TOKEN veya CHAT_ID eksik")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        response = requests.post(url, data=payload, timeout=20)
        response.raise_for_status()
        print("Telegram mesajı gönderildi.")
    except Exception as e:
        print(f"TELEGRAM HATASI -> {e}")


def build_message(top_btts, top_under, stats):
    now_str = get_local_now().strftime("%Y-%m-%d %H:%M")

    msg = ""
    msg += f"🔥 HÜNKAR BOT 🔥\n"
    msg += f"⏰ Tarama Zamanı: {now_str} ({TIMEZONE})\n"
    msg += f"📅 Tarih Aralığı: {TODAY_STR} + {TOMORROW_STR}\n\n"

    msg += "📊 SİSTEM RAPORU:\n"
    msg += f"API'den Çekilen Toplam Maç: {stats['total_fixtures_api']}\n"
    msg += f"Bakılan BTTS Maçı: {stats['btts_analyzed']}\n"
    msg += f"Bakılan Kısır Lig Maçı: {stats['under_analyzed']}\n"
    msg += f"Toplam Bakılan Maç: {stats['total_analyzed']}\n"
    msg += f"Toplam Verilen Maç: {stats['total_selected']}\n"
    msg += f"Hit Rate: %{stats['hit_rate']:.2f}\n"
    msg += f"Sistem Gücü: {stats['system_score']}/100\n\n"

    if top_btts:
        msg += "🟩 BTTS ADAYLARI:\n"
        for i, item in enumerate(top_btts, 1):
            msg += f"{i}) {item['text']}\n"
        msg += "\n"
    else:
        msg += "🟩 BTTS uygun maç yok\n\n"

    if top_under:
        msg += "🟥 KISIR LİGLER / UNDER 2.5:\n"
        for i, item in enumerate(top_under, 1):
            msg += f"{i}) {item['text']}\n"
    else:
        msg += "🟥 Kısır liglerde uygun maç yok"

    return msg


# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":
    if not API_KEY:
        print("API_KEY eksik")
    else:
        top_btts, top_under, stats = analyze_matches()
        final_message = build_message(top_btts, top_under, stats)
        print(final_message)
        send_telegram(final_message)
