import requests
import time

TOKEN = "8900618226:AAE1o5o_xH1eSG4jwz7vCksardv_7SISy8c"
CHAT_ID = "870512243"
last_update_id = 0

def send(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.get(url, params={"chat_id": CHAT_ID, "text": text})

print("Эхо-бот запущен")
send("Я живой! Напиши /status")

while True:
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    r = requests.get(url, params={"offset": last_update_id + 1, "timeout": 
10}).json()
    for upd in r.get("result", []):
        last_update_id = upd["update_id"]
        msg = upd.get("message", {})
        text = msg.get("text", "")
        if text:
            send(f"Ты написал: {text}")
    time.sleep(1)
