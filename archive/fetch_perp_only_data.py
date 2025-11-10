#!/usr/bin/env python3
"""
获取只有期货合约（没有现货）的代币数据
"""

import requests
import json
import time
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path

@dataclass
class PerpOnlyTokenData:
    """只有期货的代币数据结构"""
    symbol: str
    perp_price: Optional[float] = None
    mark_price: Optional[float] = None  # 标记价格，用于基差计算
    perp_24h_change: Optional[float] = None
    perp_24h_volume: Optional[float] = None
    perp_high_24h: Optional[float] = None
    perp_low_24h: Optional[float] = None
    open_interest: Optional[float] = None
    open_interest_usd: Optional[float] = None
    funding_rate: Optional[float] = None
    funding_cycle: Optional[int] = None  # 资金费率周期（小时）
    next_funding_time: Optional[int] = None
    index_price: Optional[float] = None
    basis: Optional[float] = None
    basis_percentage: Optional[float] = None
    index_composition: Optional[str] = None
    last_updated: Optional[str] = None

def fetch_perp_only_tokens() -> List[str]:
    """获取只有期货合约的代币列表"""
    print("🔍 获取只有期货的代币列表...")
    
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
    
    # Find tokens that have only perpetual markets
    perp_only = perp_symbols - spot_symbols
    perp_only_list = sorted(list(perp_only))
    
    print(f"📊 找到 {len(perp_only_list)} 个只有期货的代币")
    return perp_only_list

def fetch_perp_data(symbols: List[str]) -> Dict[str, Dict]:
    """获取期货数据"""
    print(f"📈 获取 {len(symbols)} 个代币的期货数据...")
    
    # 1. Get 24hr ticker data
    ticker_url = 'https://fapi.binance.com/fapi/v1/ticker/24hr'
    ticker_response = requests.get(ticker_url)
    ticker_data = ticker_response.json()
    
    # 2. Get funding rate data
    funding_url = 'https://fapi.binance.com/fapi/v1/premiumIndex'
    funding_response = requests.get(funding_url)
    funding_data = funding_response.json()
    
    # Create lookup dictionaries
    ticker_dict = {item['symbol']: item for item in ticker_data}
    funding_dict = {item['symbol']: item for item in funding_data}
    
    # Get open interest for each symbol individually (since batch endpoint might not work)
    oi_dict = {}
    
    perp_data = {}
    
    for symbol in symbols:
        symbol_usdt = f"{symbol}USDT"
        
        # Get ticker data
        ticker_info = ticker_dict.get(symbol_usdt, {})
        
        # Get funding data
        funding_info = funding_dict.get(symbol_usdt, {})
        
        # Get OI data individually with retry
        oi_info = {}
        for attempt in range(3):
            try:
                oi_url = f'https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol_usdt}'
                oi_response = requests.get(oi_url, timeout=10)
                if oi_response.status_code == 200:
                    oi_info = oi_response.json()
                    break
                else:
                    print(f"⚠️  {symbol} OI API返回 {oi_response.status_code}")
                    time.sleep(1)
            except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError) as e:
                if attempt < 2:
                    print(f"⚠️  {symbol} OI连接失败，重试中... ({attempt + 1}/3)")
                    time.sleep(2)
                else:
                    print(f"⚠️  获取 {symbol} OI 失败: {e}")
            except Exception as e:
                print(f"⚠️  获取 {symbol} OI 失败: {e}")
                break
        
        time.sleep(0.2)  # Rate limiting
        
        perp_data[symbol] = {
            'price': safe_float(ticker_info.get('lastPrice')),
            'mark_price': safe_float(funding_info.get('markPrice')),  # 添加标记价格用于基差计算
            'change_24h': safe_float(ticker_info.get('priceChangePercent')),
            'volume_24h': safe_float(ticker_info.get('quoteVolume')),  # 修复：使用quoteVolume (USDT) 而不是 volume (基础资产)
            'high_24h': safe_float(ticker_info.get('highPrice')),
            'low_24h': safe_float(ticker_info.get('lowPrice')),
            'open_interest': safe_float(oi_info.get('openInterest')),
            'funding_rate': safe_float(funding_info.get('lastFundingRate')),
            'next_funding_time': safe_int(funding_info.get('nextFundingTime')),
            'index_price': safe_float(funding_info.get('indexPrice')),
        }
    
    time.sleep(0.5)  # Rate limiting
    return perp_data

def fetch_index_composition_with_retry(symbol_usdt: str, max_retries: int = 3) -> Dict:
    """带重试机制的指数组成数据获取"""
    for attempt in range(max_retries):
        try:
            url = f'https://fapi.binance.com/fapi/v1/constituents?symbol={symbol_usdt}'
            response = requests.get(url, timeout=15)  # 增加超时时间
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # 如果是限速，等待更长时间
                wait_time = (attempt + 1) * 5
                print(f"⚠️  {symbol_usdt} 限速，等待 {wait_time} 秒...")
                time.sleep(wait_time)
                continue
            else:
                print(f"⚠️  {symbol_usdt} API返回错误: {response.status_code}")
                return {}
                
        except requests.exceptions.ProxyError as e:
            print(f"⚠️  {symbol_usdt} 代理错误 (尝试 {attempt + 1}/{max_retries}): {e}")
            time.sleep((attempt + 1) * 2)  # 逐渐增加等待时间
        except requests.exceptions.ConnectionError as e:
            print(f"⚠️  {symbol_usdt} 连接错误 (尝试 {attempt + 1}/{max_retries}): {e}")
            time.sleep((attempt + 1) * 2)
        except Exception as e:
            print(f"⚠️  {symbol_usdt} 其他错误 (尝试 {attempt + 1}/{max_retries}): {e}")
            time.sleep(1)
    
    print(f"❌ {symbol_usdt} 所有重试都失败了")
    return {}

def fetch_index_composition(symbols: List[str]) -> Dict[str, str]:
    """获取指数组成数据（带重试机制）"""
    print(f"📊 获取指数组成数据...")
    
    composition_data = {}
    
    for i, symbol in enumerate(symbols, 1):
        symbol_usdt = f"{symbol}USDT"
        print(f"  ({i}/{len(symbols)}) 获取 {symbol} 指数组成...")
        
        try:
            data = fetch_index_composition_with_retry(symbol_usdt)
            
            if data and 'constituents' in data:
                constituents = data['constituents']
                if constituents:
                    # Format composition as "Exchange1: 45.2%, Exchange2: 32.1%, ..."
                    composition_parts = []
                    for constituent in constituents:
                        exchange = constituent.get('exchange', 'Unknown')
                        weight = constituent.get('weight', 0)
                        # Convert to percentage format (e.g., 0.45 -> 45%)
                        weight_pct = float(weight) * 100 if weight else 0
                        composition_parts.append(f"{exchange}: {weight_pct:.1f}%")
                    
                    composition_data[symbol] = ", ".join(composition_parts)
                    print(f"    ✅ 成功")
                else:
                    composition_data[symbol] = "No data"
                    print(f"    ⚠️  无组成数据")
            elif data:
                composition_data[symbol] = "No constituents"
                print(f"    ⚠️  无constituents字段")
            else:
                composition_data[symbol] = "API error"
                print(f"    ❌ API错误")
                
            # 在每个请求之间增加延迟
            time.sleep(0.5)
            
            # 每10个请求后休息更长时间
            if i % 10 == 0:
                print(f"    ⏳ 已处理 {i} 个，休息 3 秒...")
                time.sleep(3)
            
        except Exception as e:
            print(f"❌ 获取 {symbol} 指数组成失败: {e}")
            composition_data[symbol] = "Error"
    
    return composition_data

def calculate_funding_cycle(symbol: str) -> int:
    """计算单个代币的费率周期"""
    try:
        symbol_usdt = f"{symbol}USDT"
        url = f'https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol_usdt}&limit=3'
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            if len(data) >= 2:
                # 计算时间间隔
                timestamp1 = int(data[0]['fundingTime'])
                timestamp2 = int(data[1]['fundingTime'])
                
                interval_ms = abs(timestamp1 - timestamp2)
                interval_hours = interval_ms / (1000 * 60 * 60)
                
                # 推断周期
                if 7.5 <= interval_hours <= 8.5:
                    return 8
                elif 3.5 <= interval_hours <= 4.5:
                    return 4  
                elif 5.5 <= interval_hours <= 6.5:
                    return 6
                else:
                    return 8  # 默认8小时
            else:
                return 8  # 默认8小时
        else:
            return 8  # 默认8小时
            
    except Exception as e:
        print(f"⚠️  计算 {symbol} 费率周期失败: {e}")
        return 8  # 默认8小时

def fetch_funding_cycles(symbols: List[str]) -> Dict[str, int]:
    """获取资金费率周期信息 - 为每个代币单独计算"""
    print(f"⏰ 计算资金费率周期信息...")
    
    # 先检查几个主要代币来了解通用模式
    sample_symbols = symbols[:5] if len(symbols) > 5 else symbols
    sample_cycles = {}
    
    for symbol in sample_symbols:
        cycle = calculate_funding_cycle(symbol)
        sample_cycles[cycle] = sample_cycles.get(cycle, 0) + 1
        time.sleep(0.3)  # Rate limiting
    
    # 找出最常见的周期
    if sample_cycles:
        common_cycle = max(sample_cycles.keys(), key=lambda k: sample_cycles[k])
        print(f"📊 检测到常见费率周期: {common_cycle}小时")
        
        # 为所有代币设置通用周期（大多数都是8小时）
        # 但对于特殊情况，我们可以单独计算
        result = {}
        for symbol in symbols:
            if symbol in ['GOAT', 'MOODENG']:  # 一些新代币可能是4小时
                result[symbol] = calculate_funding_cycle(symbol)
                time.sleep(0.2)
            else:
                result[symbol] = common_cycle  # 使用通用周期
        
        return result
    else:
        # 如果检测失败，默认都是8小时
        print("⚠️  费率周期检测失败，使用默认8小时")
        return {symbol: 8 for symbol in symbols}

def safe_float(value) -> Optional[float]:
    """安全转换为float"""
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def safe_int(value) -> Optional[int]:
    """安全转换为int"""
    if value is None or value == '':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def calculate_derived_metrics(token_data: Dict[str, Any]) -> Dict[str, Any]:
    """计算衍生指标"""
    # Calculate basis (mark price vs index price) - 使用标记价格计算基差
    index_price = token_data.get('index_price')
    mark_price = token_data.get('mark_price')
    perp_price = token_data.get('price')  # 保留最新成交价用于其他计算
    
    if index_price and mark_price and index_price > 0:
        basis = mark_price - index_price
        basis_percentage = (basis / index_price) * 100
        
        token_data['basis'] = basis
        token_data['basis_percentage'] = basis_percentage
    
    # Calculate open interest in USD
    open_interest = token_data.get('open_interest')
    if open_interest and perp_price:
        token_data['open_interest_usd'] = open_interest * perp_price
    
    return token_data

def fetch_perp_only_data(symbols: List[str] = None) -> List[PerpOnlyTokenData]:
    """获取只有期货的代币完整数据"""
    if symbols is None:
        symbols = fetch_perp_only_tokens()
    
    print(f"🚀 开始获取 {len(symbols)} 个只有期货的代币数据...")
    
    # Get perp data
    perp_data = fetch_perp_data(symbols)
    
    # Get index composition
    composition_data = fetch_index_composition(symbols)
    
    # Get funding cycles for all symbols
    print("📊 正在检测资金费率周期...")
    funding_cycles = fetch_funding_cycles(symbols)
    
    # Combine data
    token_list = []
    current_time = time.strftime('%Y-%m-%d %H:%M:%S')
    
    for symbol in symbols:
        perp_info = perp_data.get(symbol, {})
        composition = composition_data.get(symbol, "No data")
        
        # Calculate derived metrics
        perp_info = calculate_derived_metrics(perp_info)
        
        token_data = PerpOnlyTokenData(
            symbol=symbol,
            perp_price=perp_info.get('price'),
            perp_24h_change=perp_info.get('change_24h'),
            perp_24h_volume=perp_info.get('volume_24h'),
            perp_high_24h=perp_info.get('high_24h'),
            perp_low_24h=perp_info.get('low_24h'),
            open_interest=perp_info.get('open_interest'),
            open_interest_usd=perp_info.get('open_interest_usd'),
            funding_rate=perp_info.get('funding_rate'),
            next_funding_time=perp_info.get('next_funding_time'),
            funding_cycle=funding_cycles.get(symbol, 8),  # 默认8小时
            index_price=perp_info.get('index_price'),
            basis=perp_info.get('basis'),
            basis_percentage=perp_info.get('basis_percentage'),
            index_composition=composition,
            last_updated=current_time
        )
        
        token_list.append(token_data)
    
    print(f"✅ 成功获取 {len(token_list)} 个代币的期货数据")
    return token_list

def save_to_json(data: List[PerpOnlyTokenData], filename: str = "perp_only_data.json"):
    """保存数据到JSON文件"""
    output_path = Path(__file__).parent.parent / "data" / filename
    output_path.parent.mkdir(exist_ok=True)
    
    # Convert to dictionaries
    data_dicts = [asdict(token) for token in data]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data_dicts, f, indent=2, ensure_ascii=False)
    
    print(f"💾 数据已保存到: {output_path}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='获取只有期货的代币数据')
    parser.add_argument('--symbols', nargs='*', help='指定代币符号 (如 1000PEPE GOAT)')
    parser.add_argument('--limit', type=int, help='限制代币数量')
    parser.add_argument('--output', default='perp_only_data.json', help='输出文件名')
    
    args = parser.parse_args()
    
    try:
        if args.symbols:
            symbols = args.symbols
            print(f"📋 获取指定代币: {symbols}")
        else:
            symbols = fetch_perp_only_tokens()
            if args.limit:
                symbols = symbols[:args.limit]
                print(f"📏 限制为前 {args.limit} 个代币")
        
        # Fetch data
        token_data = fetch_perp_only_data(symbols)
        
        # Save to file
        save_to_json(token_data, args.output)
        
        # Print summary
        print(f"\n📊 数据摘要:")
        print(f"  代币数量: {len(token_data)}")
        print(f"  有价格数据: {sum(1 for t in token_data if t.perp_price)}")
        print(f"  有OI数据: {sum(1 for t in token_data if t.open_interest)}")
        print(f"  有资金费率: {sum(1 for t in token_data if t.funding_rate)}")
        
        # Show first few examples
        print(f"\n💡 前5个代币示例:")
        for i, token in enumerate(token_data[:5], 1):
            price = f"${token.perp_price:.4f}" if token.perp_price else "N/A"
            change = f"{token.perp_24h_change:+.2f}%" if token.perp_24h_change else "N/A"
            oi_usd = f"${token.open_interest_usd:,.0f}" if token.open_interest_usd else "N/A"
            print(f"  {i}. {token.symbol}: {price} ({change}), OI: {oi_usd}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()