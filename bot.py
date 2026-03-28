import requests
import os

API_KEY = os.getenv("FOOTBALL_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

print("API_KEY:", API_KEY)
print("BOT_TOKEN var mı:", bool(BOT_TOKEN))
print("CHAT_ID var mı:", bool(CHAT_ID))

url = "https://v3.football.api-sports.io/status"
headers = {
    "x-apisports-key": API_KEY
}

response = requests.get(url, headers=headers)

print("STATUS CODE:", response.status_code)
print("RESPONSE:", response.text)
