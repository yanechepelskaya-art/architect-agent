import json, urllib.request, ssl, torch, pickle
import numpy as np
from torch import nn

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def okx_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        return json.loads(r.read())

class LSTM(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(input_size=5, hidden_size=32, num_layers=1, batch_first=True)
        self.fc = nn.Linear(32, 1)
    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1])

def train():
    data = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=800")["data"][::-1]
    X, y = [], []
    for i in range(len(data)-20):
        win = data[i:i+20]
        row = []
        for c in win:
            o=float(c[1]); h=float(c[2]); l=float(c[3]); cl=float(c[4]); v=float(c[5])
            row.append([(h-l)/o if o else 0, (cl-l)/(h-l+1e-9), (cl-o)/o if o else 0, v/(float(c[5])+1), cl/o if o else 1])
        X.append(row)
        y.append(1 if float(data[i+20][4]) > float(data[i+19][4]) else 0)
    X = torch.tensor(X, dtype=torch.float32)
    y = torch.tensor(y, dtype=torch.float32).unsqueeze(1)
    model = LSTM()
    opt = torch.optim.Adam(model.parameters(), lr=0.001)
    lossf = nn.BCEWithLogitsLoss()
    model.train()
    for epoch in range(30):
        opt.zero_grad()
        out = model(X)
        loss = lossf(out, y)
        loss.backward()
        opt.step()
    model.eval()
    with open("lstm_model.pkl", "wb") as f:
        pickle.dump(model, f)
    print("LSTM_TRAINED")

if __name__ == "__main__":
    train()
