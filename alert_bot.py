import os
import requests

# Garde ton topic ntfy comme avant (secret GitHub / variable d'environnement)
TOPIC = os.environ.get("NTFY_TOPIC", "TON_TOPIC_ICI")
SEUIL = 0.1  # hausse minimale en % sur 5 min

COINS = ["BTC", "ETH", "XRP", "SOL", "DOGE",
         "ADA", "AVAX", "LINK", "LTC", "DOT"]

def alerte(titre, message):
    requests.post(
        f"https://ntfy.sh/{TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": titre, "Tags": "chart_with_upwards_trend"},
        timeout=15,
    )

for coin in COINS:
    try:
        r = requests.get(
            f"https://api.exchange.coinbase.com/products/{coin}-USD/candles",
            params={"granularity": 300},
            headers={"User-Agent": "bot-trading"},
            timeout=15,
        )
        # [0] = bougie en cours, [1] = dernière bougie de 5 min terminée
        _, low, high, ouverture, cloture, _ = r.json()[1]
        hausse = (cloture - ouverture) / ouverture * 100
        if hausse >= SEUIL:
            alerte(f"{coin} +{hausse:.2f}%",
                   f"{coin} a monté de {hausse:.2f}% en 5 min (prix : {cloture} $)")
    except Exception as e:
        print(f"Erreur {coin} : {e}")
