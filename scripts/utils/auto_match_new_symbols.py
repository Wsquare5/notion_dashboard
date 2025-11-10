#!/usr/bin/env python3
"""
自动匹配新上市的 Binance 合约到 CoinMarketCap
"""

import requests
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

# Configuration
ROOT = Path(__file__).resolve().parents[1]
CMC_MAPPING_FILE = ROOT / 'binance_cmc_mapping.json'
API_CONFIG_FILE = ROOT / 'api_config.json'


class CMCMatcher:
    """CoinMarketCap symbol matcher"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://pro-api.coinmarketcap.com/v1"
        self.headers = {
            'X-CMC_PRO_API_KEY': api_key,
            'Accept': 'application/json'
        }
    
    def search_symbol(self, symbol: str) -> Optional[Dict]:
        """
        Search for a symbol in CoinMarketCap
        Returns the best match or None
        """
        try:
            # Method 1: Try exact match with map endpoint
            url = f"{self.base_url}/cryptocurrency/map"
            params = {'symbol': symbol, 'limit': 10}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status', {}).get('error_code') == 0:
                matches = data.get('data', [])
                
                if matches:
                    # Prefer active coins over inactive ones
                    active_matches = [m for m in matches if m.get('is_active') == 1]
                    if active_matches:
                        best_match = active_matches[0]
                    else:
                        best_match = matches[0]
                    
                    return {
                        'cmc_id': best_match['id'],
                        'cmc_slug': best_match['slug'],
                        'cmc_symbol': best_match['symbol'],
                        'match_type': 'auto'
                    }
            
            return None
            
        except Exception as e:
            print(f"  ⚠️  CMC search failed: {e}")
            return None


def get_binance_symbols() -> Dict[str, str]:
    """Get all trading symbols from Binance (spot + perp)"""
    symbols = {}
    
    try:
        # Get perpetual contracts
        print("📡 获取 Binance 永续合约列表...")
        perp_response = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo", timeout=10)
        perp_response.raise_for_status()
        
        for s in perp_response.json()['symbols']:
            if s['symbol'].endswith('USDT') and s['status'] == 'TRADING':
                symbol = s['symbol'].replace('USDT', '')
                symbols[symbol] = 'perp'
        
        print(f"  ✅ 找到 {len([s for s in symbols.values() if s == 'perp'])} 个永续合约")
        
        # Get spot markets
        print("📡 获取 Binance 现货列表...")
        spot_response = requests.get("https://api.binance.com/api/v3/exchangeInfo", timeout=10)
        spot_response.raise_for_status()
        
        for s in spot_response.json()['symbols']:
            if s['symbol'].endswith('USDT') and s['status'] == 'TRADING':
                symbol = s['symbol'].replace('USDT', '')
                if symbol in symbols:
                    symbols[symbol] = 'both'
                else:
                    symbols[symbol] = 'spot'
        
        print(f"  ✅ 找到 {len([s for s in symbols.values() if s == 'spot'])} 个现货")
        print(f"  ✅ 找到 {len([s for s in symbols.values() if s == 'both'])} 个同时有现货和合约")
        
        return symbols
        
    except Exception as e:
        print(f"❌ 获取 Binance 数据失败: {e}")
        return {}


def load_existing_mapping() -> Dict:
    """Load existing CMC mapping"""
    if CMC_MAPPING_FILE.exists():
        with open(CMC_MAPPING_FILE) as f:
            data = json.load(f)
            return data.get('mapping', {})
    return {}


def save_mapping(mapping: Dict):
    """Save updated mapping to file"""
    data = {
        "metadata": {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_symbols": len(mapping)
        },
        "mapping": mapping
    }
    
    with open(CMC_MAPPING_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 已保存到 {CMC_MAPPING_FILE}")


def main():
    """Main function"""
    print("🔍 自动匹配 Binance 新币种到 CoinMarketCap\n")
    
    # Load API key
    if not API_CONFIG_FILE.exists():
        print(f"❌ 找不到 API 配置文件: {API_CONFIG_FILE}")
        return
    
    with open(API_CONFIG_FILE) as f:
        api_config = json.load(f)
        cmc_api_key = api_config.get('coinmarketcap', {}).get('api_key')
    
    if not cmc_api_key:
        print("❌ CMC API key 未配置")
        return
    
    # Initialize matcher
    matcher = CMCMatcher(cmc_api_key)
    
    # Get Binance symbols
    binance_symbols = get_binance_symbols()
    if not binance_symbols:
        return
    
    # Load existing mapping
    existing_mapping = load_existing_mapping()
    print(f"\n📋 现有 mapping 中有 {len(existing_mapping)} 个币种")
    
    # Find new symbols
    new_symbols = []
    missing_cmc_id = []
    
    for symbol in sorted(binance_symbols.keys()):
        if symbol not in existing_mapping:
            new_symbols.append(symbol)
        elif not existing_mapping[symbol].get('cmc_id'):
            missing_cmc_id.append(symbol)
    
    print(f"🆕 发现 {len(new_symbols)} 个新币种")
    print(f"⚠️  {len(missing_cmc_id)} 个币种缺少 CMC ID")
    
    if not new_symbols and not missing_cmc_id:
        print("\n✅ 所有币种都已有 CMC mapping！")
        return
    
    # Process new symbols
    symbols_to_match = new_symbols + missing_cmc_id
    print(f"\n🔄 开始匹配 {len(symbols_to_match)} 个币种...\n")
    
    matched = 0
    failed = []
    
    for i, symbol in enumerate(symbols_to_match, 1):
        print(f"[{i:3d}/{len(symbols_to_match):3d}] {symbol}", end=" ")
        
        # Search in CMC
        match = matcher.search_symbol(symbol)
        
        if match:
            existing_mapping[symbol] = match
            matched += 1
            print(f"✅ 找到: {match['cmc_slug']} (ID: {match['cmc_id']})")
        else:
            existing_mapping[symbol] = {
                'cmc_id': None,
                'cmc_slug': None,
                'cmc_symbol': None,
                'match_type': 'none'
            }
            failed.append(symbol)
            print(f"❌ 未找到")
        
        # Rate limiting: wait 0.3s between requests
        if i < len(symbols_to_match):
            time.sleep(0.3)
    
    # Save updated mapping
    save_mapping(existing_mapping)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"✅ 成功匹配: {matched} 个")
    print(f"❌ 未找到: {len(failed)} 个")
    
    if failed:
        print(f"\n未找到 CMC 数据的币种:")
        print(f"  {', '.join(failed)}")
        print(f"\n💡 这些币种可能:")
        print(f"  1. 在 CMC 上没有上市")
        print(f"  2. 是 Binance 特殊合约（如 1000X 系列）")
        print(f"  3. 需要手动匹配")


if __name__ == "__main__":
    main()
