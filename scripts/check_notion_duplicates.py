#!/usr/bin/env python3
"""Check for duplicate pages in Notion database"""

import requests
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
NOTION_CONFIG_FILE = ROOT / 'config.json'

def check_duplicates():
    # Load config
    with NOTION_CONFIG_FILE.open('r') as f:
        config = json.load(f)
    
    headers = {
        'Authorization': f'Bearer {config["notion"]["api_key"]}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }
    
    # Query all pages
    url = f'https://api.notion.com/v1/databases/{config["notion"]["database_id"]}/query'
    
    all_pages = []
    has_more = True
    start_cursor = None
    
    while has_more:
        payload = {}
        if start_cursor:
            payload['start_cursor'] = start_cursor
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        all_pages.extend(result.get('results', []))
        has_more = result.get('has_more', False)
        start_cursor = result.get('next_cursor')
    
    # Extract symbols
    symbols = []
    for page in all_pages:
        title_prop = page.get('properties', {}).get('Symbol', {})
        if title_prop.get('title'):
            symbol = title_prop['title'][0]['text']['content']
            symbols.append(symbol)
    
    print(f"📊 Total pages in Notion: {len(all_pages)}")
    print(f"📊 Total symbols extracted: {len(symbols)}")
    print(f"📊 Unique symbols: {len(set(symbols))}")
    
    # Find duplicates
    counts = Counter(symbols)
    duplicates = {s: c for s, c in counts.items() if c > 1}
    
    if duplicates:
        print(f"\n⚠️  Found {len(duplicates)} duplicate symbols:")
        for symbol, count in sorted(duplicates.items()):
            print(f"  • {symbol}: {count} occurrences")
        
        # Find page IDs for duplicates
        print(f"\n🔍 Page IDs for duplicates:")
        for symbol in sorted(duplicates.keys()):
            print(f"\n  {symbol}:")
            for page in all_pages:
                title_prop = page.get('properties', {}).get('Symbol', {})
                if title_prop.get('title'):
                    page_symbol = title_prop['title'][0]['text']['content']
                    if page_symbol == symbol:
                        page_id = page['id']
                        created = page.get('created_time', 'unknown')
                        print(f"    - {page_id} (created: {created})")
    else:
        print("\n✅ No duplicates found")

if __name__ == '__main__':
    check_duplicates()
