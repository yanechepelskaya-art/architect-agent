import csv
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import numpy as np

X = []
y = []

with open("btc_data_labeled.csv", "r") as f:
    reader = csv.DictReader(f)
    prev_price = None
    prev_vol = None
    for row in reader:
        try:
            price = float(row["price"])
            vol = float(row["vol24h"])
            oi = float(row["oi"])
            funding = float(row["funding"])
            delta = float(row["delta"])
            phase = row["phase"]

            if phase == "flat":
                continue

            change = (price - prev_price) / prev_price * 100 if prev_price else 0
            vol_change = (vol - prev_vol) / prev_vol * 100 if prev_vol else 0

            X.append([price, vol, oi, funding, delta, change, vol_change])
            y.append(phase)

            prev_price = price
            prev_vol = vol
        except Exception:
            continue

print(f"Собрано {len(X)} примеров")

if len(X) < 100:
    print("❌ Мало данных для обучения")
else:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print(f"✅ Точность: {acc*100:.2f}%")
    print(f"Классы: {set(y)}")

    with open("phase_model.pkl", "wb") as f:
        pickle.dump(model, f)

    print("✅ Модель сохранена: phase_model.pkl")
