#!/usr/bin/env python3
"""
Generate a mapping report for a watchlist of bases/symbols using CoinGecko candidates.

Writes `data/mapping_report.csv` with columns:
 base, normalized, chosen_id, chosen_name, chosen_market_cap, confidence, reason, candidates
"""
from __future__ import annotations

import csv
import json
import os
from typing import List, Dict

from pycoingecko import CoinGeckoAPI
import requests

BINANCE_SPOT = "https://api.binance.com"
PRICE_MATCH_THRESHOLD = 0.05  # 5%

ROOT = os.path.dirname(os.path.dirname(__file__))
WATCHLIST = os.path.join(ROOT, "watchlist.txt")
OUT_CSV = os.path.join(ROOT, "data", "mapping_report.csv")

OVERRIDES_PATH = os.path.join(ROOT, "overrides.json")

cg = CoinGeckoAPI()


def load_watchlist(path: str) -> List[str]:
    with open(path, "r") as f:
        lines = [l.strip() for l in f if l.strip()]
    return lines


def build_candidates_map() -> Dict[str, List[Dict]]:
    coins = cg.get_coins_list()
    mapping: Dict[str, List[Dict]] = {}
    for c in coins:
        sym = c.get("symbol", "").upper()
        mapping.setdefault(sym, []).append({"id": c.get("id"), "name": c.get("name")})
    return mapping


def batch_markets(ids: List[str]) -> Dict[str, Dict]:
    out = {}
    chunk = 50
    for i in range(0, len(ids), chunk):
        part = ids[i : i + chunk]
        res = cg.get_coins_markets(vs_currency="usd", ids=part)
        for r in res:
            out[r["id"]] = r
    return out


def get_binance_spot_price_for_base(base: str) -> float | None:
    """Return the Binance spot USDT price for base (e.g., BTC -> BTCUSDT) or None if not found."""
    symbol = base.upper()
    if not symbol.endswith("USDT"):
        symbol = symbol + "USDT"
    try:
        r = requests.get(BINANCE_SPOT + f"/api/v3/ticker/price", params={"symbol": symbol}, timeout=5)
        if r.status_code != 200:
            return None
        j = r.json()
        price = j.get("price")
        if price is None:
            return None
        return float(price)
    except Exception:
        return None


def normalize_token(token: str) -> str:
    # basic normalization: remove leading digits and non-alphanum
    import re

    t = token.upper()
    t2 = re.sub(r"^[0-9_]+", "", t)
    t2 = re.sub(r"[^A-Z0-9]", "", t2)
    return t2


def main():
    watch = load_watchlist(WATCHLIST)
    candidates_map = build_candidates_map()
    # load overrides
    overrides = {}
    try:
        with open(OVERRIDES_PATH, "r") as f:
            overrides = json.load(f)
            overrides = {k.upper(): v for k, v in overrides.items()}
    except Exception:
        overrides = {}
    normalized = {w: normalize_token(w) for w in watch}

    # collect all candidate ids
    all_ids = set()
    entries = []
    for w in watch:
        norm = normalized[w]
        cands = candidates_map.get(w.upper(), []) or candidates_map.get(norm, [])
        entries.append((w, norm, cands))
        for c in cands:
            all_ids.add(c["id"])
        # include override id if present
        if w.upper() in overrides:
            all_ids.add(overrides[w.upper()])
        if norm in overrides:
            all_ids.add(overrides[norm])

    market_data = batch_markets(list(all_ids)) if all_ids else {}

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w", newline="") as csvf:
        writer = csv.writer(csvf)
        writer.writerow(["base", "normalized", "chosen_id", "chosen_name", "chosen_market_cap", "confidence", "reason", "candidates"])
        for w, norm, cands in entries:
            # if override exists, use it directly
            if w.upper() in overrides or norm in overrides:
                oid = overrides.get(w.upper()) or overrides.get(norm)
                m = market_data.get(oid)
                mc = m.get("market_cap") if m else None
                name = m.get("name") if m and m.get("name") else ""
                writer.writerow([w, norm, oid, name, mc or "", "high", "override", json.dumps([{"id": oid, "name": name, "market_cap": mc}])])
                continue

            if not cands:
                writer.writerow([w, norm, "", "", "", "none", "no_candidates", "[]"])
                continue

            # if single candidate, choose it
            if len(cands) == 1:
                cid = cands[0]["id"]
                m = market_data.get(cid, {})
                mc = m.get("market_cap") if m else None
                writer.writerow([w, norm, cid, cands[0]["name"], mc or "", "high", "unique_candidate", json.dumps(cands)])
                continue

            # multiple candidates: try price-match filter first
            best = None
            best_mc = -1
            cand_info = []
            for c in cands:
                cid = c["id"]
                m = market_data.get(cid)
                mc = m.get("market_cap") if m else None
                cp = m.get("current_price") if m else None
                cand_info.append({"id": cid, "name": c.get("name"), "market_cap": mc, "cg_price": cp})

            # attempt to get binance price for base; if unavailable, skip price-match
            binance_price = get_binance_spot_price_for_base(w)
            filtered = []
            if binance_price is not None:
                for c in cand_info:
                    cg_price = c.get("cg_price")
                    if cg_price is None:
                        continue
                    try:
                        diff = abs(binance_price - float(cg_price)) / (binance_price if binance_price else 1)
                    except Exception:
                        continue
                    if diff <= PRICE_MATCH_THRESHOLD:
                        filtered.append((c, diff))

            if filtered:
                # pick highest market cap among filtered
                filtered_sorted = sorted(filtered, key=lambda x: float(x[0].get("market_cap") or 0), reverse=True)
                chosen = filtered_sorted[0][0]
                best = {"id": chosen.get("id"), "name": chosen.get("name")}
                best_mc = chosen.get("market_cap") or 0
                confidence = "high"
                reason = f"price_matched_within_{int(PRICE_MATCH_THRESHOLD*100)}%"
            else:
                # fallback: choose highest market cap but mark price_mismatch if binance price existed
                for c in cand_info:
                    try:
                        mcv = float(c.get("market_cap") or 0)
                    except Exception:
                        mcv = -1
                    if mcv > best_mc:
                        best_mc = mcv
                        best = {"id": c.get("id"), "name": c.get("name")}
                if best_mc <= 0:
                    confidence = "none"
                    reason = "no_market_cap_candidates"
                else:
                    confidence = "medium"
                    reason = "chosen_by_highest_mc"
                    if binance_price is not None:
                        reason = "price_mismatch_but_highest_mc"

            writer.writerow([w, norm, best.get("id") if best else "", best.get("name") if best else "", best_mc if best_mc>0 else "", confidence, reason, json.dumps(cand_info)])

    print(f"Wrote mapping report to {OUT_CSV}")


if __name__ == "__main__":
    main()
