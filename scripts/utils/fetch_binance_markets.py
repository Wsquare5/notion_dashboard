#!/usr/bin/env python3
"""
Fetch Binance Spot symbols and USDT-M perpetual futures symbols, collect metrics
and enrich with CoinGecko market data. Output JSON to stdout or file.

Usage:
  python fetch_binance_markets.py --limit 30 --out data.json
"""
from __future__ import annotations

import json
import time
from typing import Dict, List, Optional
import os

import requests
from pycoingecko import CoinGeckoAPI
from tenacity import retry, stop_after_attempt, wait_exponential

BINANCE_SPOT = "https://api.binance.com"
BINANCE_FAPI = "https://fapi.binance.com"
cg = CoinGeckoAPI()
session = requests.Session()
session.headers.update({"User-Agent": "fetch-binance-markets/1.0"})

# overrides path (relative to repo)
OVERRIDES_PATH = os.path.join(os.path.dirname(__file__), "..", "overrides.json")


def load_overrides(path: str) -> Dict[str, str]:
    try:
        with open(path, "r") as f:
            data = json.load(f)
            # normalize keys to upper-case base symbols
            return {k.upper(): v for k, v in data.items()}
    except Exception:
        return {}




@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def get_json(url: str, params: dict = None) -> dict:
    r = session.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def fetch_spot_symbols() -> List[str]:
    info = get_json(BINANCE_SPOT + "/api/v3/exchangeInfo")
    syms = []
    for s in info.get("symbols", []):
        # only include trading USDT-quoted spot pairs
        if s.get("status") != "TRADING":
            continue
        if s.get("quoteAsset") != "USDT":
            continue
        syms.append(s["symbol"])  # e.g., BTCUSDT
    return syms


def fetch_perp_symbols() -> List[str]:
    info = get_json(BINANCE_FAPI + "/fapi/v1/exchangeInfo")
    syms = []
    for s in info.get("symbols", []):
        if s.get("contractType") != "PERPETUAL":
            continue
        if s.get("quoteAsset") != "USDT":
            continue
        if s.get("status") != "TRADING":
            continue
        syms.append(s["symbol"])  # e.g., BTCUSDT
    return syms


def base_asset(symbol: str) -> str:
    if symbol.endswith("USDT"):
        return symbol[:-4]
    # best-effort fallback
    return symbol


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def fetch_binance_metrics(symbol: str, perp: bool = False) -> dict:
    if perp:
        price = get_json(BINANCE_FAPI + "/fapi/v1/ticker/price", params={"symbol": symbol})
        oi = get_json(BINANCE_FAPI + "/fapi/v1/openInterest", params={"symbol": symbol})
        t24 = get_json(BINANCE_FAPI + "/fapi/v1/ticker/24hr", params={"symbol": symbol})
    else:
        price = get_json(BINANCE_SPOT + "/api/v3/ticker/price", params={"symbol": symbol})
        # open interest doesn't exist for spot
        oi = {"openInterest": None}
        t24 = get_json(BINANCE_SPOT + "/api/v3/ticker/24hr", params={"symbol": symbol})

    return {
        "symbol": symbol,
        "price": float(price.get("price", 0)) if price.get("price") is not None else None,
        "openInterest": float(oi.get("openInterest")) if oi.get("openInterest") is not None else None,
        "quoteVolume": float(t24.get("quoteVolume")) if t24.get("quoteVolume") is not None else None,
        "baseVolume": float(t24.get("volume")) if t24.get("volume") is not None else None,
    }


def build_coingecko_candidates() -> Dict[str, List[str]]:
    """
    Build a mapping from SYMBOL -> list of candidate coingecko ids that share that symbol.
    We'll later resolve ambiguous symbols by selecting the candidate with the largest market_cap
    (unless an override is provided in overrides.json).
    """
    coins = cg.get_coins_list()
    candidates: Dict[str, List[str]] = {}
    for c in coins:
        sym = c.get("symbol", "").upper()
        cid = c.get("id")
        if not sym or not cid:
            continue
        candidates.setdefault(sym, []).append(cid)
    return candidates


def batch_markets_by_ids(ids: List[str]) -> Dict[str, dict]:
    out = {}
    chunk = 50
    for i in range(0, len(ids), chunk):
        part = ids[i : i + chunk]
        try:
            markets = cg.get_coins_markets(vs_currency="usd", ids=part)
        except Exception as e:
            print("CoinGecko chunk failed, retrying once", e)
            time.sleep(1)
            markets = cg.get_coins_markets(vs_currency="usd", ids=part)
        for m in markets:
            out[m["id"]] = m
        time.sleep(1)
    return out


def resolve_coingecko_ids_for_bases(bases: List[str], candidates_map: Dict[str, List[str]], overrides: Dict[str, str]) -> Dict[str, Optional[str]]:
    """
    For each base (e.g., 'BTC'), determine the best coingecko id to use.
    Priority: overrides -> if single candidate -> choose candidate with highest market_cap among candidates -> None
    Returns mapping base -> coingecko_id or None.
    """
    # collect all candidate ids we may need to score
    needed_ids = set()
    base_to_candidates: Dict[str, List[str]] = {}
    for b in bases:
        key = b.upper()
        if key in overrides:
            # ensure override present
            needed_ids.add(overrides[key])
            base_to_candidates[b] = [overrides[key]]
            continue
        cand = candidates_map.get(key) or []
        base_to_candidates[b] = cand
        for cid in cand:
            needed_ids.add(cid)

    # fetch market data for all needed ids (to compare market caps)
    needed_ids_list = list(needed_ids)
    market_data = batch_markets_by_ids(needed_ids_list) if needed_ids_list else {}

    result: Dict[str, Optional[str]] = {}
    for b, cand in base_to_candidates.items():
        key = b.upper()
        if key in overrides:
            result[b] = overrides[key]
            continue
        if not cand:
            result[b] = None
            continue
        if len(cand) == 1:
            result[b] = cand[0]
            continue
        # multiple candidates: choose one with largest market_cap
        best_id = None
        best_mc = -1
        for cid in cand:
            m = market_data.get(cid)
            mc = None
            if m:
                mc = m.get("market_cap")
            if mc is None:
                continue
            try:
                mc_val = float(mc)
            except Exception:
                continue
            if mc_val > best_mc:
                best_mc = mc_val
                best_id = cid
        result[b] = best_id

    return result


def enrich_and_collect(symbols: List[str], perp: bool) -> List[dict]:
    results: List[dict] = []

    # prepare overrides and candidates
    overrides = load_overrides(OVERRIDES_PATH)
    candidates = build_coingecko_candidates()

    # Gather Binance metrics
    records: List[dict] = []
    bases: List[str] = []
    for s in symbols:
        try:
            metrics = fetch_binance_metrics(s, perp=perp)
        except Exception as e:
            print(f"Failed to fetch metrics for {s}: {e}")
            continue
        base = base_asset(s)
        bases.append(base)
        records.append({
            "symbol": s,
            "base": base,
            "metrics": metrics,
            "coingecko_id": None,
        })
        time.sleep(0.02)

    # resolve coingecko ids for bases
    bases_unique = list(dict.fromkeys(bases))
    resolved = resolve_coingecko_ids_for_bases(bases_unique, candidates, overrides)

    # apply resolved ids to records
    for r in records:
        r["coingecko_id"] = resolved.get(r["base"])

    ids = [r["coingecko_id"] for r in records if r.get("coingecko_id")]
    ids = list(dict.fromkeys(ids))
    market_data = batch_markets_by_ids(ids) if ids else {}

    for r in records:
        cid = r.get("coingecko_id")
        m = market_data.get(cid) if cid else None
        results.append({
            "symbol": r["symbol"],
            "base": r["base"],
            "price": r["metrics"].get("price"),
            "openInterest": r["metrics"].get("openInterest"),
            "quoteVolume": r["metrics"].get("quoteVolume"),
            "market_cap": m.get("market_cap") if m else None,
            "fdv": m.get("fully_diluted_valuation") if m else None,
            "coingecko_id": cid,
        })
        time.sleep(0.02)

    return results


def main():
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None, help="limit symbols processed per type (spot/perp). Default: all")
    p.add_argument("--out", type=str, default=None)
    args = p.parse_args()

    spot = fetch_spot_symbols()
    perp = fetch_perp_symbols()

    print(f"Spot symbols (USDT): {len(spot)}, Perp symbols (USDT): {len(perp)}")

    if args.limit:
        spot = spot[: args.limit]
        perp = perp[: args.limit]

    spot_res = enrich_and_collect(spot, perp=False)
    perp_res = enrich_and_collect(perp, perp=True)

    out = {"spot": spot_res, "perp": perp_res}
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print(f"Wrote output to {args.out}")
    else:
        print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
