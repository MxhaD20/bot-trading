"""
Bot d'alertes crypto -> notification iPhone (ntfy)
- Lit les prix sur Binance (API publique, pas de clé nécessaire)
- Envoie une alerte quand :
    * RSI passe sous 30 (survente = prix bas, possible moment d'achat)
    * RSI passe au-dessus de 70 (surchauffe = prudence)
    * Le prix chute de plus de X% en 24h
- Ne passe AUCUN ordre : il te prévient, c'est toi qui décides.
"""
import os
import requests

# ====== RÉGLAGES (modifie ici) ======
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]  # cryptos à surveiller
INTERVAL = "1h"        # bougies de 1 heure
RSI_PERIOD = 14
RSI_BAS = 30
RSI_HAUT = 70
CHUTE_24H_PCT = 5      # alerte si le prix baisse de plus de 5% en 24h
# ====================================

TOPIC = os.environ["NTFY_TOPIC"]  # le nom secret de ton "canal" ntfy
API = "https://data-api.binance.vision/api/v3"


def envoyer(message):
    requests.post(
        f"https://ntfy.sh/{TOPIC}",
        data=message.encode("utf-8"),
        timeout=15,
    )


def get_closes(symbol):
    r = requests.get(
        f"{API}/klines",
        params={"symbol": symbol, "interval": INTERVAL, "limit": 200},
        timeout=15,
    )
    r.raise_for_status()
    # on enlève la dernière bougie (pas encore fermée)
    return [float(k[4]) for k in r.json()][:-1]


def rsi_series(closes, period=14):
    """RSI de Wilder, renvoie la liste des RSI."""
    gains, pertes = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        pertes.append(max(-diff, 0))
    avg_g = sum(gains[:period]) / period
    avg_p = sum(pertes[:period]) / period
    out = []
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_p = (avg_p * (period - 1) + pertes[i]) / period
        rs = avg_g / avg_p if avg_p != 0 else 999
        out.append(100 - 100 / (1 + rs))
    return out


def verifier(symbol):
    closes = get_closes(symbol)
    rsi = rsi_series(closes, RSI_PERIOD)
    rsi_now, rsi_prev = rsi[-1], rsi[-2]
    prix = closes[-1]

    # On alerte seulement au moment du franchissement (évite le spam)
    if rsi_now < RSI_BAS <= rsi_prev:
        envoyer(f"🟢 {symbol}: RSI {rsi_now:.0f} (survente)\nPrix: {prix:,.2f} $\nPossible zone d'achat, à toi de juger.")
    elif rsi_now > RSI_HAUT >= rsi_prev:
        envoyer(f"🔴 {symbol}: RSI {rsi_now:.0f} (surchauffe)\nPrix: {prix:,.2f} $\nPrudence avant d'acheter.")

    # Chute sur 24h (24 bougies d'1h)
    if len(closes) > 25:
        var = (closes[-1] - closes[-25]) / closes[-25] * 100
        var_prev = (closes[-2] - closes[-26]) / closes[-26] * 100
        if var <= -CHUTE_24H_PCT < var_prev:
            envoyer(f"⚠️ {symbol}: {var:.1f}% en 24h\nPrix: {prix:,.2f} $")


if __name__ == "__main__":
    for s in SYMBOLS:
        try:
            verifier(s)
        except Exception as e:
            print(f"Erreur {s}: {e}")
