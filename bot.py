import requests
import os
import datetime

print("BOT BASLADI")

API_KEY = os.getenv("FOOTBALL_API_KEY")

BASE_URL = "https://api.football-data.org/v4"

HEADERS = {
    "X-Auth-Token": API_KEY
}

today = datetime.date.today()
future = today + datetime.timedelta(days=3)

url = f"{BASE_URL}/matches?dateFrom={today}&dateTo={future}"

res = requests.get(url, headers=HEADERS)

data = res.json()

print("STATUS:", res.status_code)
print("MAC SAYISI:", len(data.get("matches", [])))

for m in data.get("matches", [])[:10]:
    print(
        m["homeTeam"]["name"],
        "-",
        m["awayTeam"]["name"],
        "|",
        m["utcDate"]
    )
