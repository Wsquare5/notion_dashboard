#!/usr/bin/env python3
"""
改进的多数据源加密货币数据获取器
使用CoinMarketCap API密钥提供更稳定的数据获取
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

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
    ath: Optional[float] = None
    atl: Optional[float] = None
    logo_url: Optional[str] = None
    data_source: Optional[str] = None

class EnhancedCryptoFetcher:
    """增强的加密货币数据获取器"""
    
    def __init__(self, config_file: str = "api_config.json"):
        """初始化获取器"""
        self.config = self.load_config(config_file)
        self.last_request_time = {
            'coinmarketcap': 0,
            'coingecko': 0
        }
        self.error_count = {
            'coinmarketcap': 0,
            'coingecko': 0
        }
        
        # 获取API配置
        self.cmc_api_key = self.config.get('coinmarketcap', {}).get('api_key')
        self.cmc_base_url = self.config.get('coinmarketcap', {}).get('base_url')
        self.cg_base_url = self.config.get('coingecko', {}).get('base_url')
        
        # 限速配置
        self.cmc_delay = 60 / self.config.get('coinmarketcap', {}).get('rate_limit', 30)  # 30 calls/min
        self.cg_delay = 60 / self.config.get('coingecko', {}).get('rate_limit', 30)  # 30 calls/min
        
        self.preferred_source = self.config.get('settings', {}).get('preferred_source', 'coinmarketcap')
        
        print(f"🔧 初始化多数据源获取器:")
        print(f"  CoinMarketCap API: {'✅ 已配置' if self.cmc_api_key else '❌ 未配置'}")
        print(f"  首选数据源: {self.preferred_source}")
        print(f"  限速: CMC={self.cmc_delay:.1f}s, CG={self.cg_delay:.1f}s")
    
    def load_config(self, config_file: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ 加载配置文件失败: {e}")
            return {}
    
    def _wait_for_rate_limit(self, source: str):
        """等待满足限速要求"""
        delay = self.cmc_delay if source == 'coinmarketcap' else self.cg_delay
        elapsed = time.time() - self.last_request_time[source]
        
        if elapsed < delay:
            wait_time = delay - elapsed
            print(f"⏳ {source} 限速等待 {wait_time:.1f}秒...")
            time.sleep(wait_time)
    
    def fetch_coinmarketcap_data(self, symbol: str) -> Optional[TokenSupplyData]:
        """从CoinMarketCap获取数据"""
        if not self.cmc_api_key:
            print("❌ CoinMarketCap API密钥未配置")
            return None
        
        self._wait_for_rate_limit('coinmarketcap')
        self.last_request_time['coinmarketcap'] = time.time()
        
        url = f"{self.cmc_base_url}/cryptocurrency/quotes/latest"
        
        headers = {
            'Accept': 'application/json',
            'X-CMC_PRO_API_KEY': self.cmc_api_key
        }
        
        params = {
            'symbol': symbol.upper(),
            'convert': 'USD'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and symbol.upper() in data['data']:
                    coin_data = data['data'][symbol.upper()]
                    quote_data = coin_data.get('quote', {}).get('USD', {})
                    
                    return TokenSupplyData(
                        total_supply=coin_data.get('total_supply'),
                        circulating_supply=coin_data.get('circulating_supply'),
                        max_supply=coin_data.get('max_supply'),
                        market_cap=quote_data.get('market_cap'),
                        price_usd=quote_data.get('price'),
                        volume_24h=quote_data.get('volume_24h'),
                        price_change_24h=quote_data.get('percent_change_24h'),
                        data_source="coinmarketcap"
                    )
                else:
                    print(f"❌ CoinMarketCap未找到代币: {symbol}")
                    return None
            else:
                print(f"⚠️ CoinMarketCap API错误 {response.status_code}: {response.text}")
                self.error_count['coinmarketcap'] += 1
                return None
                
        except Exception as e:
            print(f"❌ CoinMarketCap请求错误: {e}")
            self.error_count['coinmarketcap'] += 1
            return None
    
    def fetch_coingecko_data(self, coingecko_id: str, use_simple_api: bool = True) -> Optional[TokenSupplyData]:
        """从CoinGecko获取数据"""
        self._wait_for_rate_limit('coingecko')
        self.last_request_time['coingecko'] = time.time()
        
        if use_simple_api:
            # 使用简单API，限速更宽松
            url = f"{self.cg_base_url}/simple/price"
            params = {
                'ids': coingecko_id,
                'vs_currencies': 'usd',
                'include_market_cap': 'true',
                'include_24hr_vol': 'true',
                'include_24hr_change': 'true'
            }
        else:
            # 使用完整API
            url = f"{self.cg_base_url}/coins/{coingecko_id}"
            params = {}
        
        try:
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if use_simple_api:
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
                    # 完整API响应
                    market_data = data.get('market_data', {})
                    return TokenSupplyData(
                        total_supply=market_data.get('total_supply'),
                        circulating_supply=market_data.get('circulating_supply'),
                        max_supply=market_data.get('max_supply'),
                        market_cap=market_data.get('market_cap', {}).get('usd'),
                        price_usd=market_data.get('current_price', {}).get('usd'),
                        volume_24h=market_data.get('total_volume', {}).get('usd'),
                        price_change_24h=market_data.get('price_change_percentage_24h'),
                        ath=market_data.get('ath', {}).get('usd'),
                        atl=market_data.get('atl', {}).get('usd'),
                        logo_url=data.get('image', {}).get('large'),
                        data_source="coingecko_full"
                    )
                
                return None
            elif response.status_code == 429:
                print(f"⚠️ CoinGecko限速")
                self.error_count['coingecko'] += 1
                return None
            else:
                print(f"⚠️ CoinGecko API错误 {response.status_code}")
                self.error_count['coingecko'] += 1
                return None
                
        except Exception as e:
            print(f"❌ CoinGecko请求错误: {e}")
            self.error_count['coingecko'] += 1
            return None
    
    def fetch_with_smart_fallback(self, symbol: str, coingecko_id: str = None) -> Optional[TokenSupplyData]:
        """智能故障转移数据获取"""
        
        # 根据错误率动态调整首选数据源
        if self.error_count['coinmarketcap'] > 5 and self.error_count['coingecko'] <= 5:
            primary_source = 'coingecko'
        elif self.error_count['coingecko'] > 5 and self.error_count['coinmarketcap'] <= 5:
            primary_source = 'coinmarketcap'
        else:
            primary_source = self.preferred_source
        
        print(f"🔄 主数据源: {primary_source}")
        
        # 尝试主数据源
        if primary_source == 'coinmarketcap':
            data = self.fetch_coinmarketcap_data(symbol)
            if data:
                print(f"✅ CoinMarketCap成功获取 {symbol}")
                return data
            
            # 主数据源失败，尝试备用
            if coingecko_id:
                print(f"🔄 备用: CoinGecko {coingecko_id}")
                data = self.fetch_coingecko_data(coingecko_id, use_simple_api=True)
                if data:
                    print(f"✅ CoinGecko备用成功")
                    return data
        
        else:  # primary_source == 'coingecko'
            if coingecko_id:
                data = self.fetch_coingecko_data(coingecko_id, use_simple_api=True)
                if data:
                    print(f"✅ CoinGecko成功获取 {symbol}")
                    return data
            
            # 主数据源失败，尝试备用
            print(f"🔄 备用: CoinMarketCap {symbol}")
            data = self.fetch_coinmarketcap_data(symbol)
            if data:
                print(f"✅ CoinMarketCap备用成功")
                return data
        
        print(f"❌ 所有数据源都失败: {symbol}")
        return None
    
    def get_status(self) -> Dict:
        """获取获取器状态"""
        return {
            'preferred_source': self.preferred_source,
            'cmc_api_configured': bool(self.cmc_api_key),
            'error_count': self.error_count,
            'last_request_time': self.last_request_time,
            'rate_limits': {
                'coinmarketcap': f"{self.cmc_delay:.1f}s",
                'coingecko': f"{self.cg_delay:.1f}s"
            }
        }

def test_enhanced_fetcher():
    """测试增强获取器"""
    fetcher = EnhancedCryptoFetcher()
    
    # 测试用例，包括一些手动映射的代币
    test_cases = [
        {'symbol': 'BTC', 'coingecko_id': 'bitcoin'},
        {'symbol': 'ETH', 'coingecko_id': 'ethereum'},
        {'symbol': 'PEPE', 'coingecko_id': 'pepe'},
        {'symbol': 'FXS', 'coingecko_id': 'frax-share'},
        {'symbol': 'BTTC', 'coingecko_id': 'bittorrent'},
        {'symbol': 'UNKNOWN_TOKEN', 'coingecko_id': None}  # 测试错误处理
    ]
    
    print("\n🧪 测试增强多数据源获取器...")
    
    for i, test_case in enumerate(test_cases, 1):
        symbol = test_case['symbol']
        coingecko_id = test_case.get('coingecko_id')
        
        print(f"\n--- 测试 {i}: {symbol} ---")
        
        start_time = time.time()
        data = fetcher.fetch_with_smart_fallback(symbol, coingecko_id)
        end_time = time.time()
        
        if data:
            print(f"✅ 成功获取数据:")
            print(f"  数据源: {data.data_source}")
            print(f"  价格: ${data.price_usd:.6f}" if data.price_usd else "  价格: N/A")
            print(f"  市值: ${data.market_cap:,.0f}" if data.market_cap else "  市值: N/A")
            print(f"  流通量: {data.circulating_supply:,.0f}" if data.circulating_supply else "  流通量: N/A")
            print(f"  24h变化: {data.price_change_24h:.2f}%" if data.price_change_24h else "  24h变化: N/A")
        else:
            print(f"❌ 获取失败")
        
        print(f"⏱️ 耗时: {(end_time - start_time):.2f}秒")
    
    # 显示状态
    print(f"\n📊 获取器状态:")
    status = fetcher.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    test_enhanced_fetcher()