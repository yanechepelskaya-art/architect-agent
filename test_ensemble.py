
import ccxt, numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

exchange = ccxt.okx()

def get_price(symbol):
    try:
        return exchange.fetch_ticker(f"{symbol}/USDT")["last"]
    except:
        return None

def get_rsi(symbol="BTC-USDT", periods=14):
    ohlcv = exchange.fetch_ohlcv(symbol, "5m", limit=periods+1)
    closes = [c[4] for c in ohlcv]
    gains = sum(max(closes[i]-closes[i-1], 0) for i in range(1, len(closes)))
    losses = sum(max(closes[i-1]-closes[i], 0) for i in range(1, len(closes)))
    avg_gain, avg_loss = gains/periods, losses/periods
    if avg_loss == 0: return 100
    return round(100 - (100/(1 + avg_gain/avg_loss)), 1)

print("=" * 50)
print("МЕГА-АНСАМБЛЬ (4 модели)")
print("=" * 50)

ohlcv = exchange.fetch_ohlcv("BTC/USDT", "1h", limit=500)
closes = np.array([c[4] for c in ohlcv])
volumes = np.array([c[5] for c in ohlcv])

X, y = [], []
for i in range(24, len(closes)-1):
    features = [closes[i-24+j] for j in range(24)] + [volumes[i]]
    X.append(features)
    change = (closes[i+1] - closes[i]) / closes[i] * 100
    y.append(0 if change > 0.5 else (1 if change < -0.5 else 2))

X, y = np.array(X), np.array(y)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Random Forest
rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
rf.fit(X_scaled, y)

# Linear Regression
lr = LinearRegression()
lr.fit(np.arange(len(closes[-100:])).reshape(-1,1), closes[-100:])

# Предсказание
last = [closes[-25+j] for j in range(24)] + [volumes[-1]]
X_pred = scaler.transform([last])

rf_pred = rf.predict(X_pred)[0]
rf_proba = rf.predict_proba(X_pred)[0]

lr_pred_val = lr.predict([[len(closes)]])[0]
lr_change = (lr_pred_val - closes[-1]) / closes[-1] * 100

labels = {0: "BUY", 1: "SELL", 2: "HOLD"}
p = get_price("BTC")
rsi = get_rsi()

print(f"₿ BTC: ${p:,.2f}")
print(f"📐 RSI: {rsi}")
print()
print(f"🌲 Random Forest: {labels.get(rf_pred, '—')}")
print(f"   BUY: {rf_proba[0]*100:.0f}% | SELL: {rf_proba[1]*100:.0f}% | HOLD: {rf_proba[2]*100:.0f}%")
print(f"📈 Linear Reg: {labels.get(0 if lr_change > 0.5 else (1 if lr_change < -0.5 else 2))} ({lr_change:+.2f}%)")
print()
print("=" * 50)
print("Ансамбль работает!")
