"""
ECOBANK token price resolution via Hive-Engine LP ratios.

Chain: HSBIDAO:ECOBANK LP (quote) -> 0.5 HSBIDAO/HIVE peg -> HIVE/USD rate.
Inspired by the standalone token-price-widget project's resolver design.
"""

import logging
import time

import requests

logger = logging.getLogger(__name__)

HSBIDAO_HIVE_PEG = 0.5
HIVE_USD_API_URL = (
    "https://api.coingecko.com/api/v3/simple/price?ids=hive&vs_currencies=usd"
)

_hive_usd_cache = {"value": None, "ts": 0.0}


def _he_post(node, method, params):
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    r = requests.post(f"{node}/contracts", json=payload, timeout=10)
    r.raise_for_status()
    return r.json().get("result")


def resolve_ecobank_price_in_hsbidao(node, pair="HSBIDAO:ECOBANK"):
    """Return the price of 1 ECOBANK in HSBIDAO terms from the Hive-Engine LP pool."""
    result = _he_post(
        node,
        "findOne",
        {"contract": "marketpools", "table": "pools", "query": {"tokenPair": pair}},
    )
    role = "quote"
    if not result:
        tokens = pair.split(":")
        reversed_pair = f"{tokens[1]}:{tokens[0]}"
        result = _he_post(
            node,
            "findOne",
            {
                "contract": "marketpools",
                "table": "pools",
                "query": {"tokenPair": reversed_pair},
            },
        )
        if not result:
            raise ValueError(f"LP pool not found: {pair} (also tried reversed)")
        role = "base"

    key = "quotePrice" if role == "quote" else "basePrice"
    return float(result[key])


def get_hive_usd_rate():
    """Fetch HIVE/USD with a 60-second in-process cache to avoid redundant calls."""
    now = time.time()
    if _hive_usd_cache["value"] is not None and now - _hive_usd_cache["ts"] < 60:
        return _hive_usd_cache["value"]

    r = requests.get(HIVE_USD_API_URL, timeout=10)
    r.raise_for_status()
    value = float(r.json()["hive"]["usd"])

    _hive_usd_cache["value"] = value
    _hive_usd_cache["ts"] = now
    return value


def resolve_ecobank_price(node):
    """Resolve the current ECOBANK price in HIVE and USD terms."""
    ecobank_in_hsbidao = resolve_ecobank_price_in_hsbidao(node)
    price_hive = ecobank_in_hsbidao * HSBIDAO_HIVE_PEG
    price_usd = price_hive * get_hive_usd_rate()
    return {"hive": price_hive, "usd": price_usd}
