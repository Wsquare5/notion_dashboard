#!/usr/bin/env python3
"""
多数据源加密货币数据获取器
支持CoinGecko和CoinMarketCap作为备用数据源，自动处理限速和故障切换
"""

import requests
import json
import time
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

class DataSource(Enum):
    COINGECKO = "coingecko"
    COINMARKETCAP = "coinmarketcap"

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

class MultiSourceCryptoFetcher:
    """多数据源加密货币数据获取器"""
    
    def __init__(self):
        # CoinMarketCap API密钥（可选，有密钥会有更高的限速）
        self.cmc_api_key = os.getenv('CMC_API_KEY')  # 从环境变量获取
        
        # 请求限制配置
        self.coingecko_delay = 2.1  # CoinGecko免费版限制
        self.cmc_delay = 1.0 if self.cmc_api_key else 3.0  # 有密钥的话更快
        
        # 上次请求时间记录
        self.last_request_time = {
            DataSource.COINGECKO: 0,
            DataSource.COINMARKETCAP: 0
        }
        
        # 错误计数
        self.error_count = {
            DataSource.COINGECKO: 0,
            DataSource.COINMARKETCAP: 0
        }
        
        # 当前首选数据源
        self.preferred_source = DataSource.COINGECKO
    
    def _wait_for_rate_limit(self, source: DataSource):
        """等待满足限速要求"""
        delay = self.coingecko_delay if source == DataSource.COINGECKO else self.cmc_delay
        elapsed = time.time() - self.last_request_time[source]
        
        if elapsed < delay:
            wait_time = delay - elapsed
            print(f"⏳ {source.value} 限速等待 {wait_time:.1f}秒...")
            time.sleep(wait_time)
    
    def _make_request(self, url: str, headers: Dict = None, timeout: int = 15) -> Optional[Dict]:
        """发起HTTP请求"""
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                print(f"⚠️ 限速 429: {url}")
                return None
            else:
                print(f"⚠️ HTTP {response.status_code}: {url}")
                return None
                
        except Exception as e:
            print(f"❌ 请求错误: {e}")
            return None
    
    def fetch_coingecko_data(self, coingecko_id: str) -> Optional[TokenSupplyData]:
        """从CoinGecko获取数据"""
        self._wait_for_rate_limit(DataSource.COINGECKO)
        self.last_request_time[DataSource.COINGECKO] = time.time()
        
        url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}"
        
        data = self._make_request(url)
        if not data:
            self.error_count[DataSource.COINGECKO] += 1
            return None
        
        try:
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
                data_source="coingecko"
            )
            
        except Exception as e:
            print(f"❌ CoinGecko数据解析错误: {e}")
            self.error_count[DataSource.COINGECKO] += 1
            return None
    
    def fetch_coinmarketcap_data(self, symbol: str) -> Optional[TokenSupplyData]:
        """从CoinMarketCap获取数据"""
        self._wait_for_rate_limit(DataSource.COINMARKETCAP)
        self.last_request_time[DataSource.COINMARKETCAP] = time.time()
        
        # CoinMarketCap API端点
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        
        headers = {
            'Accept': 'application/json',
        }
        
        # 如果有API密钥，添加到请求头
        if self.cmc_api_key:
            headers['X-CMC_PRO_API_KEY'] = self.cmc_api_key
        
        params = {
            'symbol': symbol.upper(),
            'convert': 'USD'
        }
        
        # 构造完整URL
        param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{url}?{param_str}"
        
        data = self._make_request(full_url, headers=headers)
        if not data:
            self.error_count[DataSource.COINMARKETCAP] += 1
            return None
        
        try:
            # CoinMarketCap返回格式
            if 'data' not in data or symbol.upper() not in data['data']:
                print(f"❌ CoinMarketCap未找到代币: {symbol}")
                return None
            
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
                ath=None,  # CoinMarketCap基础API不包含ATH数据
                atl=None,
                logo_url=None,  # 需要单独的API调用获取Logo
                data_source="coinmarketcap"
            )
            
        except Exception as e:
            print(f"❌ CoinMarketCap数据解析错误: {e}")
            self.error_count[DataSource.COINMARKETCAP] += 1
            return None
    
    def fetch_with_fallback(self, symbol: str, coingecko_id: str = None) -> Optional[TokenSupplyData]:
        """带故障转移的数据获取"""
        
        # 决定首选数据源
        primary_source = self.preferred_source
        
        # 如果一个数据源错误太多，切换到另一个
        if self.error_count[DataSource.COINGECKO] > 5:
            primary_source = DataSource.COINMARKETCAP
            print("🔄 切换到CoinMarketCap作为主数据源")
        elif self.error_count[DataSource.COINMARKETCAP] > 5:
            primary_source = DataSource.COINGECKO
            print("🔄 切换到CoinGecko作为主数据源")
        
        # 尝试主数据源
        if primary_source == DataSource.COINGECKO and coingecko_id:
            print(f"🔄 尝试CoinGecko: {symbol} -> {coingecko_id}")
            data = self.fetch_coingecko_data(coingecko_id)
            if data:
                return data
            print(f"⚠️ CoinGecko失败，尝试备用数据源...")
        
        # 尝试备用数据源
        if primary_source == DataSource.COINGECKO:
            print(f"🔄 尝试CoinMarketCap: {symbol}")
            data = self.fetch_coinmarketcap_data(symbol)
            if data:
                return data
        else:
            print(f"🔄 尝试CoinMarketCap: {symbol}")
            data = self.fetch_coinmarketcap_data(symbol)
            if data:
                return data
            
            if coingecko_id:
                print(f"⚠️ CoinMarketCap失败，尝试CoinGecko: {coingecko_id}")
                data = self.fetch_coingecko_data(coingecko_id)
                if data:
                    return data
        
        print(f"❌ 所有数据源都失败: {symbol}")
        return None
    
    def get_status(self) -> Dict:
        """获取数据源状态"""
        return {
            'preferred_source': self.preferred_source.value,
            'error_count': {k.value: v for k, v in self.error_count.items()},
            'cmc_api_key_configured': bool(self.cmc_api_key),
            'last_request_time': {k.value: v for k, v in self.last_request_time.items()}
        }

def test_multi_source_fetcher():
    """测试多数据源获取器"""
    fetcher = MultiSourceCryptoFetcher()
    
    # 测试用例
    test_cases = [
        {'symbol': 'BTC', 'coingecko_id': 'bitcoin'},
        {'symbol': 'ETH', 'coingecko_id': 'ethereum'},
        {'symbol': 'SOL', 'coingecko_id': 'solana'},
        {'symbol': 'PEPE', 'coingecko_id': 'pepe'},
        {'symbol': 'UNKNOWN', 'coingecko_id': 'non-existent-coin'}  # 测试错误处理
    ]
    
    print("🧪 测试多数据源获取器...")
    
    for i, test_case in enumerate(test_cases, 1):
        symbol = test_case['symbol']
        coingecko_id = test_case['coingecko_id']
        
        print(f"\n--- 测试 {i}: {symbol} ---")
        
        start_time = time.time()
        data = fetcher.fetch_with_fallback(symbol, coingecko_id)
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
    # 运行测试
    test_multi_source_fetcher()