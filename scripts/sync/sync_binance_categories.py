#!/usr/bin/env python3
"""
Sync Binance categories to Notion database
This script fetches categories from Binance Perpetual API and updates all coins in Notion
"""

import json
import requests
import time
from pathlib import Path

# Configuration
NOTION_CONFIG_FILE = Path(__file__).parent.parent / "config.json"

def load_config():
    """Load Notion configuration"""
    with NOTION_CONFIG_FILE.open('r') as f:
        config = json.load(f)
    return config['notion']['api_key'], config['notion']['database_id']

def fetch_all_binance_categories():
    """Fetch all categories from Binance Perpetual API
    
    Returns:
        dict: {symbol: [categories]}
    """
    print("📡 Fetching categories from Binance Perpetual API...")
    
    try:
        resp = requests.get('https://fapi.binance.com/fapi/v1/exchangeInfo', timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        categories_map = {}
        for s in data['symbols']:
            if s['symbol'].endswith('USDT') and s['status'] == 'TRADING':
                symbol = s['symbol'].replace('USDT', '')
                categories = s.get('underlyingSubType', [])
                if categories:
                    categories_map[symbol] = categories
        
        print(f"✅ Found categories for {len(categories_map)} symbols")
        return categories_map
        
    except Exception as e:
        print(f"❌ Failed to fetch categories: {e}")
        return {}

def get_all_notion_pages(api_key, database_id):
    """Get all pages from Notion database"""
    print("\n📚 Fetching all pages from Notion...")
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json'
    }
    
    url = f'https://api.notion.com/v1/databases/{database_id}/query'
    all_pages = []
    has_more = True
    next_cursor = None
    
    while has_more:
        payload = {}
        if next_cursor:
            payload['start_cursor'] = next_cursor
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            all_pages.extend(data.get('results', []))
            has_more = data.get('has_more', False)
            next_cursor = data.get('next_cursor')
            
            print(f"  Fetched {len(all_pages)} pages...", end='\r')
            time.sleep(0.35)
            
        except Exception as e:
            print(f"\n  ⚠️  Error: {e}")
            break
    
    print(f"\n✅ Found {len(all_pages)} pages in Notion")
    return all_pages

def update_page_categories(page_id, categories, api_key):
    """Update a page with categories"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json'
    }
    
    url = f'https://api.notion.com/v1/pages/{page_id}'
    payload = {
        'properties': {
            'Categories': {
                'multi_select': [{'name': cat} for cat in categories]
            }
        }
    }
    
    response = requests.patch(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()

def check_categories_field(api_key, database_id):
    """Check if Categories field exists in database"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json'
    }
    
    url = f'https://api.notion.com/v1/databases/{database_id}'
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    props = data.get('properties', {})
    
    if 'Categories' not in props:
        print("\n❌ 错误：Notion database 中没有 'Categories' 字段")
        print("\n请先在 Notion 中添加 'Categories' 字段（类型：Multi-select）")
        print("\n步骤:")
        print("1. 打开 Notion database")
        print("2. 点击右上角的 '+' 添加新列")
        print("3. 字段名称: Categories")
        print("4. 字段类型: Multi-select")
        return False
    
    return True

def main():
    """Main function"""
    print("=" * 80)
    print("🏷️  Sync Binance Categories to Notion")
    print("=" * 80 + "\n")
    
    # Load config
    api_key, database_id = load_config()
    
    # Check if Categories field exists
    if not check_categories_field(api_key, database_id):
        return
    
    # Fetch categories from Binance
    categories_map = fetch_all_binance_categories()
    if not categories_map:
        print("❌ No categories found")
        return
    
    # Get all pages from Notion
    pages = get_all_notion_pages(api_key, database_id)
    if not pages:
        print("❌ No pages found in Notion")
        return
    
    # Update each page
    print("\n🔄 Updating pages with categories...\n")
    print("=" * 80)
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for page in pages:
        try:
            # Get symbol
            symbol_prop = page.get('properties', {}).get('Symbol', {})
            if not symbol_prop.get('title'):
                continue
            
            symbol = symbol_prop['title'][0]['text']['content']
            
            # Check if this symbol has categories
            if symbol in categories_map:
                categories = categories_map[symbol]
                
                # Check if already has same categories
                current_cats_prop = page.get('properties', {}).get('Categories', {})
                current_cats = [c['name'] for c in current_cats_prop.get('multi_select', [])]
                
                if set(current_cats) == set(categories):
                    print(f"⏭️  {symbol}: Already up-to-date {categories}")
                    skipped_count += 1
                else:
                    # Update
                    update_page_categories(page['id'], categories, api_key)
                    print(f"✅ {symbol}: {categories}")
                    updated_count += 1
                    time.sleep(0.35)
            else:
                print(f"⚠️  {symbol}: No categories found in Binance")
                skipped_count += 1
                
        except Exception as e:
            print(f"❌ {symbol}: Error - {e}")
            error_count += 1
    
    # Summary
    print("\n" + "=" * 80)
    print(f"\n✅ 同步完成!")
    print(f"   Updated: {updated_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Errors: {error_count}")
    print(f"   Total: {len(pages)}")

if __name__ == '__main__':
    main()
