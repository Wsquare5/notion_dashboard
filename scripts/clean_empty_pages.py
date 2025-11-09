#!/usr/bin/env python3
"""
清理Notion数据库中的空页面和重复页面
"""

import requests
import json
import time
from pathlib import Path
from collections import defaultdict

CONFIG_FILE = Path('config.json')


def load_config():
    """加载配置文件"""
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_all_pages(api_key: str, database_id: str) -> list:
    """获取数据库中的所有页面"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }
    
    url = f'https://api.notion.com/v1/databases/{database_id}/query'
    all_pages = []
    has_more = True
    start_cursor = None
    
    while has_more:
        payload = {}
        if start_cursor:
            payload['start_cursor'] = start_cursor
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                data = response.json()
                all_pages.extend(data.get('results', []))
                has_more = data.get('has_more', False)
                start_cursor = data.get('next_cursor')
                print(f"已获取 {len(all_pages)} 个页面...")
            else:
                print(f"❌ 查询失败: {response.status_code}")
                break
        except Exception as e:
            print(f"❌ 错误: {e}")
            break
        
        time.sleep(0.3)  # 避免请求过快
    
    return all_pages


def delete_page(api_key: str, page_id: str) -> bool:
    """删除（归档）一个页面"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }
    
    url = f'https://api.notion.com/v1/pages/{page_id}'
    payload = {'archived': True}
    
    try:
        response = requests.patch(url, headers=headers, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"  ❌ 删除失败: {e}")
        return False


def analyze_pages(pages: list) -> dict:
    """分析页面，找出空页面和重复页面"""
    empty_pages = []
    symbol_pages = defaultdict(list)
    
    for page in pages:
        page_id = page['id']
        props = page.get('properties', {})
        
        # 获取Symbol（Symbol是title类型，不是rich_text！）
        symbol_prop = props.get('Symbol', {}).get('title', [])  # ✅ 修复：改为title
        symbol = symbol_prop[0]['plain_text'] if symbol_prop else ''  # ✅ 修复：使用plain_text
        
        # 获取Name（Name也是rich_text类型）
        name_prop = props.get('Name', {}).get('rich_text', [])  # ✅ 修复：Name是rich_text
        name = name_prop[0]['plain_text'] if name_prop else ''  # ✅ 修复：使用plain_text
        
        created_time = page.get('created_time', '')
        last_edited = page.get('last_edited_time', '')
        
        page_info = {
            'id': page_id,
            'symbol': symbol,
            'name': name,
            'created_time': created_time,
            'last_edited': last_edited
        }
        
        # 如果Symbol和Name都为空，标记为空页面
        if not symbol and not name:
            empty_pages.append(page_info)
        elif symbol:
            symbol_pages[symbol].append(page_info)
    
    return {
        'empty_pages': empty_pages,
        'symbol_pages': symbol_pages
    }


def main():
    """主函数"""
    config = load_config()
    api_key = config['notion']['api_key']
    database_id = config['notion']['database_id']
    
    print("🔍 获取所有页面...")
    pages = get_all_pages(api_key, database_id)
    print(f"✅ 共获取 {len(pages)} 个页面\n")
    
    print("📊 分析页面...")
    analysis = analyze_pages(pages)
    
    empty_pages = analysis['empty_pages']
    symbol_pages = analysis['symbol_pages']
    
    # 找出有重复的Symbol
    duplicates = {symbol: pages_list for symbol, pages_list in symbol_pages.items() 
                  if len(pages_list) > 1}
    
    print(f"\n=== 分析结果 ===")
    print(f"空页面（Symbol和Name都为空）: {len(empty_pages)} 个")
    print(f"有重复的Symbol: {len(duplicates)} 个")
    
    # 显示空页面
    if empty_pages:
        print(f"\n📋 空页面列表:")
        for i, page in enumerate(empty_pages[:20], 1):
            print(f"  {i}. ID: {page['id']}")
            print(f"     创建: {page['created_time']}")
            print(f"     编辑: {page['last_edited']}")
    
    # 显示重复页面
    if duplicates:
        print(f"\n📋 重复的Symbol（前20个）:")
        for i, (symbol, pages_list) in enumerate(list(duplicates.items())[:20], 1):
            print(f"\n  {i}. {symbol} - {len(pages_list)} 个页面:")
            for j, page in enumerate(pages_list, 1):
                print(f"     {j}) ID: {page['id']}")
                print(f"        Name: {page['name'] or '(空)'}")
                print(f"        创建: {page['created_time']}")
                print(f"        编辑: {page['last_edited']}")
    
    # 询问是否删除
    print(f"\n{'='*60}")
    if empty_pages:
        confirm = input(f"\n是否删除 {len(empty_pages)} 个空页面? (yes/no): ").strip().lower()
        if confirm == 'yes':
            print(f"\n🗑️  开始删除空页面...")
            deleted = 0
            for page in empty_pages:
                if delete_page(api_key, page['id']):
                    deleted += 1
                    print(f"  ✅ 已删除: {page['id']}")
                else:
                    print(f"  ❌ 删除失败: {page['id']}")
                time.sleep(0.3)
            print(f"\n✅ 成功删除 {deleted}/{len(empty_pages)} 个空页面")
        else:
            print("取消删除空页面")
    
    # 处理重复Symbol（保留最新的，删除旧的）
    if duplicates:
        confirm = input(f"\n是否清理重复的Symbol（保留最新编辑的，删除旧的）? (yes/no): ").strip().lower()
        if confirm == 'yes':
            print(f"\n🗑️  开始清理重复页面...")
            deleted = 0
            for symbol, pages_list in duplicates.items():
                # 按最后编辑时间排序，保留最新的
                sorted_pages = sorted(pages_list, key=lambda x: x['last_edited'], reverse=True)
                keep_page = sorted_pages[0]
                delete_pages = sorted_pages[1:]
                
                print(f"\n  {symbol}:")
                print(f"    保留: {keep_page['id']} (最后编辑: {keep_page['last_edited']})")
                
                for page in delete_pages:
                    if delete_page(api_key, page['id']):
                        deleted += 1
                        print(f"    ✅ 已删除: {page['id']} (编辑: {page['last_edited']})")
                    else:
                        print(f"    ❌ 删除失败: {page['id']}")
                    time.sleep(0.3)
            
            print(f"\n✅ 成功删除 {deleted} 个重复页面")
        else:
            print("取消删除重复页面")


if __name__ == '__main__':
    main()
