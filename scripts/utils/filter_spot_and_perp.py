#!/usr/bin/env python3
"""Filter aggregated_usdt.csv for rows that have both spot_price and perp_price.

Outputs:
 - data/aggregated_usdt_spot_and_perp.csv
 - data/aggregated_usdt_spot_and_perp.json

Usage: run from repo root: python3 scripts/filter_spot_and_perp.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / 'data' / 'aggregated_usdt.csv'
OUT_CSV = ROOT / 'data' / 'aggregated_usdt_spot_and_perp.csv'
OUT_JSON = ROOT / 'data' / 'aggregated_usdt_spot_and_perp.json'


def _parse_float(s):
    if s is None:
        return None
    s = s.strip()
    if s == '':
        return None
    try:
        return float(s)
    except Exception:
        return None


def main():
    if not IN_CSV.exists():
        print(f'Input file not found: {IN_CSV}')
        return 1

    kept = []
    with IN_CSV.open('r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            spot_p = _parse_float(row.get('spot_price'))
            perp_p = _parse_float(row.get('perp_price'))
            # keep rows where both prices exist and > 0
            if spot_p is not None and perp_p is not None and spot_p > 0 and perp_p > 0:
                # normalize numeric fields
                row['spot_price'] = spot_p
                row['perp_price'] = perp_p
                # openInterest may be empty
                oi = _parse_float(row.get('openInterest'))
                row['openInterest'] = oi
                # market_cap and fdv may be empty
                row['market_cap'] = _parse_float(row.get('market_cap'))
                row['fdv'] = _parse_float(row.get('fdv'))
                kept.append(row)

    # write CSV
    if kept:
        fieldnames = list(kept[0].keys())
    else:
        fieldnames = ['base','spot_price','perp_price','openInterest','market_cap','fdv']

    with OUT_CSV.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in kept:
            writer.writerow(r)

    # write JSON
    with OUT_JSON.open('w', encoding='utf-8') as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)

    print(f'Kept {len(kept)} rows with both spot and perp prices')
    print(f'Wrote CSV: {OUT_CSV}')
    print(f'Wrote JSON: {OUT_JSON}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
