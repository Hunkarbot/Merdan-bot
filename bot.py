import requests

API_KEY = "9d815aaf3a5947e681eda9a895a281b5"

BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

def test_api():
    print("API TEST BASLIYOR...")
    print("KEY:", API_KEY)

    r = requests.get(f"{BASE_URL}/status", headers=HEADERS)

    print("STATUS:", r.status_code)
    print("CEVAP:", r.text)

test_api()
