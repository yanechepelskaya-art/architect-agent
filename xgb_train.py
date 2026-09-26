
import requests, numpy as np, pickle
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from xgboost import XGBClassifier

def okx_get(url):
    session = requests.Session()
    retry = Retry(total=2, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session.get(url, timeout=15)

def train_xgb():
    r = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=300")
    candles = r.json()["data"][::-1]
    X, y = [], []
    for i in range(5, len(candles)-1):
        row = []
        for j in range(i-5, i):
            c = candles[j]
            row += [float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])]
        X.append(row)
        y.append(1 if float(candles[i+1][4]) > float(candles[i][4]) else 0)
    if len(X) < 30:
        return None
    model = XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42)
    model.fit(X, y)
    with open("xgb_model.pkl", "wb") as f:
        pickle.dump(model, f)
    return True

def xgb_predict():
    try:
        with open("xgb_model.pkl", "rb") as f:
            model = pickle.load(f)
    except:
        return None
    r = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=10")
    candles = r.json()["data"][::-1]
    row = []
    for c in candles[-5:]:
        row += [float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])]
    return model.predict_proba([row])[0][1]

if __name__ == "__main__":
    if train_xgb():
        print("XGB_TRAINED")
        print("PROB_UP", xgb_predict())
    else:
        print("NOT_ENOUGH_DATA")
