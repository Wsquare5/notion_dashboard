#!/usr/bin/env python3
"""
使用CoinMarketCap免费API的数据获取器
免费API不需要密钥，但有限制
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class TokenSupplyData:
    """代币供应量数据"""
    total_supply: Optional[float] = None
    circulating_supply: Optional[float] = None
    max_supply: Optional[float] = None
    market_cap: Optional[float] = None
    price_usd: Optional[float] = None
    volume_24h: Optional[float] = None
    price_change_24h: Optional[float] = None
    data_source: Optional[str] = None

class SimpleCryptoFetcher:
    """简化的加密货币数据获取器"""
    
    def __init__(self):
        self.last_cg_request = 0
        self.last_cmc_request = 0
        self.cg_delay = 3.0  # CoinGecko延迟
        self.cmc_delay = 2.0  # 更保守的延迟
    
    def fetch_coingecko_simple(self, coingecko_id: str) -> Optional[TokenSupplyData]:
        """使用CoinGecko简单API"""
        # 等待限速
        elapsed = time.time() - self.last_cg_request
        if elapsed < self.cg_delay:
            wait_time = self.cg_delay - elapsed
            print(f"⏳ CoinGecko等待 {wait_time:.1f}秒...")
            time.sleep(wait_time)
        
        self.last_cg_request = time.time()
        
        # 使用简单的价格API，限制更宽松
        url = f"https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': coingecko_id,
            'vs_currencies': 'usd',
            'include_market_cap': 'true',
            'include_24hr_vol': 'true',
            'include_24hr_change': 'true'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if coingecko_id in data:
                    coin_data = data[coingecko_id]
                    return TokenSupplyData(
                        price_usd=coin_data.get('usd'),
                        market_cap=coin_data.get('usd_market_cap'),
                        volume_24h=coin_data.get('usd_24h_vol'),
                        price_change_24h=coin_data.get('usd_24h_change'),
                        data_source="coingecko_simple"
                    )
                else:
                    print(f"❌ CoinGecko未找到: {coingecko_id}")
                    return None
            elif response.status_code == 429:
                print(f"⚠️ CoinGecko限速")
                return None
            else:
                print(f"⚠️ CoinGecko错误: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ CoinGecko请求错误: {e}")
            return None
    
    def fetch_coinmarketcap_free(self, symbol: str) -> Optional[TokenSupplyData]:
        """使用CoinMarketCap免费网页API（非官方）"""
        # 等待限速
        elapsed = time.time() - self.last_cmc_request
        if elapsed < self.cmc_delay:
            wait_time = self.cmc_delay - elapsed
            print(f"⏳ CoinMarketCap等待 {wait_time:.1f}秒...")
            time.sleep(wait_time)
        
        self.last_cmc_request = time.time()
        
        # 使用CoinMarketCap的Web API (不需要密钥，但不保证稳定)
        url = f"https://web-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        params = {
            'symbol': symbol.upper(),
            'convert_id': '2781'  # USD的ID
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and symbol.upper() in data['data']:
                    coin_data = data['data'][symbol.upper()]
                    quote_data = coin_data.get('quote', {}).get('2781', {})  # USD quotes
                    
                    return TokenSupplyData(
                        total_supply=coin_data.get('total_supply'),
                        circulating_supply=coin_data.get('circulating_supply'),
                        max_supply=coin_data.get('max_supply'),
                        market_cap=quote_data.get('market_cap'),
                        price_usd=quote_data.get('price'),
                        volume_24h=quote_data.get('volume_24h'),
                        price_change_24h=quote_data.get('percent_change_24h'),
                        data_source="coinmarketcap_web"
                    )
                else:
                    print(f"❌ CoinMarketCap未找到: {symbol}")
                    return None
            else:
                print(f"⚠️ CoinMarketCap错误: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ CoinMarketCap请求错误: {e}")
            return None
    
    def fetch_alternative_api(self, symbol: str) -> Optional[TokenSupplyData]:
        """使用第三方免费API作为备用"""
        elapsed = time.time() - self.last_cmc_request
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        
        # 使用CoinAPI.io免费tier (需要注册但有免费额度)
        # 或者使用其他免费API
        url = f"https://api.coinlore.net/api/ticker/"
        
        try:
            # 先搜索代币ID
            search_url = f"https://api.coinlore.net/api/search/?q={symbol}"
            response = requests.get(search_url, timeout=10)
            
            if response.status_code == 200:
                search_data = response.json()
                if search_data and len(search_data) > 0:
                    coin_id = search_data[0]['id']
                    
                    # 获取详细数据
                    detail_response = requests.get(f"{url}?id={coin_id}", timeout=10)
                    if detail_response.status_code == 200:
                        coin_data = detail_response.json()[0]
                        
                        return TokenSupplyData(
                            total_supply=float(coin_data.get('tsupply', 0)) if coin_data.get('tsupply') else None,
                            circulating_supply=float(coin_data.get('csupply', 0)) if coin_data.get('csupply') else None,
                            max_supply=float(coin_data.get('msupply', 0)) if coin_data.get('msupply') else None,
                            market_cap=float(coin_data.get('market_cap_usd', 0)) if coin_data.get('market_cap_usd') else None,
                            price_usd=float(coin_data.get('price_usd', 0)) if coin_data.get('price_usd') else None,
                            volume_24h=float(coin_data.get('volume24', 0)) if coin_data.get('volume24') else None,
                            price_change_24h=float(coin_data.get('percent_change_24h', 0)) if coin_data.get('percent_change_24h') else None,
                            data_source="coinlore"
                        )
            
            return None
            
        except Exception as e:
            print(f"❌ 备用API错误: {e}")
            return None
    
    def fetch_with_fallback(self, symbol: str, coingecko_id: str = None) -> Optional[TokenSupplyData]:
        """多数据源获取，带故障转移"""
        
        # 1. 优先尝试CoinGecko简单API（如果有ID）
        if coingecko_id:
            print(f"🔄 尝试CoinGecko简单API: {coingecko_id}")
            data = self.fetch_coingecko_simple(coingecko_id)
            if data:
                print(f"✅ CoinGecko成功")
                return data
        
        # 2. 尝试备用API
        print(f"🔄 尝试备用API: {symbol}")
        data = self.fetch_alternative_api(symbol)
        if data:
            print(f"✅ 备用API成功")
            return data
        
        # 3. 最后尝试CoinMarketCap（如果前面都失败）
        print(f"🔄 尝试CoinMarketCap: {symbol}")
        data = self.fetch_coinmarketcap_free(symbol)
        if data:
            print(f"✅ CoinMarketCap成功")
            return data
        
        print(f"❌ 所有数据源都失败: {symbol}")
        return None

def test_simple_fetcher():
    """测试简化获取器"""
    fetcher = SimpleCryptoFetcher()
    
    test_cases = [
        {'symbol': 'BTC', 'coingecko_id': 'bitcoin'},
        {'symbol': 'ETH', 'coingecko_id': 'ethereum'},
        {'symbol': 'PEPE', 'coingecko_id': 'pepe'},
    ]
    
    print("🧪 测试简化多数据源获取器...")
    
    for i, test_case in enumerate(test_cases, 1):
        symbol = test_case['symbol']
        coingecko_id = test_case.get('coingecko_id')
        
        print(f"\n--- 测试 {i}: {symbol} ---")
        
        start_time = time.time()
        data = fetcher.fetch_with_fallback(symbol, coingecko_id)
        end_time = time.time()
        
        if data:
            print(f"✅ 成功获取数据:")
            print(f"  数据源: {data.data_source}")
            print(f"  价格: ${data.price_usd:.6f}" if data.price_usd else "  价格: N/A")
            print(f"  市值: ${data.market_cap:,.0f}" if data.market_cap else "  市值: N/A")
            print(f"  24h变化: {data.price_change_24h:.2f}%" if data.price_change_24h else "  24h变化: N/A")
        else:
            print(f"❌ 获取失败")
        
        print(f"⏱️ 耗时: {(end_time - start_time):.2f}秒")

if __name__ == "__main__":
    test_simple_fetcher()