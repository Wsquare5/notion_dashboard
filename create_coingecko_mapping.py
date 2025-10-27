#!/usr/bin/env python3
"""
创建Binance代币到CoinGecko ID的本地映射文件
这样可以避免每次都重新匹配，进一步提升性能
"""

import requests
import json
import time
from pathlib import Path

def create_binance_coingecko_mapping():
    """创建Binance代币到CoinGecko ID的映射并保存到本地"""
    
    print("🔍 获取Binance交易对...")
    
    # Get Binance symbols
    spot_response = requests.get('https://api.binance.com/api/v3/exchangeInfo')
    perp_response = requests.get('https://fapi.binance.com/fapi/v1/exchangeInfo')
    
    spot_data = spot_response.json()
    perp_data = perp_response.json()
    
    # Extract all USDT symbols
    binance_symbols = set()
    for symbol_info in spot_data['symbols']:
        if symbol_info['symbol'].endswith('USDT') and symbol_info['status'] == 'TRADING':
            binance_symbols.add(symbol_info['baseAsset'])
    
    for symbol_info in perp_data['symbols']:
        if symbol_info['symbol'].endswith('USDT') and symbol_info['status'] == 'TRADING':
            binance_symbols.add(symbol_info['baseAsset'])
    
    binance_symbols = sorted(list(binance_symbols))
    print(f"📊 找到 {len(binance_symbols)} 个Binance代币")
    
    # Get CoinGecko coins list
    print("📥 获取CoinGecko代币列表...")
    time.sleep(2)
    
    cg_response = requests.get('https://api.coingecko.com/api/v3/coins/list', timeout=15)
    if cg_response.status_code != 200:
        print(f"❌ 获取CoinGecko列表失败: {cg_response.status_code}")
        return
    
    coingecko_coins = cg_response.json()
    print(f"📊 获取到 {len(coingecko_coins)} 个CoinGecko代币")
    
    # Create symbol to ID mapping
    cg_symbol_map = {}
    for coin in coingecko_coins:
        symbol = coin['symbol'].upper()
        if symbol not in cg_symbol_map:
            cg_symbol_map[symbol] = []
        cg_symbol_map[symbol].append({
            'id': coin['id'],
            'name': coin['name'],
            'symbol': coin['symbol']
        })
    
    # Match Binance symbols to CoinGecko IDs
    print("🔗 匹配Binance代币到CoinGecko...")
    
    # Enhanced major coins mapping
    major_coins = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'BNB': 'binancecoin',
        'SOL': 'solana',
        'XRP': 'ripple',
        'ADA': 'cardano',
        'AVAX': 'avalanche-2',
        'DOT': 'polkadot',
        'MATIC': 'matic-network',
        'LINK': 'chainlink',
        'UNI': 'uniswap',
        'LTC': 'litecoin',
        'BCH': 'bitcoin-cash',
        'NEAR': 'near',
        'ATOM': 'cosmos',
        'FTM': 'fantom',
        'ALGO': 'algorand',
        'VET': 'vechain',
        'ICP': 'internet-computer',
        'HBAR': 'hedera-hashgraph',
        'ETC': 'ethereum-classic',
        'FIL': 'filecoin',
        'THETA': 'theta-token',
        'XLM': 'stellar',
        'TRX': 'tron',
        'AAVE': 'aave',
        'MKR': 'maker',
        'SNX': 'havven',
        'COMP': 'compound-governance-token',
        'YFI': 'yearn-finance',
        'DOGE': 'dogecoin',
        'SHIB': 'shiba-inu',
        'PEPE': 'pepe',
        'WIF': 'dogwifcoin',
        'FLOKI': 'floki',
        'BONK': 'bonk',
        'MEME': 'memecoin',
        'WLD': 'worldcoin-wld',
        'ORDI': 'ordinals',
        'SATS': '1000sats',
        'RATS': 'rats',
        'AI': 'sleepless-ai',
        'ID': 'space-id',
        'ARB': 'arbitrum',
        'OP': 'optimism',
        'APT': 'aptos',
        'SUI': 'sui',
        'INJ': 'injective-protocol',
        'SEI': 'sei-network',
        'STRK': 'starknet',
        'TIA': 'celestia',
        'PYTH': 'pyth-network',
        'JTO': 'jito-governance-token',
        'MANTA': 'manta-network',
        'ALT': 'altlayer',
        'JUP': 'jupiter-exchange-solana',
        'DYM': 'dymension',
        'PIXEL': 'pixels',
        'PORTAL': 'portal',
        'WEN': 'wen-4',
        'METIS': 'metis-token',
        'AEVO': 'aevo-exchange',
        'BOME': 'book-of-meme',
        'SAGA': 'saga-2',
        'TAO': 'bittensor',
        'OMNI': 'omni-network',
        'REZ': 'renzo',
        'IO': 'io-net',
        'ZK': 'zksync',
        'ZRO': 'layerzero',
        'G': 'gravity',
        'BANANA': 'banana-gun',
        'RENDER': 'render-token',
        'THETA': 'theta-token',
        'RUNE': 'thorchain',
        'FTT': 'ftx-token',
        'KCS': 'kucoin-shares',
        'GT': 'gatechain-token'
    }
    
    mapping_results = {}
    matched_count = 0
    
    for symbol in binance_symbols:
        coingecko_id = None
        match_type = "none"
        
        # Check major coins first
        if symbol.upper() in major_coins:
            coingecko_id = major_coins[symbol.upper()]
            match_type = "major"
            matched_count += 1
        else:
            # Try symbol matching with variations
            search_symbols = [symbol.upper()]
            
            # Handle special prefixes
            if symbol.upper().startswith('1000'):
                search_symbols.append(symbol[4:].upper())  # 1000SATS -> SATS
            elif symbol.upper().startswith('1M'):
                search_symbols.append(symbol[2:].upper())  # 1MBABYDOGE -> BABYDOGE
            
            # Search in CoinGecko
            for search_symbol in search_symbols:
                if search_symbol in cg_symbol_map:
                    candidates = cg_symbol_map[search_symbol]
                    if len(candidates) == 1:
                        coingecko_id = candidates[0]['id']
                        match_type = "exact"
                        matched_count += 1
                        break
                    else:
                        # Multiple matches - take first one (could be improved)
                        coingecko_id = candidates[0]['id']
                        match_type = "multiple"
                        matched_count += 1
                        break
        
        mapping_results[symbol] = {
            'coingecko_id': coingecko_id,
            'match_type': match_type,
            'timestamp': time.time()
        }
        
        if coingecko_id:
            print(f"✅ {symbol} -> {coingecko_id} ({match_type})")
        else:
            print(f"❌ {symbol} -> 无匹配")
    
    print(f"\n📊 匹配统计:")
    print(f"  总代币数: {len(binance_symbols)}")
    print(f"  匹配成功: {matched_count}")
    print(f"  匹配率: {matched_count/len(binance_symbols)*100:.1f}%")
    
    # Save to file
    output_file = Path('binance_coingecko_mapping.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_symbols': len(binance_symbols),
                'matched_symbols': matched_count,
                'match_rate': matched_count/len(binance_symbols)*100
            },
            'mapping': mapping_results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"💾 映射文件已保存到: {output_file}")
    print(f"📄 文件大小: {output_file.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    create_binance_coingecko_mapping()