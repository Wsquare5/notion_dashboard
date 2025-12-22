#!/usr/bin/env python3
"""
从币安API获取最新的交易对列表，并更新到Notion数据库和本地配置文件。
新增功能：在创建新币种页面时，自动从CoinMarketCap获取并填充元数据。
"""
import sys
import json
import time
from pathlib import Path

# --- 关键修复：将项目根目录添加到Python模块搜索路径 ---
# 这能确保 'from scripts.xxx' 能够被正确找到。
sys.path.insert(0, str(Path(__file__).resolve().parent))
# ----------------------------------------------------

# 导入自定义的API客户端
from scripts.notion_api import NotionClient
from scripts.cmc_api import CMCClient
from scripts.binance_api import BinanceClient

def load_config(path):
    """通用配置加载函数，包含错误处理。"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ 配置文件未找到: {path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ 配置文件格式错误: {path}")
        sys.exit(1)

def save_config(data, path):
    """通用配置保存函数。"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def get_cmc_metadata_for_new_coin(cmc_client, cmc_id):
    """为新币种获取并组装CMC元数据。"""
    if not cmc_id:
        return None, None

    try:
        # 加入短暂延时，避免在连续添加多个新币时请求过快
        time.sleep(1.5) # 增加延时以更安全
        print(f"    - 正在为 CMC ID: {cmc_id} 获取元数据...")
        
        token_data = cmc_client.get_token_metadata(cmc_id)
        if not token_data:
            print(f"    - ⚠️ CMC API 未返回 ID: {cmc_id} 的数据")
            return None, None

        metadata = token_data.get('metadata', {})
        quote_data = token_data.get('quote', {})

        properties = {}
        
        # 静态元数据
        if metadata.get('name'):
            properties['Name'] = {"rich_text": [{"text": {"content": metadata['name']}}]}
        
        websites = metadata.get('urls', {}).get('website', [])
        if websites and websites[0]:
            properties['Website'] = {"url": websites[0]}
            
        explorer = metadata.get('urls', {}).get('explorer', [])
        if explorer and explorer[0]:
            properties['Explorer'] = {"url": explorer[0]}

        whitepaper = metadata.get('urls', {}).get('whitepaper', [])
        if whitepaper and whitepaper[0]:
            properties['Whitepaper'] = {"url": whitepaper[0]}

        if metadata.get('date_added'):
            date_str = metadata['date_added'][:10]
            properties['Genesis Date'] = {"date": {"start": date_str}}

        # 动态元数据（初始值）
        if quote_data.get('circulating_supply'):
            properties['Circulating Supply'] = {"number": float(quote_data['circulating_supply'])}
        if quote_data.get('total_supply'):
            properties['Total Supply'] = {"number": float(quote_data['total_supply'])}
        if quote_data.get('max_supply'):
            properties['Max Supply'] = {"number": float(quote_data['max_supply'])}
        
        # Logo (作为页面图标)
        icon_url = metadata.get('logo')
        icon = {"type": "external", "external": {"url": icon_url}} if icon_url else None

        return properties, icon

    except Exception as e:
        print(f"    - ❌ 获取 CMC 元数据时出错: {e}")
        return None, None


def main():
    """主执行函数。"""
    print("\n" + "="*80)
    print("🔄 开始同步币安最新交易对...")
    print("="*80)

    # --- 1. 加载配置 ---
    print("\n[1/5] 正在加载本地配置...")
    config = load_config('config/config.json')
    api_config = load_config('config/api_config.json')
    cmc_mapping = load_config('config/binance_cmc_mapping.json').get('mapping', {})
    blacklist = load_config('config/blacklist.json')
    print("✅ 本地配置加载完成。")

    # --- 2. 初始化客户端 ---
    print("\n[2/5] 正在初始化 API 客户端...")
    binance_client = BinanceClient()
    notion_client = NotionClient(config['notion']['api_key'], config['notion']['database_id'])
    cmc_client = CMCClient(api_config['coinmarketcap']['api_key'])
    print("✅ API 客户端初始化完成。")

    # --- 3. 获取最新和已有的交易对 ---
    print("\n[3/5] 正在获取数据...")
    print("  - 从币安获取最新交易对...")
    all_binance_symbols = binance_client.get_all_usdt_perp_symbols()
    if not all_binance_symbols:
        print("❌ 无法从币安获取交易对列表，程序终止。")
        return
    print(f"    - 币安返回 {len(all_binance_symbols)} 个USDT永续合约。")

    print("  - 从Notion获取现有交易对...")
    existing_notion_symbols = notion_client.get_all_symbols_from_db()
    print(f"    - Notion中存在 {len(existing_notion_symbols)} 个交易对。")

    # --- 4. 找出新交易对并创建页面 ---
    print("\n[4/5] 正在比对并创建新页面...")
    new_symbols = [s for s in all_binance_symbols if s not in existing_notion_symbols and s not in blacklist]

    if not new_symbols:
        print("✅ 没有发现新的交易对。")
    else:
        print(f"💎 发现 {len(new_symbols)} 个新交易对: {', '.join(new_symbols)}")
        for symbol in new_symbols:
            print(f"\n  - 正在为新币种 {symbol} 创建Notion页面...")
            
            # 为新币种获取CMC元数据
            cmc_id = cmc_mapping.get(symbol, {}).get('cmc_id')
            properties, icon = get_cmc_metadata_for_new_coin(cmc_client, cmc_id)
            
            # 无论是否获取到CMC数据，都先创建页面，确保Symbol存在
            if properties is None:
                properties = {}
                print("    - 未能获取CMC元数据，将创建基础页面。")

            # 添加Symbol属性，这是必须的
            properties['Symbol'] = {'title': [{'text': {'content': symbol}}]}
            
            try:
                notion_client.create_page(properties, icon)
                print(f"    - ✅ 成功为 {symbol} 创建了Notion页面。")
            except Exception as e:
                print(f"    - ❌ 为 {symbol} 创建页面失败: {e}")

    # --- 5. 更新本地配置文件 ---
    print("\n[5/5] 正在更新本地 `config.json` 的币种列表...")
    # 合并新旧列表，去重并排序
    final_symbol_list = sorted(list(set(all_binance_symbols) - set(blacklist)))
    config['binance_symbols'] = final_symbol_list
    save_config(config, 'config/config.json')
    print(f"✅ `config.json` 更新完成，现在包含 {len(final_symbol_list)} 个币种。")

    print("\n" + "="*80)
    print("🎉 同步完成！")
    print("="*80)

if __name__ == "__main__":
    main()