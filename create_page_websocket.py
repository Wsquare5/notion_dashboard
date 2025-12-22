#!/usr/bin/env python3
"""
使用 WebSocket 数据和 CMC API 创建 Notion 页面
避免 Binance REST API 封禁
"""

import json
import sys
from pathlib import Path
from notion_client import Client

# Configuration
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / 'config' / 'config.json'
CMC_MAPPING_FILE = BASE_DIR / 'config' / 'binance_cmc_mapping.json'
WS_DATA_FILE = BASE_DIR / 'data' / 'websocket_collected_data.json'


def load_config():
    """加载配置"""
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    return config


def load_cmc_mapping():
    """加载 CMC 映射"""
    with open(CMC_MAPPING_FILE, 'r') as f:
        data = json.load(f)
        if 'mapping' in data:
            return data['mapping']
        return data


def load_websocket_data():
    """加载 WebSocket 数据"""
    if not WS_DATA_FILE.exists():
        return {}
    
    with open(WS_DATA_FILE, 'r') as f:
        return json.load(f)


def get_cmc_metadata(symbol: str, cmc_api_key: str):
    """从 CMC API 获取元数据"""
    import requests
    
    cmc_mapping = load_cmc_mapping()
    
    if symbol not in cmc_mapping:
        print(f"❌ {symbol} 不在 CMC 映射中")
        return None
    
    cmc_id = cmc_mapping[symbol]['cmc_id']
    
    url = 'https://pro-api.coinmarketcap.com/v2/cryptocurrency/info'
    headers = {
        'X-CMC_PRO_API_KEY': cmc_api_key,
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
                'description': coin_data.get('description', ''),
                'cmc_id': cmc_id,
                'cmc_slug': coin_data.get('slug', '')
            }
    except Exception as e:
        print(f"⚠️  获取 CMC 元数据失败: {e}")
    
    return None


def create_notion_page(notion: Client, database_id: str, symbol: str, metadata: dict, ws_data: dict):
    """创建 Notion 页面"""
    
    properties = {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": f"{metadata['name']} ({symbol})"
                    }
                }
            ]
        },
        "Symbol": {
            "rich_text": [
                {
                    "text": {
                        "content": symbol
                    }
                }
            ]
        }
    }
    
    # CMC ID
    if 'cmc_id' in metadata:
        properties["CMC ID"] = {
            "number": metadata['cmc_id']
        }
    
    # Icon
    icon = None
    if metadata.get('logo'):
        icon = {
            "type": "external",
            "external": {
                "url": metadata['logo']
            }
        }
    
    # WebSocket 交易数据
    if ws_data:
        if 'price' in ws_data:
            properties["Price"] = {
                "number": ws_data['price']
            }
        
        if 'price_change_percent_24h' in ws_data:
            properties["24h Change %"] = {
                "number": ws_data['price_change_percent_24h']
            }
        
        if 'volume_24h' in ws_data:
            properties["24h Volume"] = {
                "number": ws_data['volume_24h']
            }
        
        if 'high_24h' in ws_data:
            properties["24h High"] = {
                "number": ws_data['high_24h']
            }
        
        if 'low_24h' in ws_data:
            properties["24h Low"] = {
                "number": ws_data['low_24h']
            }
        
        if 'funding_rate' in ws_data:
            properties["Funding Rate"] = {
                "number": ws_data['funding_rate']
            }
    
    # Website
    if metadata.get('website'):
        properties["Website"] = {
            "url": metadata['website']
        }
    
    # 创建页面
    try:
        page = notion.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            icon=icon
        )
        return page
    except Exception as e:
        print(f"❌ 创建页面失败: {e}")
        return None


def main():
    """主函数"""
    
    if len(sys.argv) < 2:
        print("用法: python3 create_page_websocket.py SYMBOL")
        print("示例: python3 create_page_websocket.py RLS")
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    
    print(f"🚀 使用 WebSocket 数据创建 {symbol} 页面")
    print()
    
    # 加载配置
    config = load_config()
    notion_token = config['notion']['token']
    database_id = config['notion']['database_id']
    cmc_api_key = config['cmc']['api_key']
    
    # 初始化 Notion 客户端
    notion = Client(auth=notion_token)
    
    # 加载 WebSocket 数据
    ws_data_all = load_websocket_data()
    ws_data = ws_data_all.get(symbol, {})
    
    if ws_data:
        print(f"✅ 找到 WebSocket 数据:")
        print(f"   价格: ${ws_data.get('price', 'N/A')}")
        print(f"   24h 涨跌: {ws_data.get('price_change_percent_24h', 'N/A')}%")
        print(f"   24h 成交量: {ws_data.get('volume_24h', 'N/A')}")
    else:
        print(f"⚠️  未找到 WebSocket 数据，将仅创建元数据")
    
    print()
    
    # 获取 CMC 元数据
    print(f"📡 从 CMC API 获取元数据...")
    metadata = get_cmc_metadata(symbol, cmc_api_key)
    
    if not metadata:
        print(f"❌ 无法获取 {symbol} 的元数据")
        sys.exit(1)
    
    print(f"✅ 获取到元数据:")
    print(f"   名称: {metadata['name']}")
    print(f"   CMC ID: {metadata['cmc_id']}")
    print(f"   Logo: {metadata['logo'][:50]}...")
    print(f"   Website: {metadata.get('website', 'N/A')}")
    print()
    
    # 创建 Notion 页面
    print(f"📝 创建 Notion 页面...")
    page = create_notion_page(notion, database_id, symbol, metadata, ws_data)
    
    if page:
        print(f"✅ 页面创建成功！")
        print(f"   URL: https://www.notion.so/{page['id'].replace('-', '')}")
    else:
        print(f"❌ 页面创建失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
