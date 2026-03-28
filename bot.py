import requests
import os

API_KEY = os.getenv("FOOTBALL_API_KEY")

url = "https://v3.football.api-sports.io/status"

headers = {
    "x-apisports-key": API_KEY
}

print("API_KEY:", API_KEY)
print("VAR MI:", bool(API_KEY))

response = requests.get(url, headers=headers)

print("STATUS CODE:", response.status_code)
print("RESPONSE:", response.text)
