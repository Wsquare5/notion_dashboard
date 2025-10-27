#!/usr/bin/env python3
"""
创建Binance到CoinMarketCap ID的本地映射文件
使用 CoinMarketCap Professional API (/v1/cryptocurrency/map) 分页获取整个代币列表
"""

import requests
import json
import time
from pathlib import Path

CONFIG_FILE = Path('api_config.json')


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def fetch_cmc_map(api_key: str) -> list:
    """Fetch the /v1/cryptocurrency/map endpoint (paginated)"""
    base_url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/map'
    headers = {'X-CMC_PRO_API_KEY': api_key}

    start = 1
    limit = 100
    all_coins = []

    while True:
        params = {'start': start, 'limit': limit}
        print(f"Fetching CMC map start={start} limit={limit}...")
        resp = requests.get(base_url, headers=headers, params=params, timeout=15)
        if resp.status_code != 200:
            print(f"Error fetching CMC map: {resp.status_code} {resp.text}")
            break
        data = resp.json()
        if 'data' not in data:
            break
        batch = data['data']
        all_coins.extend(batch)
        if len(batch) < limit:
            break
        start += limit
        time.sleep(1)  # modest delay
    return all_coins


def get_binance_symbols():
    """Get all Binance USDT base assets from spot and perp exchangeInfo"""
    spot = requests.get('https://api.binance.com/api/v3/exchangeInfo', timeout=15).json()
    perp = requests.get('https://fapi.binance.com/fapi/v1/exchangeInfo', timeout=15).json()

    symbols = set()
    for s in spot['symbols']:
        if s['symbol'].endswith('USDT') and s['status'] == 'TRADING':
            symbols.add(s['baseAsset'])
    for s in perp['symbols']:
        if s['symbol'].endswith('USDT') and s['status'] == 'TRADING':
            symbols.add(s['baseAsset'])
    return sorted(list(symbols))


def build_mapping(cmc_list, binance_symbols):
    """Build symbol->CMC id mapping by symbol match. If multiple CMC entries share the same symbol, pick the highest market cap rank if available."""
    symbol_map = {}
    cmc_by_symbol = {}
    for item in cmc_list:
        sym = item.get('symbol', '').upper()
        if sym not in cmc_by_symbol:
            cmc_by_symbol[sym] = []
        cmc_by_symbol[sym].append(item)

    matched = 0
    mapping = {}
    for b in binance_symbols:
        candidates = cmc_by_symbol.get(b.upper(), [])
        if candidates:
            # prefer the one with lowest cmc_rank if available
            best = sorted(candidates, key=lambda x: (x.get('cmc_rank') or 1e9))[0]
            mapping[b] = {
                'cmc_id': best.get('id'),
                'cmc_slug': best.get('slug'),
                'cmc_symbol': best.get('symbol'),
                'match_type': 'exact'
            }
            matched += 1
        else:
            mapping[b] = {
                'cmc_id': None,
                'cmc_slug': None,
                'cmc_symbol': None,
                'match_type': 'none'
            }
    return mapping, matched


def save_mapping(mapping):
    out = {
        'metadata': {
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_symbols': len(mapping)
        },
        'mapping': mapping
    }
    with open('binance_cmc_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print('Saved mapping to binance_cmc_mapping.json')


if __name__ == '__main__':
    cfg = load_config()
    cmc_key = cfg.get('coinmarketcap', {}).get('api_key')
    if not cmc_key:
        print('CoinMarketCap API key missing in api_config.json')
        raise SystemExit(1)

    print('Fetching CoinMarketCap map (this may take a while)...')
    coins = fetch_cmc_map(cmc_key)
    print(f'Fetched {len(coins)} CMC entries')

    binance_symbols = get_binance_symbols()
    print(f'Binance symbols: {len(binance_symbols)}')

    mapping, matched = build_mapping(coins, binance_symbols)
    print(f'Matched {matched}/{len(binance_symbols)}')

    save_mapping(mapping)

    # Print unmatched
    unmatched = [s for s, info in mapping.items() if not info['cmc_id']]
    print('Unmatched tokens:')
    print(unmatched)
