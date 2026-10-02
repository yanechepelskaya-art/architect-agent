# atr.py — единый ATR по Уайлдеру
import requests

def calculate_atr(highs, lows, closes, period=14):
    """ATR по Уайлдеру."""
    if len(highs) < period + 1:
        return None
    trs = []
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        trs.append(tr)
    atr = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
    return round(atr, 2)

def get_atr_okx(instId="BTC-USDT", bar="1H", period=14):
    """Тянет свечи с OKX, считает ATR."""
    url = f"https://www.okx.com/api/v5/market/candles?instId={instId}&bar={bar}&limit={period+1}"
    r = requests.get(url, timeout=10)
    data = r.json()["data"][::-1]
    highs  = [float(c[2]) for c in data]
    lows   = [float(c[3]) for c in data]
    closes = [float(c[4]) for c in data]
    return calculate_atr(highs, lows, closes, period)

if __name__ == "__main__":
    print("ATR BTC-USDT 1H:", get_atr_okx())
