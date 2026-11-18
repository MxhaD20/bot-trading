"""
Bot d'alertes : TOUTES les cryptos (paires USDT sur Binance) -> notification iPhone (ntfy)

Chaque heure, le bot scanne tout le marché et t'envoie UNE notification
avec les cryptos qui viennent de monter fort (classées de la plus forte à la plus faible).
Il ne passe AUCUN ordre : il te prévient, c'est toi qui décides.
"""
import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor

# ====== RÉGLAGES (modifie ici) ======
HAUSSE_1H_PCT = 3          # une crypto qui monte de +3% sur la dernière heure déclenche l'alerte
HAUSSE_24H_PCT = 10        # ou +10% sur 24h
VOLUME_MIN_USDT = 5_000_000  # ignore les cryptos peu échangées (évite les pièges)
NB_MAX_DANS_ALERTE = 10    # nombre max de cryptos listées dans la notif
# ====================================

TOPIC = os.environ["NTFY_TOPIC"]
API = "https://data-api.binance.vision/api/v3"
STABLES = {"USDC", "FDUSD", "TUSD", "USDP", "DAI", "EUR", "AEUR", "USDE", "XUSD", "BFUSD", "PYUSD"}


def envoyer(message):
    requests.post(f"https://ntfy.sh/{TOPIC}", data=message.encode("utf-8"), timeout=15)


def liste_cryptos():
    """Toutes les paires USDT assez échangées."""
    r = requests.get(f"{API}/ticker/24hr", timeout=30)
    r.raise_for_status()
    out = []
    for t in r.json():
        s = t["symbol"]
        if not s.endswith("USDT"):
            continue
        base = s[:-4]
        if base in STABLES or base.endswith(("UP", "DOWN", "BULL", "BEAR")):
            continue
        if float(t["quoteVolume"]) < VOLUME_MIN_USDT:
            continue
        out.append(s)
    return out


def analyser(symbol):
    try:
        r = requests.get(
            f"{API}/klines",
            params={"symbol": symbol, "interval": "1h", "limit": 26},
            timeout=15,
        )
        r.raise_for_status()
        k = r.json()[:-1]  # on enlève la bougie en cours (pas fermée)
        if len(k) < 25:
            return None
        ouv, clo = float(k[-1][1]), float(k[-1][4])
        h1 = (clo - ouv) / ouv * 100
        h24 = (clo - float(k[-25][4])) / float(k[-25][4]) * 100
        if h1 >= HAUSSE_1H_PCT or h24 >= HAUSSE_24H_PCT:
            return (symbol[:-4], h1, h24, clo)
    except Exception as e:
        print(f"Erreur {symbol}: {e}")
    return None


def prix_txt(p):
    return f"{p:,.2f}" if p >= 1 else f"{p:.6f}".rstrip("0")


if __name__ == "__main__":
    symboles = liste_cryptos()
    print(f"{len(symboles)} cryptos scannées")
    with ThreadPoolExecutor(max_workers=8) as ex:
        resultats = [r for r in ex.map(analyser, symboles) if r]

    if resultats:
        resultats.sort(key=lambda x: x[1], reverse=True)  # plus forte hausse 1h d'abord
        lignes = [
            f"{nom}: {h1:+.1f}% (1h) / {h24:+.1f}% (24h) - {prix_txt(p)} $"
            for nom, h1, h24, p in resultats[:NB_MAX_DANS_ALERTE]
        ]
        reste = len(resultats) - NB_MAX_DANS_ALERTE
        if reste > 0:
            lignes.append(f"... et {reste} autres")
        envoyer("📈 Cryptos en hausse\n" + "\n".join(lignes))
    else:
        print("Rien à signaler")
