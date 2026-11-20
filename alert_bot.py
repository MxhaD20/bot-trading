import os
import requests

# Le topic vient du secret GitHub NTFY_TOPIC
TOPIC = os.environ.get("NTFY_TOPIC", "TON_TOPIC_ICI")
SEUIL = 0.1  # variation minimale en % sur 5 min (hausse ou baisse)

COINS = ["BTC", "ETH", "XRP", "SOL", "DOGE",
         "ADA", "AVAX", "LINK", "LTC", "DOT"]


def alerte(titre, message, tag):
    requests.post(
        f"https://ntfy.sh/{TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": titre, "Tags": tag},
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
        variation = (cloture - ouverture) / ouverture * 100

        if variation >= SEUIL:
            alerte(
                f"{coin} +{variation:.2f}%",
                f"{coin} a monté de {variation:.2f}% en 5 min (prix : {cloture} $)",
                "chart_with_upwards_trend",
            )
        elif variation <= -SEUIL:
            alerte(
                f"{coin} {variation:.2f}%",
                f"{coin} a baissé de {abs(variation):.2f}% en 5 min (prix : {cloture} $)",
                "chart_with_downwards_trend",
            )
    except Exception as e:
        print(f"Erreur {coin} : {e}")
