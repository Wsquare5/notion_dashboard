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
    """Build symbol->CMC id mapping with smart matching.
    
    Matching strategy:
    1. Exact symbol match - pick the one with highest market cap (lowest rank)
    2. For multiple matches, prefer active status
    3. Sort by market cap to ensure we pick the most significant coin
    """
    symbol_map = {}
    cmc_by_symbol = {}
    for item in cmc_list:
        sym = item.get('symbol', '').upper()
        if sym not in cmc_by_symbol:
            cmc_by_symbol[sym] = []
        cmc_by_symbol[sym].append(item)

    matched = 0
    mapping = {}
    match_details = []  # Track matching details for review
    
    for b in binance_symbols:
        candidates = cmc_by_symbol.get(b.upper(), [])
        if candidates:
            # Smart matching: prioritize by rank (market cap proxy) and active status
            active_candidates = [c for c in candidates if c.get('is_active') == 1]
            
            # If we have active candidates, use them; otherwise fall back to all
            pool = active_candidates if active_candidates else candidates
            
            # Sort by rank (lower rank = higher market cap = more significant)
            # Handle None ranks by putting them at the end
            best = sorted(pool, key=lambda x: (x.get('rank') or 999999))[0]
            
            mapping[b] = {
                'cmc_id': best.get('id'),
                'cmc_slug': best.get('slug'),
                'cmc_symbol': best.get('symbol'),
                'match_type': 'exact'
            }
            
            # Track details for review
            detail = {
                'symbol': b,
                'cmc_id': best.get('id'),
                'name': best.get('name'),
                'slug': best.get('slug'),
                'rank': best.get('rank'),
                'is_active': best.get('is_active'),
                'total_candidates': len(candidates),
                'active_candidates': len(active_candidates)
            }
            match_details.append(detail)
            
            matched += 1
        else:
            mapping[b] = {
                'cmc_id': None,
                'cmc_slug': None,
                'cmc_symbol': None,
                'match_type': 'none'
            }
    
    return mapping, matched, match_details


def save_mapping(mapping, match_details=None):
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
    
    # Save match details for review
    if match_details:
        # Sort by multiple candidates (potential issues) and then by rank
        review_candidates = [d for d in match_details if d['total_candidates'] > 1]
        review_candidates.sort(key=lambda x: (-x['total_candidates'], x['rank'] or 999999))
        
        review_out = {
            'metadata': {
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'note': 'Tokens with multiple CMC matches - review recommended'
            },
            'tokens': review_candidates
        }
        
        with open('cmc_mapping_review.json', 'w', encoding='utf-8') as f:
            json.dump(review_out, f, indent=2, ensure_ascii=False)
        
        if review_candidates:
            print(f'\n⚠️  {len(review_candidates)} tokens have multiple CMC matches')
            print('Review file created: cmc_mapping_review.json')
            print('\nTop 10 tokens to review (most candidates):')
            for d in review_candidates[:10]:
                print(f"  {d['symbol']:8} - {d['name']:30} (Rank: {d['rank'] or 'N/A':>6}) [{d['total_candidates']} candidates]")


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

    mapping, matched, match_details = build_mapping(coins, binance_symbols)
    print(f'Matched {matched}/{len(binance_symbols)}')

    save_mapping(mapping, match_details)

    # Print unmatched
    unmatched = [s for s, info in mapping.items() if not info['cmc_id']]
    if unmatched:
        print(f'\n❌ {len(unmatched)} unmatched tokens:')
        print(', '.join(unmatched[:20]))
        if len(unmatched) > 20:
            print(f'   ... and {len(unmatched) - 20} more')
