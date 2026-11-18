"""
Bot d'alertes : TOUTES les cryptos (paires USDT sur Binance) -> notification iPhone (ntfy)

Lancé toutes les 5 minutes. Il n'alerte que sur les cryptos qui MONTENT EN CE MOMENT
(hausse sur les 15 dernières minutes, et la dernière bougie de 5 min encore verte).
Une crypto n'est signalée qu'au moment où elle franchit le seuil (pas de répétition).
Il ne passe AUCUN ordre : il te prévient, c'est toi qui décides.
"""
import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor

# ====== RÉGLAGES (modifie ici) ======
HAUSSE_15MIN_PCT = 3         # alerte si +3% sur les 15 dernières minutes
VOLUME_MIN_USDT = 5_000_000  # ignore les cryptos peu échangées (évite les pièges)
NB_MAX_DANS_ALERTE = 10      # nombre max de cryptos listées dans la notif
# ====================================

TOPIC = os.environ["NTFY_TOPIC"]
API = "https://data-api.binance.vision/api/v3"
STABLES = {"USDC", "FDUSD", "TUSD", "USDP", "DAI", "EUR", "AEUR", "USDE", "XUSD", "BFUSD", "PYUSD"}


def envoyer(message):
    requests.post(f"https://ntfy.sh/{TOPIC}", data=message.encode("utf-8"), timeout=15)


def liste_cryptos():
    """Toutes les paires USDT assez échangées -> {symbole: variation 24h en %}."""
    r = requests.get(f"{API}/ticker/24hr", timeout=30)
    r.raise_for_status()
    out = {}
    for t in r.json():
        s = t["symbol"]
        if not s.endswith("USDT"):
            continue
        base = s[:-4]
        if base in STABLES or base.endswith(("UP", "DOWN", "BULL", "BEAR")):
            continue
        if float(t["quoteVolume"]) < VOLUME_MIN_USDT:
            continue
        out[s] = float(t["priceChangePercent"])
    return out


def analyser(args):
    symbol, h24 = args
    try:
        r = requests.get(
            f"{API}/klines",
            params={"symbol": symbol, "interval": "5m", "limit": 16},
            timeout=15,
        )
        r.raise_for_status()
        k = r.json()
        # on garde uniquement les bougies fermées
        maintenant = time.time() * 1000
        k = [x for x in k if x[6] < maintenant]
        if len(k) < 14:
            return None
        c = [float(x[4]) for x in k]
        o_last = float(k[-1][1])
        chg_now = (c[-1] - c[-4]) / c[-4] * 100    # variation sur 15 min
        chg_prev = (c[-2] - c[-5]) / c[-5] * 100   # idem, 5 min plus tôt
        h1 = (c[-1] - c[-13]) / c[-13] * 100       # variation sur 1h (info)
        encore_vert = c[-1] > o_last               # la dernière bougie monte
        # franchissement du seuil = une seule alerte par mouvement
        if chg_now >= HAUSSE_15MIN_PCT > chg_prev and encore_vert:
            return (symbol[:-4], chg_now, h1, h24, c[-1])
    except Exception as e:
        print(f"Erreur {symbol}: {e}")
    return None


def prix_txt(p):
    return f"{p:,.2f}" if p >= 1 else f"{p:.6f}".rstrip("0")


if __name__ == "__main__":
    cryptos = liste_cryptos()
    print(f"{len(cryptos)} cryptos scannées")
    with ThreadPoolExecutor(max_workers=8) as ex:
        resultats = [r for r in ex.map(analyser, cryptos.items()) if r]

    if resultats:
        resultats.sort(key=lambda x: x[1], reverse=True)
        lignes = [
            f"{nom}: {m15:+.1f}% (15min) | 1h {h1:+.1f}% | 24h {h24:+.1f}% | {prix_txt(p)} $"
            for nom, m15, h1, h24, p in resultats[:NB_MAX_DANS_ALERTE]
        ]
        reste = len(resultats) - NB_MAX_DANS_ALERTE
        if reste > 0:
            lignes.append(f"... et {reste} autres")
        envoyer("🚀 Ça monte maintenant\n" + "\n".join(lignes))
    else:
        print("Rien à signaler")
