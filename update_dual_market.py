#!/usr/bin/env python3
"""
更新双市场代币数据
"""

import sys
import os
sys.path.append('scripts')

from enhanced_data_fetcher import fetch_enhanced_data
import requests
import json
from dataclasses import asdict

def get_dual_market_tokens():
    """获取双市场代币列表"""
    print("🔍 获取双市场代币列表...")
    
    # Get all USDT trading pairs
    spot_response = requests.get('https://api.binance.com/api/v3/exchangeInfo')
    perp_response = requests.get('https://fapi.binance.com/fapi/v1/exchangeInfo')
    
    spot_data = spot_response.json()
    perp_data = perp_response.json()
    
    # Extract active USDT pairs
    spot_symbols = set()
    for symbol_info in spot_data['symbols']:
        if symbol_info['symbol'].endswith('USDT') and symbol_info['status'] == 'TRADING':
            base = symbol_info['baseAsset']
            spot_symbols.add(base)
    
    perp_symbols = set()
    for symbol_info in perp_data['symbols']:
        if symbol_info['symbol'].endswith('USDT') and symbol_info['status'] == 'TRADING':
            base = symbol_info['baseAsset']
            perp_symbols.add(base)
    
    # Find tokens that have both spot and perp markets
    dual_market = spot_symbols & perp_symbols
    dual_market_list = sorted(list(dual_market))
    
    print(f"📊 现货交易对: {len(spot_symbols)}")
    print(f"📊 期货交易对: {len(perp_symbols)}")
    print(f"📊 双市场代币: {len(dual_market_list)}")
    
    return dual_market_list

if __name__ == "__main__":
    try:
        # Get dual market tokens
        dual_tokens = get_dual_market_tokens()
        
        # Update first 50 tokens
        print(f"🚀 开始更新前50个双市场代币...")
        test_symbols = dual_tokens[:50]
        
        data = fetch_enhanced_data(test_symbols)
        print(f"✅ 成功获取 {len(data)} 个双市场代币数据")
        
        # Save to file
        data_dicts = [asdict(token) for token in data]
        
        os.makedirs('data', exist_ok=True)
        with open('data/dual_market_50.json', 'w', encoding='utf-8') as f:
            json.dump(data_dicts, f, indent=2, ensure_ascii=False)
        
        print("💾 数据已保存到: data/dual_market_50.json")
        
        # Show summary
        print(f"\n📊 数据摘要:")
        print(f"  代币数量: {len(data)}")
        print(f"  有现货价格: {sum(1 for t in data if t.spot_price)}")
        print(f"  有期货价格: {sum(1 for t in data if t.perp_price)}")
        print(f"  有资金费率: {sum(1 for t in data if t.funding_rate)}")
        
        print(f"\n💡 前5个代币示例:")
        for i, token in enumerate(data[:5], 1):
            spot = f"${token.spot_price:.4f}" if token.spot_price else "N/A"
            perp = f"${token.perp_price:.4f}" if token.perp_price else "N/A"
            funding = f"{token.funding_rate*100:.4f}%" if token.funding_rate else "N/A"
            print(f"  {i}. {token.base}: 现货{spot}, 期货{perp}, 资金费率{funding}")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()