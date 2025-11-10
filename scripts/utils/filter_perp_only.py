#!/usr/bin/env python3
"""Filter aggregated_usdt.csv for rows that have a perp_price but no spot_price.

Outputs:
 - data/aggregated_usdt_perp_only.csv
 - data/aggregated_usdt_perp_only.json

Usage: python3 scripts/filter_perp_only.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / 'data' / 'aggregated_usdt.csv'
OUT_CSV = ROOT / 'data' / 'aggregated_usdt_perp_only.csv'
OUT_JSON = ROOT / 'data' / 'aggregated_usdt_perp_only.json'


def _parse_float(s):
    if s is None:
        return None
    s = str(s).strip()
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
            # keep rows where perp exists and spot is missing or not >0
            if perp_p is not None and (spot_p is None or spot_p <= 0):
                row['spot_price'] = spot_p
                row['perp_price'] = perp_p
                row['openInterest'] = _parse_float(row.get('openInterest'))
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

    with OUT_JSON.open('w', encoding='utf-8') as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)

    print(f'Kept {len(kept)} perp-only rows (perp present, spot missing/non-positive)')
    print(f'Wrote CSV: {OUT_CSV}')
    print(f'Wrote JSON: {OUT_JSON}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
