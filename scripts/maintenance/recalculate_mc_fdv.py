#!/usr/bin/env python3
"""Recalculate and update MC and FDV in Notion

MC = Circulating Supply × Spot Price
FDV = Total Supply × Spot Price

This script reads existing supply and price data from Notion and recalculates MC/FDV.
"""

import requests
import json
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
NOTION_CONFIG_FILE = ROOT / 'config.json'

class NotionClient:
    """Notion API client"""
    
    def __init__(self, api_key: str, database_id: str):
        self.api_key = api_key
        self.database_id = database_id
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
        self.base_url = 'https://api.notion.com/v1'
    
    def query_all_pages(self) -> list:
        """Query all pages in database"""
        url = f"{self.base_url}/databases/{self.database_id}/query"
        
        all_results = []
        has_more = True
        start_cursor = None
        
        while has_more:
            payload = {}
            if start_cursor:
                payload['start_cursor'] = start_cursor
            
            try:
                response = requests.post(url, headers=self.headers, json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()
                
                all_results.extend(result.get('results', []))
                has_more = result.get('has_more', False)
                start_cursor = result.get('next_cursor')
                
            except Exception as e:
                print(f"❌ Error querying Notion: {e}")
                break
        
        return all_results
    
    def update_page(self, page_id: str, properties: Dict) -> Dict:
        """Update existing page"""
        url = f"{self.base_url}/pages/{page_id}"
        payload = {"properties": properties}
        
        try:
            response = requests.patch(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error updating page: {e}")
            raise


def extract_number(prop: Dict) -> Optional[float]:
    """Extract number from Notion property"""
    if not prop or prop.get('type') != 'number':
        return None
    return prop.get('number')


def extract_title(prop: Dict) -> Optional[str]:
    """Extract title from Notion property"""
    if not prop or prop.get('type') != 'title':
        return None
    title_array = prop.get('title', [])
    if not title_array:
        return None
    return title_array[0].get('text', {}).get('content')


def recalculate_mc_fdv():
    """Recalculate MC and FDV for all tokens"""
    
    print("🚀 Recalculating MC and FDV...\n")
    
    # Load config
    with NOTION_CONFIG_FILE.open('r') as f:
        config = json.load(f)
    
    # Initialize client
    notion_client = NotionClient(
        config['notion']['api_key'],
        config['notion']['database_id']
    )
    
    # Query all pages
    print("📥 Fetching all pages from Notion...")
    all_pages = notion_client.query_all_pages()
    print(f"✅ Found {len(all_pages)} pages\n")
    
    # Process each page
    success_count = 0
    skipped_count = 0
    error_count = 0
    
    for i, page in enumerate(all_pages, 1):
        props = page.get('properties', {})
        page_id = page['id']
        
        # Extract symbol
        symbol = extract_title(props.get('Symbol'))
        if not symbol:
            skipped_count += 1
            continue
        
        print(f"[{i}/{len(all_pages)}] {symbol}")
        
        try:
            # Extract data
            spot_price = extract_number(props.get('Spot Price'))
            perp_price = extract_number(props.get('Perp Price'))
            circulating_supply = extract_number(props.get('Circulating Supply'))
            total_supply = extract_number(props.get('Total Supply'))
            
            # Use spot price if available, otherwise use perp price
            price = spot_price if spot_price else perp_price
            
            # Calculate new values
            new_mc = None
            new_fdv = None
            
            if price and circulating_supply and circulating_supply > 0:
                new_mc = price * circulating_supply
            
            if price and total_supply and total_supply > 0:
                new_fdv = price * total_supply
            
            # Check if we have anything to update
            if new_mc is None and new_fdv is None:
                print(f"  ⚠️  No data to calculate (spot: {spot_price}, perp: {perp_price}, circ: {circulating_supply}, total: {total_supply})")
                skipped_count += 1
                continue
            
            # Build update properties
            update_props = {}
            
            if new_mc is not None:
                update_props["MC"] = {"number": round(new_mc, 2)}
            
            if new_fdv is not None:
                update_props["FDV"] = {"number": round(new_fdv, 2)}
            
            # Update Notion
            notion_client.update_page(page_id, update_props)
            
            # Show what was updated
            info_parts = []
            if new_mc:
                info_parts.append(f"MC: ${new_mc:,.0f}")
            if new_fdv:
                info_parts.append(f"FDV: ${new_fdv:,.0f}")
            
            info_str = " | ".join(info_parts)
            print(f"  ✅ {info_str}")
            
            success_count += 1
            
            # Rate limiting
            if i % 3 == 0:
                import time
                time.sleep(0.3)
            
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            error_count += 1
    
    print(f"\n✨ Recalculation complete!")
    print(f"  Success: {success_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Errors: {error_count}")


if __name__ == '__main__':
    recalculate_mc_fdv()
