#!/usr/bin/env python3
"""
优化版本的期货数据获取脚本 - 可以跳过慢速的指数组成API
"""

import requests
import json
import time
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path
import argparse

@dataclass
class PerpOnlyTokenData:
    """只有期货的代币数据结构"""
    symbol: str
    perp_price: Optional[float] = None
    mark_price: Optional[float] = None
    perp_24h_change: Optional[float] = None
    perp_24h_volume: Optional[float] = None
    perp_high_24h: Optional[float] = None
    perp_low_24h: Optional[float] = None
    open_interest: Optional[float] = None
    open_interest_usd: Optional[float] = None
    funding_rate: Optional[float] = None
    funding_cycle: Optional[int] = None
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

def fetch_fast_perp_data(symbols: List[str], skip_composition: bool = False) -> List[PerpOnlyTokenData]:
    """快速获取期货数据，可选跳过指数组成"""
    print(f"🚀 快速获取 {len(symbols)} 个代币的数据...")
    
    # 1. Get 24hr ticker data
    print("📈 获取24小时行情数据...")
    ticker_url = 'https://fapi.binance.com/fapi/v1/ticker/24hr'
    ticker_response = requests.get(ticker_url, timeout=30)
    ticker_data = ticker_response.json()
    
    # 2. Get funding rate data
    print("💰 获取资金费率数据...")
    funding_url = 'https://fapi.binance.com/fapi/v1/premiumIndex'
    funding_response = requests.get(funding_url, timeout=30)
    funding_data = funding_response.json()
    
    # Create lookup dictionaries
    ticker_dict = {item['symbol']: item for item in ticker_data}
    funding_dict = {item['symbol']: item for item in funding_data}
    
    # Process each symbol
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    token_list = []
    
    print(f"🔄 处理 {len(symbols)} 个代币...")
    
    for i, symbol in enumerate(symbols, 1):
        symbol_usdt = f"{symbol}USDT"
        
        # Progress indicator
        if i % 10 == 0 or i == len(symbols):
            print(f"  处理进度: {i}/{len(symbols)} ({i/len(symbols)*100:.1f}%)")
        
        # Get ticker data
        ticker_info = ticker_dict.get(symbol_usdt, {})
        funding_info = funding_dict.get(symbol_usdt, {})
        
        # Get OI data individually (fastest critical data)
        oi_info = {}
        try:
            oi_url = f'https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol_usdt}'
            oi_response = requests.get(oi_url, timeout=5)
            if oi_response.status_code == 200:
                oi_info = oi_response.json()
        except:
            pass  # 忽略OI获取失败
        
        # Calculate derived metrics
        perp_price = safe_float(ticker_info.get('lastPrice'))
        index_price = safe_float(funding_info.get('indexPrice'))
        mark_price = safe_float(funding_info.get('markPrice'))
        open_interest = safe_float(oi_info.get('openInterest'))
        
        # Calculate basis
        basis = None
        basis_percentage = None
        if index_price and mark_price and index_price > 0:
            basis = mark_price - index_price
            basis_percentage = (basis / index_price) * 100
        
        # Calculate OI in USD
        open_interest_usd = None
        if open_interest and perp_price:
            open_interest_usd = open_interest * perp_price
        
        # Get composition (optional, slow)
        composition = "Skipped" if skip_composition else "No data"
        if not skip_composition:
            try:
                comp_url = f'https://fapi.binance.com/fapi/v1/constituents?symbol={symbol_usdt}'
                comp_response = requests.get(comp_url, timeout=8)
                if comp_response.status_code == 200:
                    comp_data = comp_response.json()
                    constituents = comp_data.get('constituents', [])
                    if constituents:
                        composition_parts = []
                        for constituent in constituents:
                            exchange = constituent.get('exchange', 'Unknown')
                            weight = constituent.get('weight', 0)
                            weight_pct = float(weight) * 100 if weight else 0
                            composition_parts.append(f"{exchange}: {weight_pct:.1f}%")
                        composition = ", ".join(composition_parts)
            except:
                composition = "Failed"
        
        token_data = PerpOnlyTokenData(
            symbol=symbol,
            perp_price=perp_price,
            mark_price=mark_price,
            perp_24h_change=safe_float(ticker_info.get('priceChangePercent')),
            perp_24h_volume=safe_float(ticker_info.get('quoteVolume')),
            perp_high_24h=safe_float(ticker_info.get('highPrice')),
            perp_low_24h=safe_float(ticker_info.get('lowPrice')),
            open_interest=open_interest,
            open_interest_usd=open_interest_usd,
            funding_rate=safe_float(funding_info.get('lastFundingRate')),
            funding_cycle=4,  # 默认4小时
            next_funding_time=safe_int(funding_info.get('nextFundingTime')),
            index_price=index_price,
            basis=basis,
            basis_percentage=basis_percentage,
            index_composition=composition,
            last_updated=current_time
        )
        
        token_list.append(token_data)
        
        # Rate limiting
        if i % 20 == 0:
            time.sleep(1)
        else:
            time.sleep(0.05)
    
    print(f"✅ 成功获取 {len(token_list)} 个代币的数据")
    return token_list

def save_to_json(data: List[PerpOnlyTokenData], filename: str = "fast_perp_data.json"):
    """保存数据到JSON文件"""
    output_path = Path(__file__).parent / "data" / filename
    output_path.parent.mkdir(exist_ok=True)
    
    # Convert to dictionaries
    data_dicts = [asdict(token) for token in data]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data_dicts, f, indent=2, ensure_ascii=False)
    
    print(f"💾 数据已保存到: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='快速获取期货数据')
    parser.add_argument('--symbols', nargs='*', help='指定代币符号')
    parser.add_argument('--limit', type=int, help='限制代币数量')
    parser.add_argument('--output', default='fast_perp_data.json', help='输出文件名')
    parser.add_argument('--skip-composition', action='store_true', help='跳过指数组成数据（更快）')
    parser.add_argument('--full', action='store_true', help='获取全部代币')
    
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
            elif not args.full:
                # 默认只处理前30个，除非明确要求全部
                symbols = symbols[:30]
                print(f"📏 默认处理前30个代币（使用 --full 获取全部）")
        
        # 估算时间
        estimated_time = len(symbols) * (2 if args.skip_composition else 5) / 60
        print(f"⏱️  预计耗时: {estimated_time:.1f} 分钟")
        
        start_time = time.time()
        
        # Fetch data
        token_data = fetch_fast_perp_data(symbols, skip_composition=args.skip_composition)
        
        actual_time = (time.time() - start_time) / 60
        print(f"⏱️  实际耗时: {actual_time:.1f} 分钟")
        
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