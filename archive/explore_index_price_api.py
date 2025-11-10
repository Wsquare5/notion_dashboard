#!/usr/bin/env python3
"""探索Binance API中关于指数价格组成的信息"""

import requests
import json
from pprint import pprint

def test_binance_endpoints():
    """测试各种可能包含指数价格组成信息的端点"""
    
    base_url = "https://fapi.binance.com"
    symbol = "BTCUSDT"
    
    endpoints_to_test = [
        # 标准的premium index端点
        f"/fapi/v1/premiumIndex?symbol={symbol}",
        
        # 可能的指数价格组成端点
        f"/fapi/v1/indexPriceConstituents?symbol={symbol}",
        f"/fapi/v1/indexInfo?symbol={symbol}",
        f"/fapi/v1/indexPrice?symbol={symbol}",
        f"/fapi/v1/constituents?symbol={symbol}",
        
        # 通用信息端点
        f"/fapi/v1/exchangeInfo",
    ]
    
    print("=== 测试Binance期货API端点 ===\n")
    
    for endpoint in endpoints_to_test:
        print(f"测试端点: {endpoint}")
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if endpoint.endswith("exchangeInfo"):
                    # 对于exchangeInfo，只显示部分信息
                    print(f"响应: 包含 {len(data.get('symbols', []))} 个交易对")
                    # 查看是否有关于指数的信息
                    if 'symbols' in data:
                        btc_symbol = next((s for s in data['symbols'] if s['symbol'] == symbol), None)
                        if btc_symbol:
                            print("BTC交易对信息:")
                            for key in ['baseAsset', 'quoteAsset', 'status', 'contractType']:
                                if key in btc_symbol:
                                    print(f"  {key}: {btc_symbol[key]}")
                else:
                    print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
            else:
                print(f"错误: {response.text}")
                
        except Exception as e:
            print(f"请求失败: {e}")
        
        print("-" * 50)
    
    # 测试我们的broccoli代币
    print("\n=== 测试BROCCOLI714指数价格信息 ===")
    broccoli_symbol = "BROCCOLI714USDT"
    
    try:
        response = requests.get(f"{base_url}/fapi/v1/premiumIndex?symbol={broccoli_symbol}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"BROCCOLI714 premium index数据:")
            pprint(data)
        else:
            print(f"获取BROCCOLI714数据失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"请求BROCCOLI714数据失败: {e}")

def check_spot_exchanges():
    """检查现货市场可能的指数组成来源"""
    print("\n=== 检查现货市场数据来源 ===")
    
    # Binance现货API
    spot_url = "https://api.binance.com"
    
    try:
        # 获取现货价格
        response = requests.get(f"{spot_url}/api/v3/ticker/price?symbol=BTCUSDT", timeout=10)
        if response.status_code == 200:
            spot_data = response.json()
            print(f"Binance现货BTC价格: {spot_data}")
        
        # 获取现货交易对信息
        response = requests.get(f"{spot_url}/api/v3/exchangeInfo", timeout=10)
        if response.status_code == 200:
            exchange_info = response.json()
            btc_spot = next((s for s in exchange_info['symbols'] if s['symbol'] == 'BTCUSDT'), None)
            if btc_spot:
                print(f"BTC现货交易对状态: {btc_spot['status']}")
        
    except Exception as e:
        print(f"获取现货数据失败: {e}")

if __name__ == "__main__":
    test_binance_endpoints()
    check_spot_exchanges()