#!/usr/bin/env python3
"""
删除 Notion 数据库中重复的页面
保留最早创建的页面，删除后创建的重复页面
"""

import requests
import json
import time
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Configuration
ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = ROOT / 'config.json'


def get_all_pages(api_key: str, database_id: str):
    """获取数据库中的所有页面"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Notion-Version': '2022-06-28'
    }
    
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    
    all_pages = []
    has_more = True
    start_cursor = None
    
    print("📡 获取所有页面...")
    
    while has_more:
        payload = {}
        if start_cursor:
            payload['start_cursor'] = start_cursor
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            all_pages.extend(result.get('results', []))
            has_more = result.get('has_more', False)
            start_cursor = result.get('next_cursor')
            
            print(f"   已获取 {len(all_pages)} 个页面...", end='\r')
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            break
    
    print(f"\n✅ 总共获取 {len(all_pages)} 个页面")
    return all_pages


def find_duplicates(pages):
    """找出重复的 Symbol"""
    symbol_pages = defaultdict(list)
    
    for page in pages:
        try:
            symbol_prop = page['properties'].get('Symbol', {})
            title_list = symbol_prop.get('title', [])
            if title_list:
                symbol = title_list[0].get('text', {}).get('content', '')
                if symbol:
                    symbol_pages[symbol].append({
                        'id': page['id'],
                        'created_time': page.get('created_time', ''),
                        'last_edited_time': page.get('last_edited_time', '')
                    })
        except Exception as e:
            print(f"⚠️  解析页面出错: {e}")
    
    # 找出重复的 Symbol
    duplicates = {}
    for symbol, page_list in symbol_pages.items():
        if len(page_list) > 1:
            # 按创建时间排序，最早的在前
            sorted_pages = sorted(page_list, key=lambda p: p['created_time'])
            duplicates[symbol] = sorted_pages
    
    return duplicates


def delete_page(api_key: str, page_id: str):
    """删除页面（归档）"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json'
    }
    
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {"archived": True}
    
    try:
        response = requests.patch(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"   ❌ 删除失败: {e}")
        return False


def main():
    """主函数"""
    print("🗑️  删除 Notion 数据库中的重复页面\n")
    
    # 加载配置
    if not CONFIG_FILE.exists():
        print(f"❌ 找不到配置文件: {CONFIG_FILE}")
        return
    
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    
    api_key = config['notion']['api_key']
    database_id = config['notion']['database_id']
    
    # 获取所有页面
    pages = get_all_pages(api_key, database_id)
    if not pages:
        return
    
    # 找出重复页面
    print("\n🔍 查找重复的 Symbol...")
    duplicates = find_duplicates(pages)
    
    if not duplicates:
        print("✅ 没有发现重复的 Symbol！")
        return
    
    print(f"\n🚨 发现 {len(duplicates)} 个重复的 Symbol:\n")
    
    total_to_delete = sum(len(pages) - 1 for pages in duplicates.values())
    
    for symbol, page_list in sorted(duplicates.items()):
        keep_page = page_list[0]  # 保留最早创建的
        delete_pages = page_list[1:]  # 删除后创建的
        
        keep_time = datetime.fromisoformat(keep_page['created_time'].replace('Z', '+00:00'))
        keep_str = keep_time.strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"📄 {symbol}:")
        print(f"   ✅ 保留: {keep_page['id']} (创建于 {keep_str})")
        
        for page in delete_pages:
            delete_time = datetime.fromisoformat(page['created_time'].replace('Z', '+00:00'))
            delete_str = delete_time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"   🗑️  删除: {page['id']} (创建于 {delete_str})")
        print()
    
    # 确认删除
    print(f"⚠️  将删除 {total_to_delete} 个重复页面")
    confirm = input("确认删除？(yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("❌ 已取消")
        return
    
    # 执行删除
    print(f"\n🗑️  开始删除...\n")
    
    deleted_count = 0
    failed_count = 0
    
    for symbol, page_list in sorted(duplicates.items()):
        delete_pages = page_list[1:]  # 跳过第一个（保留）
        
        print(f"处理 {symbol}:")
        for page in delete_pages:
            print(f"   删除 {page['id']}...", end=" ")
            if delete_page(api_key, page['id']):
                print("✅")
                deleted_count += 1
            else:
                print("❌")
                failed_count += 1
            time.sleep(0.3)  # 避免 API 限速
    
    print(f"\n{'='*60}")
    print(f"✅ 删除完成!")
    print(f"   成功: {deleted_count}")
    print(f"   失败: {failed_count}")


if __name__ == "__main__":
    main()
