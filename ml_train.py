import json, urllib.request, pickle, ssl
import numpy as np
from sklearn.ensemble import RandomForestClassifier

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def okx_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        return json.loads(r.read())

def train_ml():
    try:
        r = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=100")
        data = r["data"][::-1]
        X, y = [], []
        vols = [float(c[5]) for c in data]
        avg_vol = np.mean(vols[-20:]) if len(vols) >= 20 else np.mean(vols)
        for i in range(len(data)-10):
            window = data[i:i+10]
            row = []
            for c in window:
                o = float(c[1])
                h = float(c[2])
                l = float(c[3])
                cl = float(c[4])
                v = float(c[5])
                rng = (h - l) / o if o else 0
                pos = (cl - l) / (h - l + 1e-9)
                ret = (cl - o) / o if o else 0
                vol_norm = v / (avg_vol + 1)
                row += [rng, pos, ret, vol_norm]
            X.append(row)
            y.append(1 if (float(data[i+6][4]) - float(data[i][4])) / float(data[i][4]) >= 0.0015 else 0)
        if len(X) < 30:
            return False
        X = np.array(X)
        y = np.array(y)
        model = RandomForestClassifier(n_estimators=200, max_depth=7, class_weight="balanced", random_state=42)
        model.fit(X, y)
        with open("ml_model.pkl", "wb") as f:
            pickle.dump(model, f)
        return True
    except Exception as e:
        print("TRAIN_ERR", e)
        return False

def ml_predict():
    try:
        with open("ml_model.pkl", "rb") as f:
            model = pickle.load(f)
        r = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=30")
        data = r["data"][::-1]
        vols = [float(c[5]) for c in data]
        avg_vol = np.mean(vols[-20:]) if len(vols) >= 20 else np.mean(vols)
        window = data[-10:]
        row = []
        for c in window:
            o = float(c[1])
            h = float(c[2])
            l = float(c[3])
            cl = float(c[4])
            v = float(c[5])
            rng = (h - l) / o if o else 0
            pos = (cl - l) / (h - l + 1e-9)
            ret = (cl - o) / o if o else 0
            vol_norm = v / (avg_vol + 1)
            row += [rng, pos, ret, vol_norm]
        prob = model.predict_proba([row])[0][1]
        return prob
    except Exception as e:
        print("PREDICT_ERR", e)
        return None

if __name__ == "__main__":
    if train_ml():
        print("ML_TRAINED")
        print("PROB_UP", round(ml_predict(), 4))
    else:
        print("NOT_ENOUGH_DATA")
