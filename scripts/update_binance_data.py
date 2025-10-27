#!/usr/bin/env python3
"""Update Binance trading data for all tokens in Notion

This script updates real-time trading data from Binance (prices, volumes, funding rates, etc.)
without overwriting the basic token info from CMC.

Usage:
    python3 scripts/update_binance_data.py
    python3 scripts/update_binance_data.py --symbols BTC,ETH,SOL
    python3 scripts/update_binance_data.py --limit 50
"""

import requests
import json
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent))
from enhanced_data_fetcher import fetch_enhanced_data, TokenData

# Configuration
ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = ROOT / 'config.json'


def load_config() -> Dict:
    """Load Notion configuration"""
    with CONFIG_FILE.open('r') as f:
        return json.load(f)


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
    
    def query_database(self, filter_params: Dict = None) -> List[Dict]:
        """Query database pages"""
        url = f"{self.base_url}/databases/{self.database_id}/query"
        
        all_results = []
        has_more = True
        start_cursor = None
        
        while has_more:
            payload = {}
            if filter_params:
                payload['filter'] = filter_params
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
    
    def get_page_by_symbol(self, symbol: str) -> Optional[Dict]:
        """Find page by symbol"""
        filter_params = {
            "property": "Symbol",
            "title": {
                "equals": symbol
            }
        }
        
        results = self.query_database(filter_params)
        return results[0] if results else None
    
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


def build_trading_properties(token_data: TokenData) -> Dict:
    """Build Notion properties for trading data only (not basic token info)"""
    
    properties = {}
    
    # Price fields
    if token_data.spot_price:
        properties["Spot Price"] = {"number": token_data.spot_price}
    if token_data.perp_price:
        properties["Perp Price"] = {"number": token_data.perp_price}
    
    # 24h price change
    if hasattr(token_data, 'spot_24h_change') and token_data.spot_24h_change is not None:
        properties["Price change"] = {"number": token_data.spot_24h_change / 100}
    elif hasattr(token_data, 'perp_24h_change') and token_data.perp_24h_change is not None:
        properties["Price change"] = {"number": token_data.perp_24h_change / 100}
    
    # Basis (spot-perp spread)
    if token_data.basis is not None:
        properties["Basis"] = {"number": token_data.basis}
    
    # Volume fields
    if token_data.spot_volume_24h:
        properties["Spot vol 24h"] = {"number": token_data.spot_volume_24h}
    if token_data.perp_volume_24h:
        properties["Perp vol 24h"] = {"number": token_data.perp_volume_24h}
    
    # Open Interest
    if getattr(token_data, 'open_interest_usd', None) is not None:
        properties["OI"] = {"number": token_data.open_interest_usd}
    elif token_data.open_interest:
        properties["OI"] = {"number": token_data.open_interest}
    
    # Funding rate and cycle
    if token_data.funding_rate is not None:
        properties["Funding"] = {"number": token_data.funding_rate}
    if hasattr(token_data, 'funding_cycle') and token_data.funding_cycle is not None:
        properties["Funding Cycle"] = {"number": token_data.funding_cycle}
    
    # Index composition
    if token_data.index_composition_summary:
        properties["Index Composition"] = {
            "rich_text": [{"text": {"content": token_data.index_composition_summary}}]
        }
    
    return properties


def get_all_notion_symbols(client: NotionClient) -> List[str]:
    """Get all symbols from Notion database"""
    print("📥 Fetching symbols from Notion database...")
    
    pages = client.query_database()
    symbols = []
    
    for page in pages:
        title_prop = page.get('properties', {}).get('Symbol', {})
        if title_prop.get('title'):
            symbol = title_prop['title'][0]['text']['content']
            symbols.append(symbol)
    
    print(f"✅ Found {len(symbols)} symbols in Notion")
    return symbols


def update_binance_data(symbols: List[str] = None, limit: int = None):
    """Update Binance trading data for tokens"""
    
    print("🚀 Starting Binance data update...\n")
    
    # Load config
    config = load_config()
    notion_client = NotionClient(
        config['notion']['api_key'],
        config['notion']['database_id']
    )
    
    # Determine which symbols to update
    if symbols:
        symbols_to_update = symbols
    else:
        # Get all symbols from Notion
        symbols_to_update = get_all_notion_symbols(notion_client)
        
        if limit:
            symbols_to_update = symbols_to_update[:limit]
    
    print(f"📊 Updating {len(symbols_to_update)} tokens\n")
    
    success_count = 0
    error_count = 0
    skip_count = 0
    
    for i, symbol in enumerate(symbols_to_update, 1):
        try:
            print(f"[{i}/{len(symbols_to_update)}] Processing {symbol}...", end=' ')
            
            # Check if page exists
            page = notion_client.get_page_by_symbol(symbol)
            if not page:
                print("⚠️  Not found in Notion, skipping")
                skip_count += 1
                continue
            
            # Fetch Binance data (fetch_enhanced_data expects a list)
            token_data_list = fetch_enhanced_data([symbol])
            
            if not token_data_list or len(token_data_list) == 0:
                print("⚠️  No Binance data available")
                skip_count += 1
                continue
            
            token_data = token_data_list[0]
            
            # Build properties (trading data only)
            properties = build_trading_properties(token_data)
            
            if not properties:
                print("⚠️  No trading data to update")
                skip_count += 1
                continue
            
            # Update page
            notion_client.update_page(page['id'], properties)
            
            # Show what was updated
            updates = []
            if token_data.spot_price:
                updates.append(f"Spot: ${token_data.spot_price:.4f}")
            if token_data.perp_price:
                updates.append(f"Perp: ${token_data.perp_price:.4f}")
            if token_data.funding_rate is not None:
                updates.append(f"FR: {token_data.funding_rate:.4f}%")
            if token_data.spot_volume_24h or token_data.perp_volume_24h:
                vol = token_data.spot_volume_24h or token_data.perp_volume_24h
                updates.append(f"Vol: ${vol:,.0f}")
            
            print(f"✅ {' | '.join(updates)}")
            success_count += 1
            
            # Rate limiting
            time.sleep(0.2)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            error_count += 1
            continue
    
    print(f"\n✨ Update complete!")
    print(f"  ✅ Success: {success_count}")
    print(f"  ⚠️  Skipped: {skip_count}")
    print(f"  ❌ Errors: {error_count}")


def main():
    parser = argparse.ArgumentParser(description='Update Binance trading data in Notion')
    parser.add_argument('--symbols', type=str, help='Comma-separated list of symbols (e.g., BTC,ETH,SOL)')
    parser.add_argument('--limit', type=int, help='Limit number of tokens to update')
    
    args = parser.parse_args()
    
    symbols = args.symbols.split(',') if args.symbols else None
    
    update_binance_data(symbols=symbols, limit=args.limit)


if __name__ == '__main__':
    main()
