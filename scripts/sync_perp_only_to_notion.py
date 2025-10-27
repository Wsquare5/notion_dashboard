#!/usr/bin/env python3
"""
将只有期货的代币数据同步到Notion
"""

import json
import requests
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

class NotionPerpOnlySync:
    def __init__(self, config_path: str = "config.json"):
        """初始化Notion客户端"""
        config = json.loads(Path(config_path).read_text())
        self.api_key = config['notion']['api_key']
        self.perp_only_database_id = config['notion'].get('perp_only_database_id')
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
        
        if not self.perp_only_database_id:
            print("⚠️  注意: 配置中没有找到 perp_only_database_id，将使用主数据库")
            self.perp_only_database_id = config['notion']['database_id']

    def format_perp_only_properties(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化只有期货的代币属性 - 使用与现有数据库相同的字段名"""
        
        def safe_number(value, decimals=4):
            if value is None:
                return None
            return round(float(value), decimals)
        
        def safe_percentage(value, decimals=2):
            if value is None:
                return None
            return round(float(value), decimals)
        
        def safe_currency(value, decimals=0):
            if value is None:
                return None
            return round(float(value), decimals)
        
        # 基础属性 - 使用现有数据库的确切字段名
        properties = {
            "Symbol": {
                "title": [{"text": {"content": token_data['symbol']}}]
            }
        }
        
        # 价格数据
        if token_data.get('perp_price'):
            properties["Perp Price"] = {
                "number": safe_number(token_data['perp_price'], 6)
            }
        
        # 24小时价格变化 - 除以100因为Notion字段设置为percent格式
        if token_data.get('perp_24h_change'):
            properties["Price change"] = {
                "number": token_data['perp_24h_change'] / 100
            }
        
        # 24小时交易量
        if token_data.get('perp_24h_volume'):
            properties["Perp vol 24h"] = {
                "number": safe_currency(token_data['perp_24h_volume'])
            }
        
        # 开仓量数据
        if token_data.get('open_interest_usd'):
            properties["OI"] = {
                "number": safe_currency(token_data['open_interest_usd'])
            }
        
        # 资金费率
        if token_data.get('funding_rate'):
            # Convert to percentage
            funding_rate_pct = token_data['funding_rate'] * 100
            properties["Funding"] = {
                "number": safe_percentage(funding_rate_pct, 4)
            }
        
        # 资金费率周期
        if token_data.get('funding_cycle'):
            properties["Funding Cycle"] = {
                "number": token_data['funding_cycle']
            }
        
        # 基差数据
        if token_data.get('basis_percentage'):
            properties["Basis"] = {
                "number": safe_percentage(token_data['basis_percentage'], 4)
            }
        
        # 指数组成
        if token_data.get('index_composition') and token_data['index_composition'] != "No data":
            properties["Index Composition"] = {
                "rich_text": [{"text": {"content": token_data['index_composition']}}]
            }
        
        return properties

    def find_existing_page(self, symbol: str) -> Optional[str]:
        """查找现有页面"""
        try:
            query_url = f'https://api.notion.com/v1/databases/{self.perp_only_database_id}/query'
            
            filter_data = {
                "filter": {
                    "property": "Symbol",
                    "title": {
                        "equals": symbol
                    }
                }
            }
            
            response = requests.post(query_url, headers=self.headers, json=filter_data)
            if response.status_code == 200:
                results = response.json().get('results', [])
                if results:
                    return results[0]['id']
            
            return None
            
        except Exception as e:
            print(f"⚠️  查找页面失败 {symbol}: {e}")
            return None

    def create_page(self, token_data: Dict[str, Any]) -> bool:
        """创建新页面"""
        try:
            properties = self.format_perp_only_properties(token_data)
            
            # Add icon if available
            page_data = {
                "parent": {"database_id": self.perp_only_database_id},
                "properties": properties
            }
            
            # Try to add logo as icon (simplified approach)
            # For now, we'll just use a default icon for perp-only tokens
            page_data["icon"] = {
                "type": "emoji",
                "emoji": "⚡"  # Lightning bolt for perp-only tokens
            }
            
            url = 'https://api.notion.com/v1/pages'
            response = requests.post(url, headers=self.headers, json=page_data)
            
            if response.status_code == 200:
                return True
            else:
                print(f"❌ 创建页面失败 {token_data['symbol']}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 创建页面异常 {token_data['symbol']}: {e}")
            return False

    def update_page(self, page_id: str, token_data: Dict[str, Any]) -> bool:
        """更新现有页面"""
        try:
            properties = self.format_perp_only_properties(token_data)
            
            page_data = {
                "properties": properties
            }
            
            url = f'https://api.notion.com/v1/pages/{page_id}'
            response = requests.patch(url, headers=self.headers, json=page_data)
            
            if response.status_code == 200:
                return True
            else:
                print(f"❌ 更新页面失败 {token_data['symbol']}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 更新页面异常 {token_data['symbol']}: {e}")
            return False

    def sync_token_to_notion(self, token_data: Dict[str, Any]) -> bool:
        """同步单个代币到Notion"""
        symbol = token_data['symbol']
        
        try:
            # Check if page exists
            existing_page_id = self.find_existing_page(symbol)
            
            if existing_page_id:
                # Update existing page
                success = self.update_page(existing_page_id, token_data)
                if success:
                    print(f"✅ {symbol} updated")
                return success
            else:
                # Create new page
                success = self.create_page(token_data)
                if success:
                    print(f"✅ {symbol} created")
                return success
                
        except Exception as e:
            print(f"❌ 同步失败 {symbol}: {e}")
            return False

def sync_perp_only_data(data_file: str = "data/perp_only_data.json", 
                       config_file: str = "config.json",
                       batch_size: int = 10,
                       delay: float = 0.4) -> None:
    """同步只有期货的代币数据到Notion"""
    
    # Load data
    data_path = Path(data_file)
    if not data_path.exists():
        print(f"❌ 数据文件不存在: {data_file}")
        return
    
    with open(data_path, 'r', encoding='utf-8') as f:
        token_data_list = json.load(f)
    
    print(f"📊 准备同步 {len(token_data_list)} 个只有期货的代币...")
    
    # Initialize Notion client
    notion_client = NotionPerpOnlySync(config_file)
    
    # Process in batches
    successful = 0
    failed = 0
    
    for i in range(0, len(token_data_list), batch_size):
        batch = token_data_list[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        print(f"\n📦 处理批次 {batch_num}: {len(batch)} 个代币")
        
        for token_data in batch:
            success = notion_client.sync_token_to_notion(token_data)
            if success:
                successful += 1
            else:
                failed += 1
            
            time.sleep(delay)  # Rate limiting
        
        if i + batch_size < len(token_data_list):
            print(f"⏳ 批次完成，等待 2 秒...")
            time.sleep(2)
    
    # Final summary
    print(f"\n🎉 同步完成!")
    print(f"✅ 成功: {successful}")
    print(f"❌ 失败: {failed}")
    print(f"📊 成功率: {successful/(successful+failed)*100:.1f}%")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='同步只有期货的代币数据到Notion')
    parser.add_argument('--data-file', default='data/perp_only_data.json', help='数据文件路径')
    parser.add_argument('--config', default='config.json', help='配置文件路径')
    parser.add_argument('--batch-size', type=int, default=10, help='批次大小')
    parser.add_argument('--delay', type=float, default=0.4, help='请求间隔(秒)')
    
    args = parser.parse_args()
    
    sync_perp_only_data(
        data_file=args.data_file,
        config_file=args.config,
        batch_size=args.batch_size,
        delay=args.delay
    )