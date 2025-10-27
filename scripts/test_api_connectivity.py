#!/usr/bin/env python3
"""
简化版本的数据获取脚本，处理网络连接问题
"""

import requests
import json
import time
from typing import Dict, List, Optional

def safe_request(url: str, max_retries: int = 3, timeout: int = 10) -> Optional[Dict]:
    """安全的HTTP请求，带重试机制"""
    for attempt in range(max_retries):
        try:
            print(f"  尝试请求 ({attempt + 1}/{max_retries}): {url}")
            response = requests.get(url, timeout=timeout)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                wait_time = (attempt + 1) * 5
                print(f"  限速，等待 {wait_time} 秒...")
                time.sleep(wait_time)
            else:
                print(f"  HTTP错误: {response.status_code}")
                return None
                
        except requests.exceptions.ProxyError as e:
            print(f"  代理错误 (尝试 {attempt + 1}): {e}")
            time.sleep((attempt + 1) * 2)
        except requests.exceptions.ConnectionError as e:
            print(f"  连接错误 (尝试 {attempt + 1}): {e}")
            time.sleep((attempt + 1) * 2)
        except requests.exceptions.Timeout as e:
            print(f"  超时错误 (尝试 {attempt + 1}): {e}")
            time.sleep((attempt + 1) * 2)
        except Exception as e:
            print(f"  其他错误 (尝试 {attempt + 1}): {e}")
            time.sleep(1)
    
    print(f"  ❌ 所有重试失败: {url}")
    return None

def test_api_connectivity():
    """测试API连通性"""
    print("🔍 测试API连通性...")
    
    apis = {
        "现货API": "https://api.binance.com/api/v3/ping",
        "期货API": "https://fapi.binance.com/fapi/v1/ping", 
        "现货时间": "https://api.binance.com/api/v3/time",
        "期货时间": "https://fapi.binance.com/fapi/v1/time"
    }
    
    results = {}
    for name, url in apis.items():
        result = safe_request(url, max_retries=2, timeout=5)
        results[name] = result is not None
        print(f"  {name}: {'✅' if results[name] else '❌'}")
        time.sleep(1)
    
    return results

def get_spot_data(symbol: str) -> Optional[Dict]:
    """获取现货数据"""
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT"
    data = safe_request(url)
    
    if data:
        return {
            "price": float(data.get("lastPrice", 0)),
            "change_24h": float(data.get("priceChangePercent", 0)),
            "volume_24h": float(data.get("quoteVolume", 0)),
            "high_24h": float(data.get("highPrice", 0)),
            "low_24h": float(data.get("lowPrice", 0))
        }
    return None

def get_perp_data(symbol: str) -> Optional[Dict]:
    """获取期货数据"""
    symbol_usdt = f"{symbol}USDT"
    
    # 获取期货24h数据
    ticker_url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol_usdt}"
    ticker_data = safe_request(ticker_url)
    
    if not ticker_data:
        return None
    
    result = {
        "price": float(ticker_data.get("lastPrice", 0)),
        "change_24h": float(ticker_data.get("priceChangePercent", 0)),
        "volume_24h": float(ticker_data.get("quoteVolume", 0)),
        "high_24h": float(ticker_data.get("highPrice", 0)),
        "low_24h": float(ticker_data.get("lowPrice", 0))
    }
    
    # 获取OI数据
    oi_url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol_usdt}"
    oi_data = safe_request(oi_url)
    if oi_data:
        result["open_interest"] = float(oi_data.get("openInterest", 0))
    
    # 获取资金费率和价格数据
    premium_url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol_usdt}"
    premium_data = safe_request(premium_url)
    if premium_data:
        result["funding_rate"] = float(premium_data.get("lastFundingRate", 0))
        result["mark_price"] = float(premium_data.get("markPrice", 0))
        result["index_price"] = float(premium_data.get("indexPrice", 0))
    
    return result

def calculate_funding_cycle(symbol: str) -> int:
    """计算费率周期"""
    try:
        url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}USDT&limit=3"
        data = safe_request(url)
        
        if data and len(data) >= 2:
            timestamp1 = int(data[0]['fundingTime'])
            timestamp2 = int(data[1]['fundingTime'])
            
            interval_ms = abs(timestamp1 - timestamp2)
            interval_hours = interval_ms / (1000 * 60 * 60)
            
            if 7.5 <= interval_hours <= 8.5:
                return 8
            elif 3.5 <= interval_hours <= 4.5:
                return 4  
            elif 5.5 <= interval_hours <= 6.5:
                return 6
            else:
                return 8
        else:
            return 8
    except:
        return 8

def test_single_token(symbol: str):
    """测试单个代币的数据获取"""
    print(f"\n🔍 测试 {symbol} 数据获取:")
    
    # 测试现货数据
    print("  获取现货数据...")
    spot_data = get_spot_data(symbol)
    if spot_data:
        print(f"    ✅ 现货价格: ${spot_data['price']:.4f}")
        print(f"    📈 24h变化: {spot_data['change_24h']:+.2f}%")
        print(f"    💰 24h交易额: ${spot_data['volume_24h']:,.0f}")
    else:
        print("    ❌ 现货数据获取失败")
    
    # 测试期货数据
    print("  获取期货数据...")
    perp_data = get_perp_data(symbol)
    if perp_data:
        print(f"    ✅ 期货价格: ${perp_data['price']:.4f}")
        print(f"    📈 24h变化: {perp_data['change_24h']:+.2f}%")
        print(f"    💰 24h交易额: ${perp_data['volume_24h']:,.0f}")
        if 'open_interest' in perp_data:
            oi_usd = perp_data['open_interest'] * perp_data['price']
            print(f"    📊 开仓量: ${oi_usd:,.0f}")
        if 'funding_rate' in perp_data:
            print(f"    💸 资金费率: {perp_data['funding_rate']*100:.4f}%")
    else:
        print("    ❌ 期货数据获取失败")
    
    # 测试费率周期
    print("  计算费率周期...")
    cycle = calculate_funding_cycle(symbol)
    print(f"    ⏰ 费率周期: {cycle}小时")
    
    return spot_data, perp_data, cycle

if __name__ == "__main__":
    # 先测试连通性
    connectivity = test_api_connectivity()
    
    if not any(connectivity.values()):
        print("❌ 所有API都无法访问！")
        exit(1)
    
    # 测试几个代币
    test_symbols = ["BTC", "ETH", "1000PEPE"]
    
    for symbol in test_symbols:
        spot, perp, cycle = test_single_token(symbol)
        time.sleep(2)  # 避免限速