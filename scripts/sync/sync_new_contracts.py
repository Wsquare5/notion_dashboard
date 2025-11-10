#!/usr/bin/env python3
"""
自动检测Binance新合约并同步到Notion
- 检测新上线的永续合约
- 从CoinMarketCap获取基本信息
- 创建Notion页面
- 更新本地数据文件
"""

import json
import requests
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

class NewContractSync:
    def __init__(self, config_path: str = "config.json"):
        """初始化"""
        self.root = Path(__file__).resolve().parents[1]
        config_path = self.root / config_path
        
        config = json.loads(config_path.read_text())
        self.notion_api_key = config['notion']['api_key']
        self.notion_database_id = config['notion']['database_id']
        
        self.notion_headers = {
            'Authorization': f'Bearer {self.notion_api_key}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
        
        # 加载CMC mapping
        self.cmc_mapping_file = self.root / 'binance_cmc_mapping.json'
        self.cmc_mapping = self.load_cmc_mapping()
        
        # 数据文件路径
        self.aggregated_file = self.root / 'data' / 'aggregated_usdt_perp_only.json'
    
    def load_cmc_mapping(self) -> Dict[str, Any]:
        """加载CMC映射"""
        if self.cmc_mapping_file.exists():
            return json.loads(self.cmc_mapping_file.read_text())
        return {}
    
    def get_binance_perp_contracts(self) -> Set[str]:
        """获取Binance所有永续合约"""
        try:
            response = requests.get('https://fapi.binance.com/fapi/v1/exchangeInfo', timeout=10)
            response.raise_for_status()
            data = response.json()
            
            contracts = set()
            for symbol in data.get('symbols', []):
                if (symbol.get('contractType') == 'PERPETUAL' and 
                    symbol.get('quoteAsset') == 'USDT' and 
                    symbol.get('status') == 'TRADING'):
                    base = symbol['symbol'][:-4]  # Remove 'USDT'
                    contracts.add(base)
            
            return contracts
        except Exception as e:
            print(f"❌ 获取Binance合约失败: {e}")
            return set()
    
    def get_existing_symbols(self) -> Set[str]:
        """获取已存在的币种"""
        existing = set()
        
        # 从本地数据文件获取
        if self.aggregated_file.exists():
            data = json.loads(self.aggregated_file.read_text())
            existing.update(item['base'] for item in data)
        
        # 从Notion数据库获取
        try:
            url = f"https://api.notion.com/v1/databases/{self.notion_database_id}/query"
            has_more = True
            start_cursor = None
            
            while has_more:
                payload = {"page_size": 100}
                if start_cursor:
                    payload["start_cursor"] = start_cursor
                
                response = requests.post(url, headers=self.notion_headers, json=payload, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                for page in data.get('results', []):
                    props = page.get('properties', {})
                    symbol_prop = props.get('Symbol', {})
                    title = symbol_prop.get('title', [])
                    if title:
                        symbol = title[0].get('text', {}).get('content', '')
                        if symbol:
                            existing.add(symbol)
                
                has_more = data.get('has_more', False)
                start_cursor = data.get('next_cursor')
        
        except Exception as e:
            print(f"⚠️  从Notion获取现有币种时出错: {e}")
        
        return existing
    
    def fetch_cmc_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从CMC mapping获取币种信息，如果不存在则使用基本信息"""
        cmc_info = self.cmc_mapping.get(symbol)
        if cmc_info:
            return {
                'cmc_id': cmc_info.get('id'),
                'cmc_slug': cmc_info.get('slug'),
                'name': cmc_info.get('name', symbol),
                'symbol': symbol
            }
        
        # 如果CMC映射不存在，使用基本信息继续
        print(f"  ⚠️  {symbol}: CMC映射不存在，使用基本信息")
        return {
            'cmc_id': None,
            'cmc_slug': None,
            'name': symbol,
            'symbol': symbol
        }
    
    def fetch_binance_data(self, symbol: str) -> Dict[str, Any]:
        """获取Binance交易数据"""
        data = {
            'perp_price': None,
            'perp_24h_change': None,
            'perp_volume_24h': None,
            'open_interest': None,
            'open_interest_usd': None,
            'funding_rate': None,
            'funding_cycle': None,
            'mark_price': None,
            'index_price': None,
            'basis': None,
            'index_composition_summary': None
        }
        
        try:
            # 获取24h数据
            r = requests.get(
                'https://fapi.binance.com/fapi/v1/ticker/24hr',
                params={'symbol': f'{symbol}USDT'},
                timeout=10
            )
            r.raise_for_status()
            ticker = r.json()
            
            data['perp_price'] = float(ticker['lastPrice'])
            data['perp_24h_change'] = float(ticker['priceChangePercent'])
            data['perp_volume_24h'] = float(ticker['quoteVolume'])
            
            # 获取持仓量
            r = requests.get(
                'https://fapi.binance.com/fapi/v1/openInterest',
                params={'symbol': f'{symbol}USDT'},
                timeout=10
            )
            r.raise_for_status()
            oi = r.json()
            data['open_interest'] = float(oi['openInterest'])
            data['open_interest_usd'] = data['open_interest'] * data['perp_price']
            
            # 获取资金费率
            r = requests.get(
                'https://fapi.binance.com/fapi/v1/premiumIndex',
                params={'symbol': f'{symbol}USDT'},
                timeout=10
            )
            r.raise_for_status()
            premium = r.json()
            data['funding_rate'] = float(premium['lastFundingRate'])
            data['mark_price'] = float(premium['markPrice'])
            data['index_price'] = float(premium['indexPrice'])
            
            # 计算基差
            if data['index_price'] and data['index_price'] > 0:
                data['basis'] = (data['perp_price'] - data['index_price']) / data['index_price']
            
            # 检测资金费率周期
            try:
                r = requests.get(
                    'https://fapi.binance.com/fapi/v1/fundingRate',
                    params={'symbol': f'{symbol}USDT', 'limit': 2},
                    timeout=10
                )
                r.raise_for_status()
                funding_history = r.json()
                if len(funding_history) >= 2:
                    time_diff_ms = funding_history[1]['fundingTime'] - funding_history[0]['fundingTime']
                    time_diff_hours = time_diff_ms / (1000 * 60 * 60)
                    if 3.5 <= time_diff_hours <= 4.5:
                        data['funding_cycle'] = 4
                    elif 7.5 <= time_diff_hours <= 8.5:
                        data['funding_cycle'] = 8
            except:
                pass
            
            # 获取指数组成
            try:
                r = requests.get(
                    'https://fapi.binance.com/fapi/v1/constituents',
                    params={'symbol': f'{symbol}USDT'},
                    timeout=10
                )
                r.raise_for_status()
                comp_data = r.json()
                constituents = comp_data.get('constituents', [])
                if constituents:
                    exchange_weights = {}
                    for c in constituents:
                        exchange = c.get('exchange', 'unknown')
                        weight = float(c.get('weight', 0))
                        exchange_weights[exchange] = weight
                    
                    sorted_exchanges = sorted(exchange_weights.items(), key=lambda x: x[1], reverse=True)
                    summary_parts = [f"{ex} ({w*100:.0f}%)" for ex, w in sorted_exchanges[:5]]
                    summary = ", ".join(summary_parts)
                    if len(sorted_exchanges) > 5:
                        summary += f", +{len(sorted_exchanges)-5} more"
                    data['index_composition_summary'] = summary
            except:
                pass
        
        except Exception as e:
            print(f"  ⚠️  获取{symbol}交易数据失败: {e}")
        
        return data
    
    def create_notion_page(self, symbol: str, cmc_data: Dict[str, Any], binance_data: Dict[str, Any]) -> bool:
        """在Notion中创建新页面"""
        try:
            properties = {
                "Symbol": {
                    "title": [{"text": {"content": symbol}}]
                }
            }
            
            # CMC数据 - 只有在有值时才添加
            if cmc_data.get('name') and cmc_data['name'] != symbol:
                properties["Name"] = {
                    "rich_text": [{"text": {"content": cmc_data['name']}}]
                }
            
            # Binance交易数据 - 只添加有效值
            if binance_data.get('perp_price') is not None:
                properties["Perp Price"] = {"number": round(binance_data['perp_price'], 6)}
            
            if binance_data.get('perp_24h_change') is not None:
                # Notion expects percentage as decimal
                properties["Price change"] = {"number": round(binance_data['perp_24h_change'] / 100, 6)}
            
            if binance_data.get('perp_volume_24h') is not None:
                properties["Perp vol 24h"] = {"number": round(binance_data['perp_volume_24h'], 0)}
            
            if binance_data.get('open_interest_usd') is not None:
                properties["OI"] = {"number": round(binance_data['open_interest_usd'], 0)}
            
            if binance_data.get('funding_rate') is not None:
                properties["Funding"] = {"number": round(binance_data['funding_rate'], 6)}
            
            if binance_data.get('funding_cycle') is not None:
                properties["Funding Cycle"] = {"number": binance_data['funding_cycle']}
            
            if binance_data.get('basis') is not None:
                properties["Basis"] = {"number": round(binance_data['basis'], 6)}
            
            if binance_data.get('index_composition_summary'):
                # 限制文本长度到2000字符
                summary = binance_data['index_composition_summary'][:2000]
                properties["Index Composition"] = {
                    "rich_text": [{"text": {"content": summary}}]
                }
            
            # 创建页面
            url = "https://api.notion.com/v1/pages"
            payload = {
                "parent": {"database_id": self.notion_database_id},
                "properties": properties
            }
            
            response = requests.post(url, headers=self.notion_headers, json=payload, timeout=10)
            
            if response.status_code != 200:
                print(f"  ❌ Notion API错误: {response.status_code}")
                print(f"  响应: {response.text}")
                return False
            
            return True
        
        except Exception as e:
            print(f"  ❌ 创建Notion页面失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def update_aggregated_file(self, new_symbols: List[str]):
        """更新本地数据文件"""
        try:
            # 读取现有数据
            if self.aggregated_file.exists():
                existing_data = json.loads(self.aggregated_file.read_text())
            else:
                existing_data = []
            
            # 为每个新币种获取数据
            for symbol in new_symbols:
                binance_data = self.fetch_binance_data(symbol)
                
                new_entry = {
                    "base": symbol,
                    "spot_price": None,
                    "perp_price": binance_data.get('perp_price'),
                    "openInterest": binance_data.get('open_interest'),
                    "market_cap": None,
                    "fdv": None
                }
                existing_data.append(new_entry)
            
            # 按base排序
            existing_data.sort(key=lambda x: x['base'])
            
            # 保存
            self.aggregated_file.write_text(json.dumps(existing_data, indent=2, ensure_ascii=False))
            print(f"✅ 已更新 {self.aggregated_file.name}")
        
        except Exception as e:
            print(f"❌ 更新数据文件失败: {e}")
    
    def sync_new_contracts(self) -> int:
        """同步新合约"""
        print("🔍 检查新合约...")
        
        # 获取所有合约
        all_contracts = self.get_binance_perp_contracts()
        print(f"📊 Binance永续合约总数: {len(all_contracts)}")
        
        # 获取已存在的币种
        existing_symbols = self.get_existing_symbols()
        print(f"📁 数据库中已有: {len(existing_symbols)}")
        
        # 找出新合约
        new_contracts = sorted(all_contracts - existing_symbols)
        
        if not new_contracts:
            print("✅ 没有发现新合约")
            return 0
        
        print(f"\n🆕 发现 {len(new_contracts)} 个新合约:")
        for symbol in new_contracts:
            print(f"  - {symbol}")
        
        # 同步每个新合约
        success_count = 0
        failed_symbols = []
        print(f"\n开始同步...")
        
        for i, symbol in enumerate(new_contracts, 1):
            print(f"\n[{i}/{len(new_contracts)}] {symbol}")
            
            # 获取CMC数据
            cmc_data = self.fetch_cmc_data(symbol)
            
            # 获取Binance数据
            print(f"  📈 获取交易数据...")
            binance_data = self.fetch_binance_data(symbol)
            
            # 创建Notion页面
            print(f"  📝 创建Notion页面...")
            if self.create_notion_page(symbol, cmc_data, binance_data):
                price_info = []
                if binance_data.get('perp_price'):
                    price_info.append(f"${binance_data['perp_price']:.4f}")
                if binance_data.get('funding_rate'):
                    price_info.append(f"FR: {binance_data['funding_rate']*100:.3f}%")
                
                info_str = " | ".join(price_info) if price_info else ""
                print(f"  ✅ 成功 {info_str}")
                success_count += 1
            else:
                print(f"  ❌ 失败")
                failed_symbols.append(symbol)
            
            # 避免请求过快
            time.sleep(0.5)
        
        # 更新本地数据文件
        if success_count > 0:
            print(f"\n📝 更新本地数据文件...")
            self.update_aggregated_file([s for s in new_contracts])
        
        print(f"\n=== 第一轮同步完成 ===")
        print(f"成功: {success_count}/{len(new_contracts)}")
        
        # 重试失败的合约
        if failed_symbols and len(failed_symbols) <= 50:
            print(f"\n🔄 开始重试失败的 {len(failed_symbols)} 个合约...")
            retry_successful = 0
            still_failed = []
            
            for i, symbol in enumerate(failed_symbols, 1):
                print(f"\n[重试 {i}/{len(failed_symbols)}] {symbol}")
                
                # 获取CMC数据
                cmc_data = self.fetch_cmc_data(symbol)
                
                # 获取Binance数据
                print("  📈 获取交易数据...")
                binance_data = self.fetch_binance_data(symbol)
                
                # 创建Notion页面
                print("  📝 创建Notion页面...")
                if self.create_notion_page(symbol, cmc_data, binance_data):
                    price_info = []
                    if binance_data.get('perp_price'):
                        price_info.append(f"${binance_data['perp_price']:.4f}")
                    if binance_data.get('funding_rate'):
                        price_info.append(f"FR: {binance_data['funding_rate']*100:.3f}%")
                    
                    info_str = " | ".join(price_info) if price_info else ""
                    print(f"  ✅ 成功 {info_str}")
                    retry_successful += 1
                else:
                    print(f"  ❌ 仍然失败")
                    still_failed.append(symbol)
                
                time.sleep(1)  # 重试时等待更长时间
            
            print(f"\n=== 重试结果 ===")
            print(f"重试成功: {retry_successful}/{len(failed_symbols)}")
            print(f"总计成功: {success_count + retry_successful}/{len(new_contracts)}")
            
            if still_failed:
                print(f"\n仍然失败的 {len(still_failed)} 个合约:")
                for symbol in still_failed:
                    print(f"  - {symbol}")
                print("\n💡 建议稍后再次运行脚本重试这些失败的合约")
        
        return success_count


def main():
    """主函数"""
    sync = NewContractSync()
    sync.sync_new_contracts()


if __name__ == "__main__":
    main()
