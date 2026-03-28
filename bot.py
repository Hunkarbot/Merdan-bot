import requests
import os

API_KEY = os.getenv("FOOTBALL_API_KEY")

BASE_URL = "https://api.football-data.org/v4"

HEADERS = {
    "X-Auth-Token": API_KEY
}

url = f"{BASE_URL}/matches"

res = requests.get(url, headers=HEADERS)

print("STATUS:", res.status_code)
print("DATA:", res.text[:500])
