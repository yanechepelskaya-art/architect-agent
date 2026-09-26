import pickle
import requests
from datetime import datetime

MODEL_PATH = "phase_model_v2.pkl"

def load_model():
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)

def get_current_data():
    try:
        r1 = requests.get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT", timeout=10)
        d1 = r1.json()["data"][0]
        price = float(d1["last"])
        vol = float(d1["vol24h"])
        open24 = float(d1["open24h"])
        change = (price - open24) / open24 * 100

        r2 = requests.get("https://www.okx.com/api/v5/public/open-interest?instId=BTC-USDT-SWAP", timeout=10)
        d2 = r2.json()["data"][0]
        oi = float(d2["oi"])

        r3 = requests.get("https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP", timeout=10)
        d3 = r3.json()["data"][0]
        funding = float(d3["fundingRate"])

        # Новые фичи — заглушки, но структура готова
        atr = 0.0
        rsi = 50.0
        hour = datetime.now().hour
        price_change_5 = 0.0
        oi_change_5 = 0.0

        return [price, vol, oi, funding, 0, atr, rsi, hour, price_change_5, oi_change_5]
    except Exception as e:
        print(f"Ошибка данных: {e}")
        return None

def predict_phase():
    model = load_model()
    data = get_current_data()
    if data is None:
        return "unknown", 0

    pred = model.predict([data])[0]
    probs = model.predict_proba([data])[0]
    confidence = max(probs) * 100

    return pred, confidence

if __name__ == "__main__":
    phase, conf = predict_phase()
    print(f"Фаза: {phase} | Уверенность: {conf:.1f}%")
