#!/usr/bin/env python3
"""
调试 fetch_perp_only_data.py 的问题
"""

import requests
import time
import sys
import traceback

def test_perp_token_count():
    """测试获取只有期货的代币数量"""
    print("🔍 测试获取只有期货的代币数量...")
    
    try:
        # Get all USDT trading pairs
        print("  - 获取现货市场数据...")
        spot_response = requests.get('https://api.binance.com/api/v3/exchangeInfo', timeout=10)
        print(f"  - 现货API状态: {spot_response.status_code}")
        
        print("  - 获取期货市场数据...")
        perp_response = requests.get('https://fapi.binance.com/fapi/v1/exchangeInfo', timeout=10)
        print(f"  - 期货API状态: {perp_response.status_code}")
        
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
        
        # Find tokens that have only perpetual markets
        perp_only = perp_symbols - spot_symbols
        perp_only_list = sorted(list(perp_only))
        
        print(f"📊 现货交易对: {len(spot_symbols)}")
        print(f"📊 期货交易对: {len(perp_symbols)}")
        print(f"📊 只有期货的代币: {len(perp_only_list)}")
        
        # 显示前10个
        print(f"📋 前10个只有期货的代币: {perp_only_list[:10]}")
        
        return perp_only_list
        
    except Exception as e:
        print(f"❌ 获取代币列表失败: {e}")
        traceback.print_exc()
        return []

def test_batch_apis(symbols):
    """测试批量API调用"""
    print(f"\n🧪 测试批量API调用 (前5个代币)...")
    
    test_symbols = symbols[:5] if len(symbols) >= 5 else symbols
    print(f"测试代币: {test_symbols}")
    
    try:
        # 1. Test 24hr ticker
        print("  - 测试24小时行情API...")
        ticker_url = 'https://fapi.binance.com/fapi/v1/ticker/24hr'
        start_time = time.time()
        ticker_response = requests.get(ticker_url, timeout=30)
        ticker_time = time.time() - start_time
        print(f"    状态: {ticker_response.status_code}, 耗时: {ticker_time:.2f}秒")
        print(f"    数据量: {len(ticker_response.json())} 个交易对")
        
        # 2. Test funding rate
        print("  - 测试资金费率API...")
        funding_url = 'https://fapi.binance.com/fapi/v1/premiumIndex'
        start_time = time.time()
        funding_response = requests.get(funding_url, timeout=30)
        funding_time = time.time() - start_time
        print(f"    状态: {funding_response.status_code}, 耗时: {funding_time:.2f}秒")
        print(f"    数据量: {len(funding_response.json())} 个交易对")
        
        return True
        
    except Exception as e:
        print(f"❌ 批量API测试失败: {e}")
        traceback.print_exc()
        return False

def test_individual_oi_calls(symbols):
    """测试单独的持仓量API调用"""
    print(f"\n🔍 测试单独的持仓量API调用...")
    
    test_symbols = symbols[:3] if len(symbols) >= 3 else symbols
    
    for i, symbol in enumerate(test_symbols, 1):
        symbol_usdt = f"{symbol}USDT"
        print(f"  ({i}/{len(test_symbols)}) 测试 {symbol_usdt}...")
        
        try:
            start_time = time.time()
            oi_url = f'https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol_usdt}'
            oi_response = requests.get(oi_url, timeout=10)
            oi_time = time.time() - start_time
            
            if oi_response.status_code == 200:
                oi_data = oi_response.json()
                print(f"    ✅ 成功 - 耗时: {oi_time:.2f}秒, OI: {oi_data.get('openInterest', 'N/A')}")
            else:
                print(f"    ❌ 失败 - 状态码: {oi_response.status_code}")
                
        except Exception as e:
            print(f"    ❌ 异常: {e}")
        
        time.sleep(0.2)  # Rate limiting

def test_index_composition_calls(symbols):
    """测试指数组成API调用 - 这可能是最慢的部分"""
    print(f"\n📊 测试指数组成API调用...")
    
    test_symbols = symbols[:3] if len(symbols) >= 3 else symbols
    
    for i, symbol in enumerate(test_symbols, 1):
        symbol_usdt = f"{symbol}USDT"
        print(f"  ({i}/{len(test_symbols)}) 测试 {symbol_usdt} 指数组成...")
        
        try:
            start_time = time.time()
            url = f'https://fapi.binance.com/fapi/v1/constituents?symbol={symbol_usdt}'
            response = requests.get(url, timeout=15)
            api_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                constituents = data.get('constituents', [])
                print(f"    ✅ 成功 - 耗时: {api_time:.2f}秒, 组成: {len(constituents)} 个交易所")
                if constituents:
                    exchanges = [c.get('exchange', 'Unknown') for c in constituents[:3]]
                    print(f"    交易所: {', '.join(exchanges)}")
            else:
                print(f"    ❌ 失败 - 状态码: {response.status_code}")
                if response.status_code == 429:
                    print(f"    限速错误，等待...")
                    time.sleep(5)
                    
        except Exception as e:
            print(f"    ❌ 异常: {e}")
        
        time.sleep(1)  # 更长的延迟，避免限速

if __name__ == "__main__":
    print("🚀 开始调试 fetch_perp_only_data.py...")
    
    # 1. 测试获取代币列表
    perp_tokens = test_perp_token_count()
    
    if not perp_tokens:
        print("❌ 无法获取代币列表，退出")
        sys.exit(1)
    
    # 2. 测试批量API
    if not test_batch_apis(perp_tokens):
        print("❌ 批量API测试失败，退出")
        sys.exit(1)
    
    # 3. 测试单独持仓量调用
    test_individual_oi_calls(perp_tokens)
    
    # 4. 测试指数组成调用 (最可能卡住的地方)
    test_index_composition_calls(perp_tokens)
    
    print("\n✅ 调试完成！")