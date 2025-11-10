#!/usr/bin/env python3
"""
获取代币官网信息的脚本
支持多个数据源：CoinGecko, CoinMarketCap, 和其他公开API
"""

import requests
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import re

class TokenWebsiteCollector:
    """代币官网信息收集器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        # 缓存机制
        self.website_cache = {}
        self.coingecko_cache = {}
        
        # 手动维护的网站映射（主要币种）
        self.manual_websites = {
            'BTC': 'https://bitcoin.org',
            'ETH': 'https://ethereum.org', 
            'BNB': 'https://www.bnbchain.org',
            'ADA': 'https://cardano.org',
            'SOL': 'https://solana.com',
            'DOT': 'https://polkadot.network',
            'MATIC': 'https://polygon.technology',
            'AVAX': 'https://www.avax.network',
            'UNI': 'https://uniswap.org',
            'LINK': 'https://chain.link',
            'LTC': 'https://litecoin.org',
            'XRP': 'https://xrpl.org',
            'ATOM': 'https://cosmos.network',
            'ICP': 'https://internetcomputer.org',
            'FTM': 'https://fantom.foundation',
            'ALGO': 'https://algorand.com',
            'XLM': 'https://stellar.org',
            'VET': 'https://www.vechain.org',
            'FLOW': 'https://flow.com',
            'THETA': 'https://thetatoken.org',
            'FIL': 'https://filecoin.io',
            'TRX': 'https://tron.network',
            'XTZ': 'https://tezos.com',
            'EOS': 'https://eos.io',
            'AAVE': 'https://aave.com',
            'MKR': 'https://makerdao.com',
            'COMP': 'https://compound.finance',
            'YFI': 'https://yearn.finance',
            'SUSHI': 'https://sushi.com',
            'CRV': 'https://curve.fi',
            '1INCH': 'https://1inch.io',
            'ENS': 'https://ens.domains',
            'LDO': 'https://lido.fi',
            'SHIB': 'https://shibatoken.com',
            'DOGE': 'https://dogecoin.com',
            'PEPE': 'https://www.pepe.vip',
        }

    def get_coingecko_website(self, symbol: str) -> Optional[str]:
        """从CoinGecko获取官网信息"""
        if symbol in self.coingecko_cache:
            return self.coingecko_cache[symbol]
        
        try:
            # 首先尝试通过symbol搜索
            search_url = f'https://api.coingecko.com/api/v3/search?query={symbol}'
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                coins = data.get('coins', [])
                
                # 寻找最匹配的币种
                best_match = None
                for coin in coins:
                    coin_symbol = coin.get('symbol', '').upper()
                    coin_name = coin.get('name', '').upper()
                    
                    # 优先精确匹配symbol
                    if coin_symbol == symbol.upper():
                        best_match = coin
                        break
                    # 如果symbol包含在名称中，也考虑
                    elif symbol.upper() in coin_name:
                        if not best_match:
                            best_match = coin
                
                if best_match:
                    coin_id = best_match.get('id')
                    if coin_id:
                        # 获取详细信息
                        detail_url = f'https://api.coingecko.com/api/v3/coins/{coin_id}'
                        time.sleep(2.1)  # Rate limiting
                        
                        detail_response = self.session.get(detail_url, timeout=10)
                        if detail_response.status_code == 200:
                            detail_data = detail_response.json()
                            links = detail_data.get('links', {})
                            homepage = links.get('homepage', [])
                            
                            if homepage and homepage[0]:
                                website = homepage[0]
                                self.coingecko_cache[symbol] = website
                                return website
            
            time.sleep(2.1)  # Rate limiting
            
        except Exception as e:
            print(f"⚠️  CoinGecko查询失败 {symbol}: {e}")
        
        self.coingecko_cache[symbol] = None
        return None

    def get_coinmarketcap_website(self, symbol: str) -> Optional[str]:
        """从CoinMarketCap获取官网信息（无API密钥的简单方法）"""
        try:
            # 这里可以实现CMC的爬取逻辑，但需要注意反爬虫措施
            # 暂时先跳过，主要依赖CoinGecko
            pass
        except Exception as e:
            print(f"⚠️  CoinMarketCap查询失败 {symbol}: {e}")
        
        return None

    def clean_website_url(self, url: str) -> str:
        """清理和标准化网站URL"""
        if not url:
            return ""
        
        # 移除多余空格
        url = url.strip()
        
        # 确保有协议
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # 移除尾部斜杠
        url = url.rstrip('/')
        
        # 验证URL格式
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if url_pattern.match(url):
            return url
        else:
            return ""

    def get_token_website(self, symbol: str) -> Optional[str]:
        """获取代币官网，尝试多个数据源"""
        
        # 1. 检查手动维护的映射
        if symbol.upper() in self.manual_websites:
            website = self.manual_websites[symbol.upper()]
            return self.clean_website_url(website)
        
        # 2. 检查缓存
        if symbol in self.website_cache:
            return self.website_cache[symbol]
        
        website = None
        
        # 3. 尝试CoinGecko
        website = self.get_coingecko_website(symbol)
        
        # 4. 如果CoinGecko失败，可以尝试其他数据源
        if not website:
            website = self.get_coinmarketcap_website(symbol)
        
        # 5. 清理URL
        if website:
            website = self.clean_website_url(website)
        
        # 缓存结果
        self.website_cache[symbol] = website
        return website

    def batch_get_websites(self, symbols: List[str], max_requests: int = 50) -> Dict[str, Optional[str]]:
        """批量获取多个代币的官网信息"""
        results = {}
        processed = 0
        
        print(f"🌐 开始获取 {len(symbols)} 个代币的官网信息...")
        
        for i, symbol in enumerate(symbols, 1):
            if processed >= max_requests:
                print(f"⚠️  达到最大请求数限制 ({max_requests})，停止处理")
                break
            
            print(f"📍 ({i}/{len(symbols)}) 获取 {symbol} 的官网...")
            
            website = self.get_token_website(symbol)
            results[symbol] = website
            
            if website:
                print(f"  ✅ {symbol}: {website}")
            else:
                print(f"  ❌ {symbol}: 未找到官网")
            
            processed += 1
            
            # 避免过于频繁的请求
            if i % 10 == 0:
                print(f"⏳ 已处理 {i} 个代币，暂停 5 秒...")
                time.sleep(5)
        
        return results

    def save_websites_to_json(self, websites: Dict[str, Optional[str]], filename: str = "token_websites.json"):
        """保存网站信息到JSON文件"""
        output_path = Path(__file__).parent.parent / "data" / filename
        output_path.parent.mkdir(exist_ok=True)
        
        # 过滤掉None值
        clean_websites = {k: v for k, v in websites.items() if v is not None}
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(clean_websites, f, indent=2, ensure_ascii=False)
        
        print(f"💾 网站信息已保存到: {output_path}")
        print(f"📊 找到 {len(clean_websites)} 个有效网站")

def get_all_binance_symbols() -> List[str]:
    """获取所有Binance代币符号"""
    try:
        # 获取现货和期货市场的所有代币
        spot_response = requests.get('https://api.binance.com/api/v3/exchangeInfo')
        perp_response = requests.get('https://fapi.binance.com/fapi/v1/exchangeInfo')
        
        spot_data = spot_response.json()
        perp_data = perp_response.json()
        
        all_symbols = set()
        
        # 现货市场代币
        for symbol_info in spot_data['symbols']:
            if symbol_info['symbol'].endswith('USDT') and symbol_info['status'] == 'TRADING':
                base = symbol_info['baseAsset']
                all_symbols.add(base)
        
        # 期货市场代币
        for symbol_info in perp_data['symbols']:
            if symbol_info['symbol'].endswith('USDT') and symbol_info['status'] == 'TRADING':
                base = symbol_info['baseAsset']
                all_symbols.add(base)
        
        return sorted(list(all_symbols))
        
    except Exception as e:
        print(f"❌ 获取Binance代币列表失败: {e}")
        return []

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='获取代币官网信息')
    parser.add_argument('--symbols', nargs='*', help='指定代币符号 (如 BTC ETH BNB)')
    parser.add_argument('--limit', type=int, default=50, help='最大请求数量 (默认50)')
    parser.add_argument('--output', default='token_websites.json', help='输出文件名')
    parser.add_argument('--test-only', action='store_true', help='只测试前几个代币')
    
    args = parser.parse_args()
    
    try:
        collector = TokenWebsiteCollector()
        
        if args.symbols:
            symbols = args.symbols
            print(f"📋 获取指定代币: {symbols}")
        else:
            symbols = get_all_binance_symbols()
            if args.test_only:
                symbols = symbols[:10]
                print(f"🧪 测试模式，只处理前10个代币")
            print(f"📊 获取到 {len(symbols)} 个Binance代币")
        
        # 获取网站信息
        websites = collector.batch_get_websites(symbols, max_requests=args.limit)
        
        # 保存结果
        collector.save_websites_to_json(websites, args.output)
        
        # 统计信息
        found_count = sum(1 for w in websites.values() if w is not None)
        print(f"\n📊 处理结果:")
        print(f"  总代币数: {len(websites)}")
        print(f"  找到网站: {found_count}")
        print(f"  成功率: {found_count/len(websites)*100:.1f}%")
        
        # 显示一些示例
        found_websites = {k: v for k, v in websites.items() if v is not None}
        if found_websites:
            print(f"\n💡 找到的网站示例:")
            for i, (symbol, website) in enumerate(list(found_websites.items())[:5], 1):
                print(f"  {i}. {symbol}: {website}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()