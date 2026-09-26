
import ccxt
import requests
import sqlite3
import json
import time
import os
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

TOKEN = "8900618226:AAGPVlCFCNSMiDYrv3DkUbeWorQWrdYti0Q"
CHAT_ID = "870512243"
CHANNEL_ID = "-1003920623687"

exchange = ccxt.okx()
last_phase = "📊 Боковик"

def get_price(symbol):
    try:
        ticker = exchange.fetch_ticker(f"{symbol}/USDT")
        return ticker["last"]
    except:
        return None

def get_atr(symbol="BTC-USDT", periods=14):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, "5m", limit=periods+1)
        tr_sum = 0
        for i in range(1, len(ohlcv)):
            high, low, close_prev = ohlcv[i][2], ohlcv[i][3], ohlcv[i-1][4]
            tr = max(high-low, abs(high-close_prev), abs(low-close_prev))
            tr_sum += tr
        return tr_sum / periods if periods > 0 else 0
    except:
        return 0

def get_funding_rate(symbol="BTC-USDT-SWAP"):
    try:
        funding = exchange.fetch_funding_rate(symbol)
        return funding["fundingRate"] * 100
    except:
        return 0

def get_rsi(symbol="BTC-USDT", periods=14):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, "5m", limit=periods+1)
        closes = [c[4] for c in ohlcv]
        gains = sum(max(closes[i] - closes[i-1], 0) for i in range(1, len(closes)))
        losses = sum(max(closes[i-1] - closes[i], 0) for i in range(1, len(closes)))
        avg_gain = gains / periods
        avg_loss = losses / periods
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 1)
    except:
        return 50

print("=" * 50)
print("МЕТРИКИ")
print("=" * 50)

p = get_price("BTC")
print(f"BTC: ${p:,.2f}" if p else "BTC: нет данных")

atr = get_atr()
print(f"ATR (5m): ${atr:,.2f}")

fr = get_funding_rate()
print(f"Funding Rate: {fr:+.4f}%")

rsi = get_rsi()
print(f"RSI (5m): {rsi}")

print("=" * 50)
print("Метрики работают!")
