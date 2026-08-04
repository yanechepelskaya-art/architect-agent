import requests, sqlite3, json, time, os, threading
from datetime import datetime, timedelta
from openpyxl import Workbook
import ccxt

TOKEN = "8900618226:AAGPVlCFCNSMiDYrv3DkUbeWorQWrdYti0Q"
CHAT_ID = "870512243"
CHANNEL_ID = "-1003920623687"

exchange = ccxt.okx()
last_phase = "📊 Боковик"

def send_tg(text, reply_markup=None, to_channel=False):
    target = CHANNEL_ID if to_channel else CHAT_ID
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": target, "text": text}, timeout=5)
    except:
        pass

def get_price(symbol):
    try:
        ticker = exchange.fetch_ticker(f"{symbol}/USDT")
        return ticker["last"]
    except Exception as e:
        print(f"send_tg error: {e}")
        return None

send_tg("🚀 Агент запущен. Отправь /start")

def process_updates():
    global last_phase, last_update_id
    try:
        r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params={"offset": last_update_id + 1, "timeout": 5}, timeout=10)
        for upd in r.json().get("result", []):
            last_update_id = upd["update_id"]
            t = upd.get("message", {}).get("text", "")
            print(f"GOT: [{t}] len={len(t)}")
            if True:  # Временно все команды -> Привет
                p = get_price("BTC")
                p_str = f"₿ BTC: ${p:,.2f}" if p else ""
                send_tg(f"👋 Привет! Я агент Архитектора.\n{p_str}")
            elif t in ["/btc", "₿ BTC"]:
                p = get_price("BTC")
                send_tg(f"₿ BTC: ${p:,.2f}" if p else "Нет данных")
            else:
                send_tg(f"Команда: {t}\nИспользуй /start или /btc")
    except Exception as e:
        print(f"send_tg error: {e}")
        pass

last_update_id = 0
# Сбрасываем старые обновления
r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params={"offset": -1, "timeout": 1}, timeout=5)
results = r.json().get("result", [])
if results:
    last_update_id = results[-1]["update_id"]

send_tg("✅ Готов к работе. /start")

while True:
    process_updates()
    time.sleep(0.5)
