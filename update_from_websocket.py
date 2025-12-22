#!/usr/bin/env python3
"""
使用 WebSocket 数据更新 Notion
完全替代 REST API，避免封禁

工作流程:
1. 从 WebSocket 数据文件加载交易数据
2. 从 CMC API 获取元数据（logo、网站等）
3. 更新或创建 Notion 页面
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

# 从现有脚本导入
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
from update_binance_trading_data import NotionClient

# Configuration
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / 'config' / 'config.json'
CMC_MAPPING_FILE = BASE_DIR / 'config' / 'binance_cmc_mapping.json'
WS_DATA_FILE = BASE_DIR / 'data' / 'websocket_collected_data.json'


class NotionUpdater:
    """使用 WebSocket 数据更新 Notion"""
    
    def __init__(self, config: dict):
        notion_key = config['notion'].get('token') or config['notion'].get('api_key')
        self.notion = NotionClient(notion_key, config['notion']['database_id'])
        self.database_id = config['notion']['database_id']
        self.cmc_api_key = config.get('cmc', {}).get('api_key', '')
        self.cmc_mapping = self.load_cmc_mapping()
        
    def load_cmc_mapping(self) -> dict:
        """加载 CMC 映射"""
        with open(CMC_MAPPING_FILE, 'r') as f:
            data = json.load(f)
            if 'mapping' in data:
                return data['mapping']
            return data
    
    def get_all_notion_pages(self) -> Dict[str, dict]:
        """获取所有 Notion 页面"""
        print("📥 加载 Notion 页面...")
        
        pages = {}
        
        try:
            all_pages = self.notion.query_database()
            
            for page in all_pages:
                # 提取 Symbol - 使用title属性而不是rich_text
                symbol_prop = page.get('properties', {}).get('Symbol', {})
                if symbol_prop.get('title'):
                    symbol = symbol_prop['title'][0]['text']['content']
                    pages[symbol] = page
            
            print(f"✅ 加载了 {len(pages)} 个页面")
            
        except Exception as e:
            print(f"⚠️  加载页面出错: {e}")
        
        return pages
    
    def get_cmc_metadata(self, symbol: str) -> dict:
        """从 CMC API 获取元数据"""
        
        if symbol not in self.cmc_mapping:
            return {}
        
        cmc_id = self.cmc_mapping[symbol]['cmc_id']
        
        url = 'https://pro-api.coinmarketcap.com/v2/cryptocurrency/info'
        headers = {
            'X-CMC_PRO_API_KEY': self.cmc_api_key,
            'Accept': 'application/json'
        }
        params = {'id': cmc_id}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data and str(cmc_id) in data['data']:
                coin_data = data['data'][str(cmc_id)]
                return {
                    'name': coin_data.get('name', ''),
                    'symbol': coin_data.get('symbol', ''),
                    'logo': coin_data.get('logo', ''),
                    'website': coin_data.get('urls', {}).get('website', [''])[0],
                    'cmc_id': cmc_id,
                    'cmc_slug': coin_data.get('slug', '')
                }
        except Exception as e:
            print(f"⚠️  {symbol} CMC API 出错: {e}")
        
        return {}
    
    def build_page_properties(self, symbol: str, ws_data: dict, metadata: dict) -> dict:
        """构建页面属性"""
        
        properties = {
            "Symbol": {
                "title": [{"text": {"content": symbol}}]
            }
        }
        
        # 名称
        if metadata.get('name'):
            properties["Name"] = {
                "title": [{"text": {"content": f"{metadata['name']} ({symbol})"}}]
            }
        
        # CMC ID
        if metadata.get('cmc_id'):
            properties["CMC ID"] = {"number": metadata['cmc_id']}
        
        # Website
        if metadata.get('website'):
            properties["Website"] = {"url": metadata['website']}
        
        # WebSocket 交易数据 - 使用数据库中实际存在的属性
        if 'price' in ws_data:
            properties["Perp Price"] = {"number": ws_data['price']}
        
        if 'price_change_percent_24h' in ws_data:
            properties["Price change"] = {"number": ws_data['price_change_percent_24h']}
        
        if 'volume_24h' in ws_data:
            properties["Perp vol 24h"] = {"number": ws_data['volume_24h']}
        
        if 'funding_rate' in ws_data:
            properties["Funding"] = {"number": ws_data['funding_rate']}
        
        return properties
    
    def create_page(self, symbol: str, ws_data: dict, metadata: dict) -> bool:
        """创建新页面"""
        
        properties = self.build_page_properties(symbol, ws_data, metadata)
        icon_url = metadata.get('logo')
        
        try:
            self.notion.create_page(properties, icon_url, symbol)
            return True
        except Exception as e:
            print(f"❌ 创建 {symbol} 失败: {e}")
            return False
    
    def update_page(self, page_id: str, symbol: str, ws_data: dict, metadata: dict, update_metadata: bool = True) -> bool:
        """更新现有页面"""
        
        properties = {}
        
        # 总是更新交易数据
        if 'price' in ws_data:
            properties["Perp Price"] = {"number": ws_data['price']}
        
        if 'price_change_percent_24h' in ws_data:
            properties["Price change"] = {"number": ws_data['price_change_percent_24h']}
        
        if 'volume_24h' in ws_data:
            properties["Perp vol 24h"] = {"number": ws_data['volume_24h']}
        
        if 'funding_rate' in ws_data:
            properties["Funding"] = {"number": ws_data['funding_rate']}
        
        # 可选：更新元数据
        if update_metadata:
            if metadata.get('name'):
                properties["Name"] = {
                    "title": [{"text": {"content": f"{metadata['name']} ({symbol})"}}]
                }
            
            if metadata.get('cmc_id'):
                properties["CMC ID"] = {"number": metadata['cmc_id']}
            
            if metadata.get('website'):
                properties["Website"] = {"url": metadata['website']}
        
        try:
            # 使用NotionClient的update_page方法
            icon_url = metadata.get('logo') if update_metadata else None
            self.notion.update_page(page_id, properties, icon_url)
            return True
        except Exception as e:
            print(f"❌ 更新 {symbol} 失败: {e}")
            return False
    
    def process_symbol(self, symbol: str, ws_data: dict, existing_pages: dict, update_metadata: bool) -> dict:
        """处理单个币种"""
        
        result = {
            'symbol': symbol,
            'success': False,
            'action': 'skip',
            'error': None
        }
        
        # 获取 CMC 元数据（如果需要）
        metadata = {}
        if update_metadata:
            metadata = self.get_cmc_metadata(symbol)
        
        # 检查页面是否存在
        if symbol in existing_pages:
            # 更新现有页面
            page_id = existing_pages[symbol]['id']
            success = self.update_page(page_id, symbol, ws_data, metadata, update_metadata)
            
            result['success'] = success
            result['action'] = 'update'
        else:
            # 创建新页面（需要元数据）
            if not metadata:
                metadata = self.get_cmc_metadata(symbol)
            
            success = self.create_page(symbol, ws_data, metadata)
            
            result['success'] = success
            result['action'] = 'create'
        
        return result


def main():
    """主函数"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='使用 WebSocket 数据更新 Notion')
    parser.add_argument('symbols', nargs='*', help='指定要更新的币种（留空则更新所有）')
    parser.add_argument('--update-metadata', action='store_true', help='更新 CMC 元数据（logo、网站等）')
    parser.add_argument('--workers', type=int, default=10, help='并发worker数量')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🚀 WebSocket 数据 → Notion 更新器")
    print("=" * 80)
    print(f"⚙️  Workers: {args.workers}")
    print(f"⚙️  更新元数据: {args.update_metadata}")
    print("=" * 80)
    print()
    
    # 加载配置
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    
    # 加载 WebSocket 数据
    print("📂 加载 WebSocket 数据...")
    if not WS_DATA_FILE.exists():
        print(f"❌ 未找到 WebSocket 数据文件: {WS_DATA_FILE}")
        print(f"   请先运行: python3 collect_websocket_data.py")
        sys.exit(1)
    
    with open(WS_DATA_FILE, 'r') as f:
        ws_data_all = json.load(f)
    
    print(f"✅ 加载了 {len(ws_data_all)} 个币种的数据")
    print()
    
    # 筛选要更新的币种
    if args.symbols:
        symbols_to_update = [s.upper() for s in args.symbols]
        ws_data = {k: v for k, v in ws_data_all.items() if k in symbols_to_update}
        print(f"🎯 指定更新 {len(symbols_to_update)} 个币种")
    else:
        ws_data = ws_data_all
        print(f"🌐 更新所有 {len(ws_data)} 个币种")
    
    print()
    
    # 初始化更新器
    updater = NotionUpdater(config)
    
    # 获取现有页面
    existing_pages = updater.get_all_notion_pages()
    print()
    
    # 并行处理
    print(f"🚀 开始更新 {len(ws_data)} 个币种（{args.workers} workers）...")
    print()
    
    start_time = time.time()
    results = {
        'updated': 0,
        'created': 0,
        'failed': 0,
        'skipped': 0
    }
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                updater.process_symbol,
                symbol,
                data,
                existing_pages,
                args.update_metadata
            ): symbol
            for symbol, data in ws_data.items()
        }
        
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                result = future.result()
                
                if result['success']:
                    if result['action'] == 'update':
                        results['updated'] += 1
                        print(f"✅ 更新 {symbol}")
                    elif result['action'] == 'create':
                        results['created'] += 1
                        print(f"🆕 创建 {symbol}")
                else:
                    results['failed'] += 1
            except Exception as e:
                results['failed'] += 1
                print(f"❌ {symbol} 出错: {e}")
    
    elapsed = time.time() - start_time
    
    # 总结
    print()
    print("=" * 80)
    print("✅ 更新完成")
    print("=" * 80)
    print(f"更新: {results['updated']}")
    print(f"创建: {results['created']}")
    print(f"失败: {results['failed']}")
    print(f"总计: {results['updated'] + results['created']}/{len(ws_data)}")
    print(f"耗时: {elapsed:.1f}秒 ({(results['updated'] + results['created'])/elapsed:.2f} 个/秒)")
    print("=" * 80)


if __name__ == '__main__':
    main()
