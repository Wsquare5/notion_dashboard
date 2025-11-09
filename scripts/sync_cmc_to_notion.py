#!/usr/bin/env python3
"""Sync CoinMarketCap token data to Notion

This script:
1. Loads local CMC mapping (binance_cmc_mapping.json)
2. Fetches detailed token info from CMC API
3. Syncs to Notion database

Usage:
    python3 scripts/sync_cmc_to_notion.py
    python3 scripts/sync_cmc_to_notion.py --symbols BTC,ETH,SOL
    python3 scripts/sync_cmc_to_notion.py --limit 50
"""

import requests
import json
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

# Configuration
ROOT = Path(__file__).resolve().parents[1]
API_CONFIG_FILE = ROOT / 'api_config.json'
CMC_MAPPING_FILE = ROOT / 'binance_cmc_mapping.json'
NOTION_CONFIG_FILE = ROOT / 'config.json'


def load_api_config() -> Dict:
    """Load API configuration"""
    with API_CONFIG_FILE.open('r') as f:
        return json.load(f)


def load_cmc_mapping() -> Dict[str, Dict]:
    """Load local CMC mapping"""
    with CMC_MAPPING_FILE.open('r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get('mapping', {})


def load_notion_config() -> Dict:
    """Load Notion configuration"""
    with NOTION_CONFIG_FILE.open('r') as f:
        return json.load(f)


class CMCClient:
    """CoinMarketCap API client"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://pro-api.coinmarketcap.com/v1"
        self.headers = {
            'X-CMC_PRO_API_KEY': api_key,
            'Accept': 'application/json'
        }
    
    def get_metadata(self, cmc_ids: List[int]) -> Dict:
        """Get token metadata in batch (up to 1000 ids per request)
        
        Returns info like: name, symbol, logo, description, urls, tags, etc.
        """
        if not cmc_ids:
            return {}
        
        url = f"{self.base_url}/cryptocurrency/info"
        params = {
            'id': ','.join(map(str, cmc_ids))
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get('status', {}).get('error_code') == 0:
                return result.get('data', {})
            else:
                print(f"❌ CMC API error: {result.get('status', {}).get('error_message')}")
                return {}
                
        except Exception as e:
            print(f"❌ Error fetching CMC metadata: {e}")
            return {}
    
    def get_quotes(self, cmc_ids: List[int]) -> Dict:
        """Get current price quotes for tokens
        
        Returns: price, volume, market cap, circulating supply, etc.
        """
        if not cmc_ids:
            return {}
        
        url = f"{self.base_url}/cryptocurrency/quotes/latest"
        params = {
            'id': ','.join(map(str, cmc_ids))
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get('status', {}).get('error_code') == 0:
                return result.get('data', {})
            else:
                print(f"❌ CMC API error: {result.get('status', {}).get('error_message')}")
                return {}
                
        except Exception as e:
            print(f"❌ Error fetching CMC quotes: {e}")
            return {}


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
            "rich_text": {
                "equals": symbol
            }
        }
        
        results = self.query_database(filter_params)
        return results[0] if results else None
    
    def create_page(self, properties: Dict, icon_url: str = None) -> Dict:
        """Create new page"""
        url = f"{self.base_url}/pages"
        payload = {
            "parent": {"database_id": self.database_id},
            "properties": properties
        }
        
        # Add icon if provided
        if icon_url:
            payload["icon"] = {
                "type": "external",
                "external": {"url": icon_url}
            }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error creating page: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            raise
    
    def update_page(self, page_id: str, properties: Dict, icon_url: str = None) -> Dict:
        """Update existing page"""
        url = f"{self.base_url}/pages/{page_id}"
        payload = {"properties": properties}
        
        # Add icon if provided
        if icon_url:
            payload["icon"] = {
                "type": "external",
                "external": {"url": icon_url}
            }
        
        try:
            response = requests.patch(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error updating page: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            raise


def build_notion_properties(symbol: str, metadata: Dict, quote: Dict, verbose: bool = False) -> Dict:
    """Build Notion page properties from CMC data
    
    Note: Only updates CMC-specific fields, does not overwrite trading data from Binance
    
    CMC API Limitations (Basic/Free tier):
    - ❌ No ATH/ATL data (requires Pro/Enterprise plan)
    - ❌ No historical OHLCV (requires Pro/Enterprise plan)
    - ✅ Logo URL available in metadata
    - ✅ Description, website, genesis date available
    - ✅ Supply data, market cap, FDV available
    """
    
    properties = {}
    
    # Track extra info for logging
    extra_info = {}
    
    # Basic info from metadata
    if metadata:
        # Logo URL
        if 'logo' in metadata and metadata['logo']:
            logo_url = metadata['logo']
            extra_info['logo'] = logo_url
            # Store in CoinGecko ID field (repurposed for logo)
            properties["CoinGecko ID"] = {
                "rich_text": [{
                    "text": {
                        "content": logo_url
                    }
                }]
            }
        
        # Description (for logging only, no field in Notion currently)
        if 'description' in metadata and metadata['description']:
            desc = metadata['description'][:200]  # First 200 chars
            extra_info['description'] = desc
        
        # Website
        if 'urls' in metadata and 'website' in metadata['urls'] and metadata['urls']['website']:
            website = metadata['urls']['website'][0]
            if website:
                properties["Website"] = {
                    "url": website
                }
                extra_info['website'] = website
        
        # Genesis Date (date_added from CMC)
        if 'date_added' in metadata:
            try:
                date_str = metadata['date_added'].split('T')[0]
                properties["Genesis Date"] = {
                    "date": {"start": date_str}
                }
                extra_info['genesis'] = date_str
            except:
                pass
    
    # Supply data from quote (only if available)
    if quote:
        # Circulating Supply - use official first, fallback to self-reported
        circ = quote.get('circulating_supply')
        if not circ or circ == 0:
            circ = quote.get('self_reported_circulating_supply')
        
        if circ and circ > 0:
            properties["Circulating Supply"] = {
                "number": round(circ, 2)
            }
            extra_info['circ_supply'] = f"{circ:,.0f}"
        
        # Total Supply
        if 'total_supply' in quote and quote['total_supply']:
            total = quote['total_supply']
            properties["Total Supply"] = {
                "number": round(total, 2)
            }
            extra_info['total_supply'] = f"{total:,.0f}"
        
        # Max Supply
        if 'max_supply' in quote and quote['max_supply']:
            max_sup = quote['max_supply']
            properties["Max Supply"] = {
                "number": round(max_sup, 2)
            }
            extra_info['max_supply'] = f"{max_sup:,.0f}"
        
        # Market Cap and FDV from quote
        if 'quote' in quote and 'USD' in quote['quote']:
            usd_data = quote['quote']['USD']
            
            # Market Cap (MC field in Notion)
            if 'market_cap' in usd_data and usd_data['market_cap']:
                mc = usd_data['market_cap']
                properties["MC"] = {
                    "number": round(mc, 2)
                }
                extra_info['market_cap'] = f"${mc:,.0f}"
            
            # FDV
            if 'fully_diluted_market_cap' in usd_data and usd_data['fully_diluted_market_cap']:
                fdv = usd_data['fully_diluted_market_cap']
                properties["FDV"] = {
                    "number": round(fdv, 2)
                }
                extra_info['fdv'] = f"${fdv:,.0f}"
    
    # Return properties and extra info for logging
    return properties, extra_info if verbose else properties


def sync_tokens_to_notion(symbols: List[str] = None, limit: int = None):
    """Main sync function"""
    
    print("🚀 Starting CMC to Notion sync...\n")
    
    # Load configurations
    api_config = load_api_config()
    cmc_mapping = load_cmc_mapping()
    notion_config = load_notion_config()
    
    # Initialize clients
    cmc_client = CMCClient(api_config['coinmarketcap']['api_key'])
    notion_client = NotionClient(
        notion_config['notion']['api_key'],
        notion_config['notion']['database_id']
    )
    
    # Determine which symbols to sync
    if symbols:
        symbols_to_sync = symbols
    else:
        # Get all symbols with valid CMC IDs
        symbols_to_sync = [
            symbol for symbol, data in cmc_mapping.items()
            if data.get('cmc_id') is not None
        ]
        
        if limit:
            symbols_to_sync = symbols_to_sync[:limit]
    
    print(f"📊 Found {len(symbols_to_sync)} symbols to sync\n")
    
    # Group symbols by CMC ID for batch requests
    symbol_to_id = {}
    for symbol in symbols_to_sync:
        if symbol in cmc_mapping and cmc_mapping[symbol].get('cmc_id'):
            symbol_to_id[symbol] = cmc_mapping[symbol]['cmc_id']
    
    if not symbol_to_id:
        print("❌ No valid CMC IDs found")
        return
    
    # Fetch data from CMC in batches (max 1000 per request, but we'll do smaller batches)
    batch_size = 100
    all_metadata = {}
    all_quotes = {}
    
    cmc_ids = list(symbol_to_id.values())
    
    print(f"📥 Fetching data from CMC for {len(cmc_ids)} tokens...")
    
    for i in range(0, len(cmc_ids), batch_size):
        batch_ids = cmc_ids[i:i + batch_size]
        print(f"  Batch {i // batch_size + 1}: {len(batch_ids)} tokens")
        
        # Fetch metadata
        metadata_batch = cmc_client.get_metadata(batch_ids)
        all_metadata.update(metadata_batch)
        
        # Rate limiting
        time.sleep(1)
        
        # Fetch quotes
        quotes_batch = cmc_client.get_quotes(batch_ids)
        all_quotes.update(quotes_batch)
        
        # Rate limiting
        time.sleep(1)
    
    print(f"✅ Fetched data for {len(all_metadata)} tokens\n")
    
    # Sync to Notion
    print("📤 Syncing to Notion...")
    
    success_count = 0
    error_count = 0
    failed_symbols = []
    
    for symbol, cmc_id in symbol_to_id.items():
        try:
            cmc_id_str = str(cmc_id)
            metadata = all_metadata.get(cmc_id_str, {})
            quote = all_quotes.get(cmc_id_str, {})
            
            # Build properties with verbose output
            result = build_notion_properties(symbol, metadata, quote, verbose=True)
            if isinstance(result, tuple):
                properties, extra_info = result
            else:
                properties = result
                extra_info = {}
            
            # Extract logo URL from metadata
            logo_url = None
            if metadata and 'logo' in metadata:
                logo_url = metadata['logo']
            
            # Check if page exists
            existing_page = notion_client.get_page_by_symbol(symbol)
            
            if existing_page:
                # Update existing page
                page_id = existing_page['id']
                notion_client.update_page(page_id, properties, icon_url=logo_url)
                action = "Updated"
            else:
                # Create new page (must include Symbol as title)
                properties["Symbol"] = {
                    "title": [{"text": {"content": symbol}}]
                }
                notion_client.create_page(properties, icon_url=logo_url)
                action = "Created"
            
            # Show what was synced
            info_parts = []
            if 'logo' in extra_info:
                info_parts.append(f"🖼️ Logo")
            if 'genesis' in extra_info:
                info_parts.append(f"📅 Genesis: {extra_info['genesis']}")
            if 'website' in extra_info:
                info_parts.append(f"🌐 Website")
            if 'circ_supply' in extra_info:
                info_parts.append(f"💰 Supply: {extra_info['circ_supply']}")
            if 'market_cap' in extra_info:
                info_parts.append(f"📊 MC: {extra_info['market_cap']}")
            
            info_str = " | ".join(info_parts) if info_parts else "basic info"
            print(f"  ✅ {action}: {symbol:12s} - {info_str}")
            
            success_count += 1
            
            # Rate limiting for Notion API
            time.sleep(0.3)
            
        except Exception as e:
            print(f"  ❌ Failed: {symbol} - {e}")
            error_count += 1
            failed_symbols.append(symbol)
    
    print(f"\n✨ Sync complete!")
    print(f"  Success: {success_count}")
    print(f"  Errors: {error_count}")
    
    # Retry failed symbols until all succeed
    retry_round = 1
    while failed_symbols and retry_round <= 5:
        print(f"\n🔄 Retry round {retry_round}: {len(failed_symbols)} failed symbols...")
        time.sleep(2)  # Wait before retry
        
        retry_failed = []
        retry_success = 0
        
        for symbol in failed_symbols:
            try:
                cmc_id = symbol_to_id.get(symbol)
                if not cmc_id:
                    continue
                
                cmc_id_str = str(cmc_id)
                metadata = all_metadata.get(cmc_id_str, {})
                quote = all_quotes.get(cmc_id_str, {})
                
                # Build properties
                result = build_notion_properties(symbol, metadata, quote, verbose=True)
                if isinstance(result, tuple):
                    properties, extra_info = result
                else:
                    properties = result
                    extra_info = {}
                
                # Extract logo URL
                logo_url = None
                if metadata and 'logo' in metadata:
                    logo_url = metadata['logo']
                
                # Check if page exists
                existing_page = notion_client.get_page_by_symbol(symbol)
                
                if existing_page:
                    page_id = existing_page['id']
                    notion_client.update_page(page_id, properties, icon_url=logo_url)
                    action = "Updated"
                else:
                    properties["Symbol"] = {
                        "title": [{"text": {"content": symbol}}]
                    }
                    notion_client.create_page(properties, icon_url=logo_url)
                    action = "Created"
                
                print(f"  ✅ {action}: {symbol}")
                retry_success += 1
                success_count += 1
                error_count -= 1
                
                time.sleep(0.3)
                
            except Exception as e:
                print(f"  ❌ Still failing: {symbol} - {str(e)[:60]}...")
                retry_failed.append(symbol)
        
        print(f"  Retry result: {retry_success}/{len(failed_symbols)} recovered")
        failed_symbols = retry_failed
        retry_round += 1
    
    if failed_symbols:
        print(f"\n⚠️  {len(failed_symbols)} symbols still failed after retries: {', '.join(failed_symbols[:10])}")
        if len(failed_symbols) > 10:
            print(f"    ... and {len(failed_symbols) - 10} more")
    else:
        print(f"\n🎉 All symbols synced successfully!")
    
    print(f"\n=== Final Statistics ===")
    print(f"✅ Total Success: {success_count}")
    print(f"❌ Total Errors: {error_count}")


def main():
    parser = argparse.ArgumentParser(description='Sync CMC data to Notion')
    parser.add_argument('--symbols', type=str, help='Comma-separated list of symbols (e.g., BTC,ETH,SOL)')
    parser.add_argument('--limit', type=int, help='Limit number of tokens to sync')
    
    args = parser.parse_args()
    
    symbols = args.symbols.split(',') if args.symbols else None
    
    sync_tokens_to_notion(symbols=symbols, limit=args.limit)


if __name__ == '__main__':
    main()
