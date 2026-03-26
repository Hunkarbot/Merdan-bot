import requests
import time
import datetime
import os

API_KEY = os.getenv("API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BASE_URL = "https://v3.football.api-sports.io"

headers = {
    "x-apisports-key": API_KEY
}

GOLLU_LIGLER = [
    "Eredivisie",
    "Bundesliga",
    "2. Bundesliga",
    "Pro League",
    "Super League",
    "Superliga",
    "Allsvenskan",
    "Eliteserien",
    "1. Liga",
    "Championship",
    "League One",
    "Süper Lig",
    "MLS",
    "A-League",
    "J-League",
    "K-League"
]

KISIR_LIGLER = [
    "Egyptian Premier League",
    "Botola Pro",
    "Ligue 1",
    "Tunisian Ligue 1",
    "Algerian Ligue 1",
    "Tanzania Premier League",
    "Ethiopia Premier League",
    "Kenya Premier League",
    "Super League Greece",
    "Liga I",
    "First League",
    "SuperLiga",
    "HNL",
    "PrvaLiga",
    "Primera Division",
    "Primera A",
    "Primera Nacional"
]

def send_telegram(message: str) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        print("BOT_TOKEN veya CHAT_ID eksik")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        requests.post(url, data=data, timeout=20)
    except Exception as e:
        print("Telegram gönderim hatası:", e)

def get_matches_by_date(match_date):
    url = f"{BASE_URL}/fixtures?date={match_date}"
    try:
        res = requests.get(url, headers=headers, timeout=20)
        data = res.json()
        return data.get("response", [])
    except Exception:
        return []

def get_last5(team_id):
    url = f"{BASE_URL}/fixtures?team={team_id}&last=5"
    try:
        time.sleep(1.1)
        res = requests.get(url, headers=headers, timeout=20)
        data = res.json()
        return data.get("response", [])
    except Exception:
        return []

def calc_team_stats(last_matches, team_id):
    played = 0
    scored_all = 0
    conceded_all = 0
    btts_count = 0
    over25_count = 0
    under25_count = 0
    wins = 0
    losses = 0
    scored_5of5 = True
    conceded_5of5 = True

    for m in last_matches:
        try:
            home_id = m["teams"]["home"]["id"]
            away_id = m["teams"]["away"]["id"]

            home_goals = m["goals"]["home"]
            away_goals = m["goals"]["away"]

            if home_goals is None or away_goals is None:
                continue

            if team_id == home_id:
                gf = home_goals
                ga = away_goals
                won = home_goals > away_goals
                lost = home_goals < away_goals
            elif team_id == away_id:
                gf = away_goals
                ga = home_goals
                won = away_goals > home_goals
                lost = away_goals < home_goals
            else:
                continue

            played += 1
            scored_all += gf
            conceded_all += ga

            if gf == 0:
                scored_5of5 = False
            if ga == 0:
                conceded_5of5 = False

            if gf > 0 and ga > 0:
                btts_count += 1

            if gf + ga > 2:
                over25_count += 1
            else:
                under25_count += 1

            if won:
                wins += 1
            if lost:
                losses += 1

        except Exception:
            continue

    if played == 0:
        return None

    return {
        "played": played,
        "avg_scored": round(scored_all / played, 2),
        "avg_conceded": round(conceded_all / played, 2),
        "btts_count": btts_count,
        "over25_count": over25_count,
        "under25_count": under25_count,
        "wins": wins,
        "losses": losses,
        "scored_5of5": scored_5of5 and played >= 5,
        "conceded_5of5": conceded_5of5 and played >= 5
    }

def is_gollu_lig(league_name):
    return any(x.lower() in league_name.lower() for x in GOLLU_LIGLER)

def is_kisir_lig(league_name):
    return any(x.lower() in league_name.lower() for x in KISIR_LIGLER)

def btts_ok(home_stats, away_stats, league_name):
    if not is_gollu_lig(league_name):
        return False, 0

    if not (
        home_stats["scored_5of5"] and
        away_stats["scored_5of5"] and
        home_stats["conceded_5of5"] and
        away_stats["conceded_5of5"]
    ):
        return False, 0

    if home_stats["avg_scored"] < 1.0 or away_stats["avg_scored"] < 1.0:
        return False, 0

    if home_stats["avg_conceded"] < 1.0 or away_stats["avg_conceded"] < 1.0:
        return False, 0

    score = 35
    score += home_stats["btts_count"] * 6
    score += away_stats["btts_count"] * 6
    score += int(home_stats["avg_scored"] * 5)
    score += int(away_stats["avg_scored"] * 5)
    score += int(home_stats["avg_conceded"] * 5)
    score += int(away_stats["avg_conceded"] * 5)

    return True, min(score, 100)

def over25_ok(home_stats, away_stats, league_name):
    if not is_gollu_lig(league_name):
        return False, 0

    if home_stats["over25_count"] < 4 or away_stats["over25_count"] < 4:
        return False, 0

    if home_stats["avg_scored"] < 1.5 or away_stats["avg_scored"] < 1.2:
        return False, 0

    if home_stats["avg_conceded"] < 1.0 and away_stats["avg_conceded"] < 1.0:
        return False, 0

    score = 30
    score += home_stats["over25_count"] * 7
    score += away_stats["over25_count"] * 7
    score += int(home_stats["avg_scored"] * 6)
    score += int(away_stats["avg_scored"] * 6)
    score += int(home_stats["avg_conceded"] * 4)
    score += int(away_stats["avg_conceded"] * 4)

    return True, min(score, 100)

def under25_ok(home_stats, away_stats, league_name):
    if not is_kisir_lig(league_name):
        return False, 0

    if home_stats["under25_count"] < 4 or away_stats["under25_count"] < 4:
        return False, 0

    if home_stats["avg_scored"] > 1.1 or away_stats["avg_scored"] > 1.1:
        return False, 0

    if home_stats["avg_conceded"] > 1.1 or away_stats["avg_conceded"] > 1.1:
        return False, 0

    score = 30
    score += home_stats["under25_count"] * 7
    score += away_stats["under25_count"] * 7
    score += int((1.2 - home_stats["avg_scored"]) * 10)
    score += int((1.2 - away_stats["avg_scored"]) * 10)

    return True, min(score, 100)

def ms_ok(home_stats, away_stats):
    if home_stats["wins"] < 4:
        return False, 0

    if away_stats["losses"] < 3:
        return False, 0

    if home_stats["avg_scored"] < 1.5:
        return False, 0

    if away_stats["avg_conceded"] < 1.2:
        return False, 0

    score = 35
    score += home_stats["wins"] * 8
    score += away_stats["losses"] * 8
    score += int(home_stats["avg_scored"] * 7)
    score += int(away_stats["avg_conceded"] * 7)

    return True, min(score, 100)

def analyze_match(match):
    try:
        fixture = match["fixture"]
        league = match["league"]
        teams = match["teams"]

        league_name = league["name"]
        home_name = teams["home"]["name"]
        away_name = teams["away"]["name"]
        home_id = teams["home"]["id"]
        away_id = teams["away"]["id"]
        match_time = fixture["date"]

        home_last5 = get_last5(home_id)
        away_last5 = get_last5(away_id)

        home_stats = calc_team_stats(home_last5, home_id)
        away_stats = calc_team_stats(away_last5, away_id)

        if not home_stats or not away_stats:
            return None

        result = {
            "match": f"{home_name} - {away_name}",
            "league": league_name,
            "time": match_time,
            "MS": None,
            "BTTS": None,
            "OVER25": None,
            "UNDER25": None
        }

        ms_pass, ms_score = ms_ok(home_stats, away_stats)
        if ms_pass:
            result["MS"] = ms_score

        btts_pass, btts_score = btts_ok(home_stats, away_stats, league_name)
        if btts_pass:
            result["BTTS"] = btts_score

        over_pass, over_score = over25_ok(home_stats, away_stats, league_name)
        if over_pass:
            result["OVER25"] = over_score

        under_pass, under_score = under25_ok(home_stats, away_stats, league_name)
        if under_pass:
            result["UNDER25"] = under_score

        return result

    except Exception:
        return None

def run_scan(match_date=None):
    if not match_date:
        match_date = datetime.date.today().strftime("%Y-%m-%d")

    matches = get_matches_by_date(match_date)

    ms_list = []
    btts_list = []
    over_list = []
    under_list = []

    for match in matches:
        analyzed = analyze_match(match)
        if not analyzed:
            continue

        if analyzed["MS"] is not None:
            ms_list.append(analyzed)

        if analyzed["BTTS"] is not None:
            btts_list.append(analyzed)

        if analyzed["OVER25"] is not None:
            over_list.append(analyzed)

        if analyzed["UNDER25"] is not None:
            under_list.append(analyzed)

    ms_list = sorted(ms_list, key=lambda x: x["MS"], reverse=True)[:5]
    btts_list = sorted(btts_list, key=lambda x: x["BTTS"], reverse=True)[:5]
    over_list = sorted(over_list, key=lambda x: x["OVER25"], reverse=True)[:5]
    under_list = sorted(under_list, key=lambda x: x["UNDER25"], reverse=True)[:5]

    return ms_list, btts_list, over_list, under_list

def format_results(ms_list, btts_list, over_list, under_list):
    message = "📊 GUNUN ANALIZI\n\n"

    message += "👑 MS ADAYLARI\n"
    if ms_list:
        for m in ms_list:
            message += f"- {m['match']} | {m['MS']}\n"
    else:
        message += "- Uygun mac yok\n"

    message += "\n🔥 BTTS ADAYLARI\n"
    if btts_list:
        for m in btts_list:
            message += f"- {m['match']} | {m['BTTS']}\n"
    else:
        message += "- Uygun mac yok\n"

    message += "\n⚽ 2.5 UST ADAYLARI\n"
    if over_list:
        for m in over_list:
            message += f"- {m['match']} | {m['OVER25']}\n"
    else:
        message += "- Uygun mac yok\n"

    message += "\n🧱 2.5 ALT ADAYLARI\n"
    if under_list:
        for m in under_list:
            message += f"- {m['match']} | {m['UNDER25']}\n"
    else:
        message += "- Uygun mac yok\n"

    return message

def main():
    if not API_KEY:
        print("API_KEY eksik")
        return

    ms_list, btts_list, over_list, under_list = run_scan()
    final_message = format_results(ms_list, btts_list, over_list, under_list)

    print(final_message)
    send_telegram(final_message)

if __name__ == "__main__":
    main()

