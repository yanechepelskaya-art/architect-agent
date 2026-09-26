
import ccxt, numpy as np, torch, torch.nn as nn
from sklearn.preprocessing import StandardScaler

exchange = ccxt.okx()

def get_price(symbol):
    try: return exchange.fetch_ticker(f"{symbol}/USDT")["last"]
    except: return None

print("=" * 50)
print("LSTM + TRANSFORMER")
print("=" * 50)

ohlcv = exchange.fetch_ohlcv("BTC/USDT", "1h", limit=500)
closes = np.array([c[4] for c in ohlcv])
volumes = np.array([c[5] for c in ohlcv])

X, y = [], []
seq_len = 24
for i in range(seq_len, len(closes)-1):
    features = np.column_stack([closes[i-seq_len:i], volumes[i-seq_len:i]])
    X.append(features)
    change = (closes[i+1] - closes[i]) / closes[i] * 100
    y.append(0 if change > 0.5 else (1 if change < -0.5 else 2))

X, y = np.array(X), np.array(y)
X_flat = X.reshape(-1, 2)
scaler = StandardScaler()
X_flat = scaler.fit_transform(X_flat)
X = X_flat.reshape(X.shape[0], seq_len, 2)

# LSTM
class LSTMModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(2, 32, 2, batch_first=True)
        self.fc = nn.Linear(32, 3)
    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])

# Transformer
class TransformerModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed = nn.Linear(2, 64)
        encoder_layer = nn.TransformerEncoderLayer(d_model=64, nhead=4, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=2)
        self.fc = nn.Linear(64, 3)
    def forward(self, x):
        x = self.embed(x)
        x = self.transformer(x)
        return self.fc(x[:, -1, :])

X_tensor = torch.FloatTensor(X)
y_tensor = torch.LongTensor(y)

# LSTM
print("Обучаю LSTM...")
lstm = LSTMModel()
opt = torch.optim.Adam(lstm.parameters(), lr=0.001)
for epoch in range(30):
    opt.zero_grad()
    loss = nn.CrossEntropyLoss()(lstm(X_tensor), y_tensor)
    loss.backward()
    opt.step()

lstm.eval()
with torch.no_grad():
    lstm_out = lstm(X_tensor[-1:])
    lstm_probs = torch.softmax(lstm_out, dim=1)[0]
    lstm_pred = torch.argmax(lstm_out, dim=1).item()

# Transformer
print("Обучаю Transformer...")
trans = TransformerModel()
opt = torch.optim.Adam(trans.parameters(), lr=0.0005)
for epoch in range(30):
    opt.zero_grad()
    loss = nn.CrossEntropyLoss()(trans(X_tensor), y_tensor)
    loss.backward()
    opt.step()

trans.eval()
with torch.no_grad():
    trans_out = trans(X_tensor[-1:])
    trans_probs = torch.softmax(trans_out, dim=1)[0]
    trans_pred = torch.argmax(trans_out, dim=1).item()

labels = {0: "BUY", 1: "SELL", 2: "HOLD"}
p = get_price("BTC")

print(f"\n₿ BTC: ${p:,.2f}")
print(f"\n🧠 LSTM: {labels.get(lstm_pred, '—')}")
print(f"   BUY: {lstm_probs[0]*100:.0f}% | SELL: {lstm_probs[1]*100:.0f}% | HOLD: {lstm_probs[2]*100:.0f}%")
print(f"\n🔮 Transformer: {labels.get(trans_pred, '—')}")
print(f"   BUY: {trans_probs[0]*100:.0f}% | SELL: {trans_probs[1]*100:.0f}% | HOLD: {trans_probs[2]*100:.0f}%")
print("\n" + "=" * 50)
print("LSTM + Transformer работают!")
