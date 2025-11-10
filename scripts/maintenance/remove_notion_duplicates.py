#!/usr/bin/env python3
"""Remove duplicate pages from Notion (keep older ones)"""

import requests
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
NOTION_CONFIG_FILE = ROOT / 'config.json'

def remove_duplicates(dry_run=True):
    # Load config
    with NOTION_CONFIG_FILE.open('r') as f:
        config = json.load(f)
    
    headers = {
        'Authorization': f'Bearer {config["notion"]["api_key"]}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }
    
    base_url = 'https://api.notion.com/v1'
    
    # Query all pages
    url = f'{base_url}/databases/{config["notion"]["database_id"]}/query'
    
    all_pages = []
    has_more = True
    start_cursor = None
    
    print("📥 Fetching all pages...")
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
    
    print(f"✅ Found {len(all_pages)} total pages\n")
    
    # Group pages by symbol
    symbol_pages = defaultdict(list)
    for page in all_pages:
        title_prop = page.get('properties', {}).get('Symbol', {})
        if title_prop.get('title'):
            symbol = title_prop['title'][0]['text']['content']
            symbol_pages[symbol].append({
                'id': page['id'],
                'created': page.get('created_time'),
                'page': page
            })
    
    # Find duplicates
    duplicates = {s: pages for s, pages in symbol_pages.items() if len(pages) > 1}
    
    if not duplicates:
        print("✅ No duplicates found!")
        return
    
    print(f"⚠️  Found {len(duplicates)} symbols with duplicates\n")
    
    # Process each duplicate
    pages_to_delete = []
    
    for symbol, pages in sorted(duplicates.items()):
        # Sort by created time (oldest first)
        pages.sort(key=lambda p: p['created'])
        
        print(f"📝 {symbol}:")
        print(f"  Keeping: {pages[0]['id']} (created: {pages[0]['created']})")
        
        for page in pages[1:]:
            print(f"  Deleting: {page['id']} (created: {page['created']})")
            pages_to_delete.append(page)
    
    print(f"\n📊 Summary:")
    print(f"  Total duplicates to remove: {len(pages_to_delete)}")
    
    if dry_run:
        print("\n⚠️  DRY RUN MODE - No pages will be deleted")
        print("Run with --confirm to actually delete pages")
        return
    
    # Delete duplicate pages
    print(f"\n🗑️  Deleting {len(pages_to_delete)} duplicate pages...")
    
    deleted_count = 0
    error_count = 0
    
    for page_data in pages_to_delete:
        page_id = page_data['id']
        try:
            # Archive (soft delete) the page
            delete_url = f'{base_url}/pages/{page_id}'
            payload = {"archived": True}
            
            response = requests.patch(delete_url, headers=headers, json=payload)
            response.raise_for_status()
            
            deleted_count += 1
            print(f"  ✅ Deleted {page_id}")
            
        except Exception as e:
            error_count += 1
            print(f"  ❌ Failed to delete {page_id}: {e}")
    
    print(f"\n✨ Cleanup complete!")
    print(f"  Deleted: {deleted_count}")
    print(f"  Errors: {error_count}")

if __name__ == '__main__':
    import sys
    
    dry_run = '--confirm' not in sys.argv
    
    if dry_run:
        print("🔍 Running in DRY RUN mode...\n")
    else:
        print("⚠️  CONFIRM MODE - Will actually delete duplicates!\n")
    
    remove_duplicates(dry_run=dry_run)
