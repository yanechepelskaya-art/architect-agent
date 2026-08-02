
from flask import Flask
import requests
import sqlite3
from datetime import datetime

app = Flask(__name__)

PORTFOLIO = {
    "BTC": {"entry": 61900, "stop": 59500, "target": 68000, "amount": 0.01},
    "ETH": {"entry": 1550, "stop": 1450, "target": 2000, "amount": 0.1},
    "SOL": {"entry": 55, "stop": 48, "target": 82, "amount": 1.0},
    "WLD": {"entry": 0.60, "stop": 0.50, "target": 0.70, "amount": 100},
    "DOGE": {"entry": 0.069, "stop": 0.060, "target": 0.085, "amount": 1000},
    "XRP": {"entry": 1.05, "stop": 0.90, "target": 1.30, "amount": 100},
    "SUI": {"entry": 0.68, "stop": 0.55, "target": 0.90, "amount": 50},
    "RENDER": {"entry": 1.42, "stop": 1.20, "target": 1.80, "amount": 50}
}

prev_price = None
prev_vol = None
last_phase = "Загрузка..."
sensor_state = "⚪ Загрузка..."
history = []

def get_market_data(symbol="BTC"):
    try:
        url = f"https://www.okx.com/api/v5/market/ticker?instId={symbol}-USDT"
        r = requests.get(url, timeout=5)
        d = r.json()
        return float(d["data"][0]["last"]), float(d["data"][0]["vol24h"])
    except:
        return None, None

def get_price(symbol):
    p, _ = get_market_data(symbol)
    return p

def get_signals():
    try:
        conn = sqlite3.connect("/Users/yananechepelskaya/Desktop/paper_trades.db")
        c = conn.cursor()
        c.execute("SELECT timestamp, coin, action, price, pnl, reason FROM trades ORDER BY id DESC LIMIT 5")
        rows = c.fetchall()
        conn.close()
        return rows
    except:
        return []

def get_paper_stats():
    try:
        conn = sqlite3.connect("/Users/yananechepelskaya/Desktop/paper_trades.db")
        c = conn.cursor()
        c.execute("SELECT SUM(pnl) FROM trades WHERE pnl IS NOT NULL")
        total_pnl = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM trades")
        total_trades = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM trades WHERE pnl > 0")
        wins = c.fetchone()[0]
        conn.close()
        paper_balance = 10000.0 + total_pnl
        winrate = (wins / total_trades * 100) if total_trades > 0 else 0
        return paper_balance, total_pnl, total_trades, winrate
    except:
        return 10000.0, 0, 0, 0

@app.route("/")
def index():
    global prev_price, prev_vol, last_phase, sensor_state, history

    p, v = get_market_data("BTC")

    if p and prev_price:
        ch = (p - prev_price) / prev_price * 100
        if ch > 0.5 and v and v > prev_vol:
            sensor_state = "🟢 ЛЁГКОСТЬ — рост на объёме"
        elif ch > 0.5:
            sensor_state = "🟡 ТЯЖЕСТЬ — рост без объёма"
        elif ch < -0.5 and v and v > prev_vol:
            sensor_state = "🔴 ТЯЖЕСТЬ — падение на объёме"
        elif ch < -0.5:
            sensor_state = "🟢 ЛЁГКОСТЬ — падение без объёма"
        else:
            sensor_state = "⚪ НЕЙТРАЛЬНО — рынок в боковике"

        if p > prev_price:
            last_phase = "📈 Эманация (рост)"
        elif p < prev_price:
            last_phase = "📉 Сжатие (коррекция)"
        else:
            last_phase = "📊 Боковик"

    if p:
        prev_price = p
        prev_vol = v

    rows = ""
    total_value = 0
    total_entry = 0
    coins_pnl = []

    for coin, d in PORTFOLIO.items():
        p = get_price(coin)
        if p:
            current_val = p * d["amount"]
            entry_val = d["entry"] * d["amount"]
            total_value += current_val
            total_entry += entry_val
            pnl = (p - d["entry"]) / d["entry"] * 100
            coins_pnl.append((coin, pnl))
            c = "#4caf50" if pnl >= 0 else "#f44336"
            rows += f"<tr><td><b>{coin}</b></td><td>${p:,.2f}</td><td>${d['entry']}</td><td style='color:{c};text-shadow: 0 0 8px {c}'>{pnl:+.2f}%</td><td>${d['stop']}</td><td>${d['target']}</td></tr>"

    total_pnl = total_value - total_entry
    total_pnl_pct = (total_pnl / total_entry * 100) if total_entry else 0
    total_color = "#4caf50" if total_pnl >= 0 else "#f44336"

    # Ближайшая цель
    nearest_coin = None
    nearest_distance = 999
    for coin, d in PORTFOLIO.items():
        p = get_price(coin)
        if p:
            dist = (d["target"] - p) / p * 100
            if 0 < dist < nearest_distance:
                nearest_distance = dist
                nearest_coin = (coin, p, d["target"], dist)

    target_html = ""
    if nearest_coin:
        coin, cp, target, dist = nearest_coin
        target_html = f"""
        <div class='card' style='text-align:center;margin:10px 0;padding:10px;background:#1a1a1a;border-radius:8px;border:1px solid #c9a96e'>
            <span style='color:#c9a96e;font-size:14px'>🎯 Ближайшая цель: </span>
            <span style='color:#e0e0e0;font-size:14px;text-shadow: 0 0 6px #c9a96e'><b>{coin}</b> → <b>${target:,.2f}</b> (осталось <b>{dist:.2f}%</b>)</span>
        </div>
        """

    # Топ-3
    coins_sorted = sorted(coins_pnl, key=lambda x: x[1], reverse=True)
    top3 = coins_sorted[:3]
    bottom3 = sorted(coins_pnl, key=lambda x: x[1])[:3]
    medals = ["🥇", "🥈", "🥉"]

    top_html = "<div style='display:flex;justify-content:space-between;margin:20px 0;gap:20px'>"
    top_html += "<div style='flex:1;padding:15px;background:#1a1a1a;border-radius:8px;border:1px solid #4caf50'><span style='color:#4caf50;font-size:14px'>🟢 Топ-3 прибыльных</span><br>"
    for i, (coin, pnl) in enumerate(top3):
        top_html += f"<div style='margin:5px 0;font-size:13px'>{medals[i]} <b>{coin}</b>: <span style='color:#4caf50;text-shadow: 0 0 6px #4caf50'>{pnl:+.2f}%</span></div>"
    top_html += "</div>"
    top_html += "<div style='flex:1;padding:15px;background:#1a1a1a;border-radius:8px;border:1px solid #f44336'><span style='color:#f44336;font-size:14px'>🔴 Топ-3 убыточных</span><br>"
    for i, (coin, pnl) in enumerate(bottom3):
        top_html += f"<div style='margin:5px 0;font-size:13px'>{medals[i]} <b>{coin}</b>: <span style='color:#f44336;text-shadow: 0 0 6px #f44336'>{pnl:+.2f}%</span></div>"
    top_html += "</div></div>"

    # Paper Trading
    paper_balance, paper_pnl, paper_trades, paper_winrate = get_paper_stats()
    paper_color = "#4caf50" if paper_pnl >= 0 else "#f44336"
    paper_html = f"""
    <div style='margin:20px 0;padding:15px;background:#1a1a1a;border-radius:8px;text-align:center;border:1px solid #c9a96e'>
        <span style='color:#c9a96e;font-size:14px'>📝 Paper Trading</span><br>
        <span style='font-size:16px'>💰 Баланс: <b>${paper_balance:,.2f}</b></span>
        <span style='margin-left:20px;font-size:16px;color:{paper_color};text-shadow: 0 0 6px {paper_color}'>PnL: <b>{paper_pnl:+,.2f}</b></span><br>
        <span style='font-size:1.5vw;color:#666'>Сделок: {paper_trades} | Винрейт: {paper_winrate:.1f}%</span>
    </div>
    """

    # История сигналов
    signals = get_signals()
    signals_html = ""
    if signals:
        signals_html = "<div style='margin:20px 0;padding:15px;background:#1a1a1a;border-radius:8px'><span style='color:#c9a96e;font-size:14px'>📋 Последние сигналы</span><br>"
        for s in signals:
            ts, coin, action, price, pnl, reason = s
            emoji = "🟢" if pnl and pnl >= 0 else "🔴"
            signals_html += f"<div style='margin:5px 0;padding:5px;border-left:3px solid #c9a96e;background:#111;font-size:1.5vw'>{emoji} <b>{ts}</b> | {coin} | {action} @ ${price:,.2f} | PnL: {pnl:+,.2f} | {reason}</div>"
        signals_html += "</div>"

    # Сенсор

    mood = ""
    if "ЛЁГКОСТЬ" in sensor_state and "Эманация" in last_phase:
        mood = "🦅"
        mood_text = "Хищник в потоке"
    elif "ЛЁГКОСТЬ" in sensor_state:
        mood = "🐂"
        mood_text = "Бык просыпается"
    elif "ТЯЖЕСТЬ" in sensor_state and "Сжатие" in last_phase:
        mood = "🐻"
        mood_text = "Медведь у руля"
    elif "ТЯЖЕСТЬ" in sensor_state:
        mood = "🐢"
        mood_text = "Рынок в спячке"
    else:
        mood = "🦎"
        mood_text = "Ящерица ждёт"

    mood_box = f"""
    <div class='card' style='text-align:center;margin:10px 0;padding:12px;background:#1a1a1a;border-radius:8px;border:1px solid #c9a96e'>
        <span style='font-size:36px'>{mood}</span><br>
        <span style='color:#c9a96e;font-size:14px'>Настроение рынка: </span>
        <span style='color:#e0e0e0;font-size:14px'><b>{mood_text}</b></span>
    </div>
    """

    if "ЛЁГКОСТЬ" in sensor_state:
        sensor_bg = "#1a3a1a"
        sensor_border = "#4caf50"
        sensor_glow = "#4caf50"
    elif "ТЯЖЕСТЬ" in sensor_state:
        sensor_bg = "#3a1a1a"
        sensor_border = "#f44336"
        sensor_glow = "#f44336"
    else:
        sensor_bg = "#1a1a2a"
        sensor_border = "#9e9e9e"
        sensor_glow = "#9e9e9e"

    sensor_box = f"""
    <div style='text-align:center;margin:10px 0;padding:12px;background:{sensor_bg};border-radius:8px;border:2px solid {sensor_border};box-shadow: 0 0 12px {sensor_glow}'>
        <span style='color:#c9a96e;font-size:14px'>🧠 Сенсор: </span>
        <span style='color:#e0e0e0;font-size:14px;text-shadow: 0 0 6px {sensor_glow}'><b>{sensor_state}</b></span>
    </div>
    """

    phase_box = f"""
    <div class='card' style='text-align:center;margin:10px 0;padding:10px;background:#1a1a1a;border-radius:8px;border:1px solid #c9a96e'>
        <span style='color:#c9a96e;font-size:16px'>Фаза рынка: </span>
        <span style='color:#e0e0e0;font-size:16px;text-shadow: 0 0 6px #c9a96e'><b>{last_phase}</b></span>
    </div>
    """

    summary = f"""
    <div class='card' style='text-align:center;margin:20px 0;padding:15px;background:#1a1a1a;border-radius:8px;border:1px solid {total_color};box-shadow: 0 0 12px {total_color}'>
        <span style='color:#c9a96e;font-size:18px'>💰 Общий баланс: </span>
        <span style='color:#e0e0e0;font-size:18px;text-shadow: 0 0 8px #c9a96e'><b>${total_value:,.2f}</b></span>
        <span style='margin-left:30px;color:#c9a96e;font-size:18px'>📈 Общая прибыль: </span>
        <span style='color:{total_color};font-size:18px;text-shadow: 0 0 8px {total_color}'><b>${total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)</b></span>
    </div>
    """

    now = datetime.now().strftime("%H:%M:%S")
    footer = f"""
    <div style='text-align:center;margin-top:20px;padding:10px;background:#1a1a1a;border-radius:8px;border:1px solid #333'>
        <span style='color:#666;font-size:1.5vw'>🕐 Последнее обновление: <b>{now}</b></span>
        <br><br>
        <a href='/' style='color:#c9a96e;text-decoration:none;margin:0 10px;text-shadow: 0 0 4px #c9a96e'>🔄 Обновить</a>
        <a href='https://t.me/YanaArchitectBot' target='_blank' style='color:#c9a96e;text-decoration:none;margin:0 10px;text-shadow: 0 0 4px #c9a96e'>🤖 Открыть бота</a>
    </div>
    """

    return f"""<!DOCTYPE html><html><head><link rel="manifest" href="/manifest.json"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-status-bar-style" content="black"><meta name="theme-color" content="#c9a96e"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Архитектор: Командный Центр</title><meta http-equiv="refresh" content="30"><style>body{{background:#050505;color:#e0e0e0;font-family:monospace;padding:2vw}}h1{{color:#c9a96e;text-align:center;text-shadow:0 0 10px #c9a96e,0 0 20px #c9a96e;font-size:5vw;letter-spacing:2px}}table{{border-collapse:collapse;width:100%;margin-top:20px;border:1px solid #c9a96e}}th{{background:linear-gradient(180deg,#1a1a1a,#0a0a0a);color:#c9a96e;padding:14px;text-align:left;border:1px solid #333;text-shadow:0 0 4px #c9a96e}}td{{padding:12px;text-align:left;border:1px solid #333}}tr:hover{{background:#1a1a1a;box-shadow:0 0 8px #c9a96e}}a{{color:#c9a96e;text-decoration:none;transition:all 0.3s}}a:hover{{color:#fff;text-shadow:0 0 8px #c9a96e}}.card{{background:#0a0a0a;border:1px solid #c9a96e;border-radius:8px;padding:15px;margin:15px 0;box-shadow:0 0 8px rgba(201,169,110,0.2)}}
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes glow {{
            0% {{ text-shadow: 0 0 4px #c9a96e; }}
            50% {{ text-shadow: 0 0 12px #c9a96e, 0 0 24px #c9a96e; }}
            100% {{ text-shadow: 0 0 4px #c9a96e; }}
        }}
</style></head><body><h1>🏰 Архитектор: Командный Центр</h1>{mood_box}{sensor_box}{phase_box}{target_html}{summary}{top_html}{paper_html}{signals_html}<div class="card"><h2 style="color:#c9a96e">📈 График PnL</h2><span style="color:#888">Нет данных.</span></div><table><tr><th>Монета</th><th>Цена</th><th>Вход</th><th>PnL</th><th>Стоп</th><th>Цель</th></tr>{rows}</table>{footer}</body></html>"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)