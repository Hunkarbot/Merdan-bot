import os
import requests
import datetime

API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")

headers = {
    "X-Auth-Token": API_KEY
}

def test_api():
    today = datetime.date.today().strftime("%Y-%m-%d")

    url = f"https://api.football-data.org/v4/matches?dateFrom={today}&dateTo={today}"

    print("URL:", url)

    r = requests.get(url, headers=headers)

    print("Status:", r.status_code)

    data = r.json()
    matches = data.get("matches", [])

    print("Toplam maç:", len(matches))

    if len(matches) > 0:
        m = matches[0]
        print("Örnek:",
              m["homeTeam"]["name"],
              "-",
              m["awayTeam"]["name"])

if __name__ == "__main__":
    test_api()
