import json, urllib.request, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def okx_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        return json.loads(r.read())

data = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=800")["data"][::-1]
wins = 0
losses = 0
pnl = 0
from sklearn.ensemble import RandomForestClassifier
import numpy as np
X, y = [], []
for i in range(20, len(data)-1):
    win = data[i-20:i]
    row = []
    for c in win:
        o=float(c[1]); h=float(c[2]); l=float(c[3]); cl=float(c[4]); v=float(c[5])
        row += [(h-l)/o if o else 0, (cl-l)/(h-l+1e-9), (cl-o)/o if o else 0, v/(float(c[5])+1)]
    X.append(row)
    y.append(1 if float(data[i+1][4]) > float(data[i][4]) else 0)
model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
model.fit(X, y)

for i in range(20, len(data)-1):
    o = float(data[i][1])
    h = float(data[i][2])
    l = float(data[i][3])
    c = float(data[i][4])
    if o == 0:
        continue
    rng = (h-l)/o
    if rng < 0.001 or rng > 0.01:
        continue
    prev_c = float(data[i-1][4])
    if c > prev_c:
        continue
    row = []
    for cc in data[i-20:i]:
        o=float(cc[1]); h=float(cc[2]); l=float(cc[3]); cl=float(cc[4]); v=float(cc[5])
        row += [(h-l)/o if o else 0, (cl-l)/(h-l+1e-9), (cl-o)/o if o else 0, v/(float(cc[5])+1)]
    prob = model.predict_proba([row])[0][1]
    if prob < 0.60:
        continue
    atr = np.mean([abs(float(data[j][2])-float(data[j][3])) for j in range(i-10, i)])
    entry = c
    stop = entry - atr * 1.2
    target = entry + atr * 2.4
    future = data[i+1]
    fh = float(future[2])
    fl = float(future[3])
    fc = float(future[4])
    if fl <= stop:
        losses += 1
        pnl -= 1
    elif fh >= target:
        wins += 1
        pnl += 2
    else:
        if fc > entry:
            wins += 1
            pnl += (fc-entry)/entry*100
        else:
            losses += 1
            pnl -= (entry-fc)/entry*100
total = wins + losses
print("BACKTEST")
print("Deals:", total)
print("Wins:", wins)
print("Losses:", losses)
print("Winrate:", round(wins/total*100, 1), "%")
print("PnL:", round(pnl, 1))
