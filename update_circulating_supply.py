#!/usr/bin/env python3
"""
定期从 CoinMarketCap 更新所有代币的流通供应量。
"""
import sys
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.notion_api import NotionClient
from scripts.cmc_api import CMCClient

# --- 配置加载 ---
def load_config(path):
    """加载 JSON 配置文件。"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ 配置文件未找到: {path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ 配置文件格式错误: {path}")
        sys.exit(1)

CONFIG = load_config('config/config.json')
API_CONFIG = load_config('config/api_config.json')
CMC_MAPPING = load_config('config/binance_cmc_mapping.json').get('mapping', {})

# --- 初始化客户端 ---
NOTION_CLIENT = NotionClient(CONFIG['notion']['api_key'], CONFIG['notion']['database_id'])
CMC_CLIENT = CMCClient(API_CONFIG['coinmarketcap']['api_key'])

# --- 常量 ---
# CoinMarketCap 的免费套餐建议每分钟不超过10次请求，我们设置一个安全间隔
# 1.5秒 * 40个请求 = 60秒，远低于限制
API_DELAY_SECONDS = 1.5
MAX_WORKERS = 5 # 使用多线程以提高效率，但限制并发数以保护API

def get_all_notion_pages():
    """获取 Notion 数据库中的所有页面。"""
    print("📥 正在从 Notion 加载所有页面...")
    try:
        pages = NOTION_CLIENT.query_database_paginated()
        print(f"✅ 成功加载 {len(pages)} 个页面。")
        return pages
    except Exception as e:
        print(f"❌ 从 Notion 加载页面失败: {e}")
        return []

def update_single_page(page, pbar):
    """更新单个页面的流通供应量。"""
    page_id = page['id']
    properties = page['properties']
    symbol_prop = properties.get('Symbol', {}).get('title', [])
    
    if not symbol_prop:
        pbar.update(1)
        return None, "缺少Symbol属性"
        
    symbol = symbol_prop[0]['text']['content']
    
    if symbol not in CMC_MAPPING or 'cmc_id' not in CMC_MAPPING[symbol]:
        pbar.update(1)
        return symbol, "在CMC映射中未找到"

    cmc_id = CMC_MAPPING[symbol]['cmc_id']
    
    try:
        # 安全间隔，分散API请求
        time.sleep(API_DELAY_SECONDS)
        
        # 从 CMC 获取数据
        token_data = CMC_CLIENT.get_circulating_supply(cmc_id)
        
        if not token_data or 'circulating_supply' not in token_data:
            pbar.update(1)
            return symbol, "CMC API未返回流通量"
            
        circulating_supply = token_data['circulating_supply']
        
        # 准备更新 Notion 的数据
        update_payload = {
            'Circulating Supply': {'number': circulating_supply}
        }
        
        # 更新 Notion 页面
        NOTION_CLIENT.update_page(page_id, update_payload)
        pbar.update(1)
        return symbol, "成功"

    except Exception as e:
        pbar.update(1)
        error_message = str(e)
        if "429" in error_message:
            return symbol, "触发CMC速率限制"
        return symbol, f"失败: {error_message[:40]}"


def main():
    """主执行函数。"""
    print("\n" + "="*80)
    print("🪙 开始从 CoinMarketCap 更新流通供应量...")
    print(f"💡 安全模式: 每个请求间隔 {API_DELAY_SECONDS} 秒，最大并发 {MAX_WORKERS} 个。")
    print("="*80 + "\n")

    pages = get_all_notion_pages()
    if not pages:
        return

    success_count = 0
    error_count = 0
    
    with tqdm(total=len(pages), desc="更新进度", ncols=100) as pbar:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # 创建未来任务列表
            futures = [executor.submit(update_single_page, page, pbar) for page in pages]
            
            for future in as_completed(futures):
                symbol, status = future.result()
                if status == "成功":
                    success_count += 1
                else:
                    # 可以在这里记录更详细的错误日志
                    # print(f"  - {symbol}: {status}")
                    error_count += 1
    
    print("\n" + "="*80)
    print("🎉 更新完成！")
    print(f"✅ 成功: {success_count} 个")
    print(f"❌ 失败/跳过: {error_count} 个")
    print("="*80)


if __name__ == "__main__":
    main()
