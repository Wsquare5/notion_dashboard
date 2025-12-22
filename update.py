#!/usr/bin/env python3
"""
从币安API获取最新的交易对列表，并更新到Notion数据库和本地配置文件。
新增功能：在创建新币种页面时，自动从CoinMarketCap获取并填充元数据。
"""
import sys
import json
import time
import requests
from pathlib import Path

# 使用与项目其他脚本相同的导入方式
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
from update_binance_trading_data import NotionClient, CMCClient

def get_all_binance_usdt_perp():
    """从币安获取所有当前在交易中的USDT永续合约列表"""
    try:
        url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # 提取所有以USDT结尾、状态为TRADING的永续合约符号
        symbols = []
        for symbol_info in data.get('symbols', []):
            symbol = symbol_info['symbol']
            status = symbol_info.get('status')
            contract_type = symbol_info.get('contractType')
            
            # 只处理状态为TRADING的永续合约
            if (symbol.endswith('USDT') and 
                contract_type == 'PERPETUAL' and 
                status == 'TRADING'):
                # 去掉USDT后缀，只保留基础币种符号
                base_symbol = symbol.replace('USDT', '')
                symbols.append(base_symbol)
        
        return sorted(symbols)
    except Exception as e:
        print(f"❌ 获取币安交易对失败: {e}")
        return []

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

        return properties, icon_url

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
    notion_client = NotionClient(config['notion']['api_key'], config['notion']['database_id'])
    cmc_client = CMCClient(api_config['coinmarketcap']['api_key'])
    print("✅ API 客户端初始化完成。")

    # --- 3. 获取最新和已有的交易对 ---
    print("\n[3/5] 正在获取数据...")
    print("  - 从币安获取最新交易对...")
    all_binance_symbols = get_all_binance_usdt_perp()
    if not all_binance_symbols:
        print("❌ 无法从币安获取交易对列表，程序终止。")
        return
    print(f"    - 币安返回 {len(all_binance_symbols)} 个USDT永续合约。")

    print("  - 从Notion获取现有交易对...")
    all_pages = notion_client.query_database()
    existing_notion_symbols = []
    for page in all_pages:
        symbol_prop = page.get('properties', {}).get('Symbol', {}).get('title', [])
        if symbol_prop:
            symbol = symbol_prop[0]['text']['content']
            existing_notion_symbols.append(symbol)
    print(f"    - Notion中存在 {len(existing_notion_symbols)} 个交易对。")

    # --- 4. 找出新交易对并创建页面 ---
    print("\n[4/5] 正在比对并创建新页面...")
    new_symbols = [s for s in all_binance_symbols if s not in existing_notion_symbols and s not in blacklist]

    if not new_symbols:
        print("✅ 没有发现新的交易对。")
    else:
        print(f"💎 发现 {len(new_symbols)} 个新交易对: {', '.join(new_symbols)}")
        
        # 只为新币种匹配CMC ID（如果它们在mapping中不存在或cmc_id为空）
        symbols_need_matching = [s for s in new_symbols if s not in cmc_mapping or not cmc_mapping.get(s, {}).get('cmc_id')]
        
        if symbols_need_matching:
            print(f"\n🔍 正在为 {len(symbols_need_matching)} 个新币种匹配 CoinMarketCap ID...")
            for symbol in symbols_need_matching:
                try:
                    # 通过CMC API搜索币种
                    headers = {'X-CMC_PRO_API_KEY': api_config['coinmarketcap']['api_key']}
                    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/map"
                    params = {'symbol': symbol, 'limit': 5}
                    response = requests.get(url, headers=headers, params=params, timeout=30)
                    response.raise_for_status()
                    
                    data = response.json()
                    if data.get('status', {}).get('error_code') == 0:
                        matches = data.get('data', [])
                        if matches:
                            # 优先选择活跃的币种
                            active_matches = [m for m in matches if m.get('is_active') == 1]
                            best_match = active_matches[0] if active_matches else matches[0]
                            
                            cmc_mapping[symbol] = {
                                'cmc_id': best_match['id'],
                                'cmc_slug': best_match['slug'],
                                'cmc_symbol': best_match['symbol']
                            }
                            print(f"  ✅ {symbol} → {best_match['slug']} (ID: {best_match['id']})")
                        else:
                            cmc_mapping[symbol] = {'cmc_id': None}
                            print(f"  ⚠️  {symbol}: 未在CMC找到匹配")
                    
                    time.sleep(0.35)  # CMC API速率限制
                    
                except Exception as e:
                    print(f"  ⚠️  {symbol}: 匹配失败 - {str(e)[:50]}")
                    cmc_mapping[symbol] = {'cmc_id': None}
            
            # 保存更新后的映射
            mapping_data = load_config('config/binance_cmc_mapping.json')
            mapping_data['mapping'] = cmc_mapping
            save_config(mapping_data, 'config/binance_cmc_mapping.json')
            print("✅ CMC映射已更新并保存。")
        
        # 创建新页面
        for symbol in new_symbols:
            print(f"\n  - 正在为新币种 {symbol} 创建Notion页面...")
            
            # 为新币种获取CMC元数据
            cmc_id = cmc_mapping.get(symbol, {}).get('cmc_id')
            properties, icon_url = get_cmc_metadata_for_new_coin(cmc_client, cmc_id)
            
            # 无论是否获取到CMC数据，都先创建页面，确保Symbol存在
            if properties is None:
                properties = {}
                icon_url = None
                print("    - 未能获取CMC元数据，将创建基础页面。")

            # 添加Symbol属性，这是必须的
            properties['Symbol'] = {'title': [{'text': {'content': symbol}}]}
            
            try:
                notion_client.create_page(properties, icon_url, symbol)
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