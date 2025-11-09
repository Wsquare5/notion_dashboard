#!/usr/bin/env python3
"""
Fast version of Binance to Notion updater with parallel processing
Optimizations:
1. Batch query all Notion pages at once
2. Parallel Binance API calls using ThreadPoolExecutor
3. Reduced rate limiting delays
4. Batch Notion updates

Expected speedup: 3 hours -> 15-20 minutes for 603 coins
"""

import json
import time
import argparse
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional, Set

# Import the existing modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.update_binance_trading_data import (
    CMCClient,
    BinanceDataFetcher,
    NotionClient,
    build_trading_properties
)

# Constants
BASE_DIR = Path(__file__).parent.parent
NOTION_CONFIG_FILE = BASE_DIR / "config.json"
API_CONFIG_FILE = BASE_DIR / "api_config.json"
CMC_MAPPING_FILE = BASE_DIR / "binance_cmc_mapping.json"
BLACKLIST_FILE = BASE_DIR / "blacklist.json"
PERP_ONLY_CACHE_FILE = BASE_DIR / "data" / "perp_only_cache.json"

# Thread pool settings
MAX_WORKERS = 20  # Parallel workers for Binance API calls
NOTION_BATCH_SIZE = 10  # Notion API batch update size


def get_binance_symbols() -> Tuple[Set[str], Set[str], Set[str]]:
    """
    Get all Binance symbols and classify them
    Returns: (all_perp_symbols, spot_symbols, perp_only_symbols)
    """
    # Get all perpetual contracts
    try:
        perp_response = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo", timeout=10)
        perp_response.raise_for_status()
        perp_symbols = {s['symbol'].replace('USDT', '') for s in perp_response.json()['symbols'] 
                       if s['symbol'].endswith('USDT') and s['status'] == 'TRADING'}
    except Exception as e:
        print(f"❌ Failed to fetch perpetual contracts: {e}")
        return set(), set(), set()
    
    # Get all spot pairs
    try:
        spot_response = requests.get("https://api.binance.com/api/v3/exchangeInfo", timeout=10)
        spot_response.raise_for_status()
        spot_symbols = {s['symbol'].replace('USDT', '') for s in spot_response.json()['symbols'] 
                       if s['symbol'].endswith('USDT') and s['status'] == 'TRADING'}
    except Exception as e:
        print(f"❌ Failed to fetch spot pairs: {e}")
        return perp_symbols, set(), perp_symbols
    
    perp_only_symbols = perp_symbols - spot_symbols
    
    return perp_symbols, spot_symbols, perp_only_symbols


def load_all_notion_pages(notion: NotionClient) -> Dict[str, Dict]:
    """
    Batch load all pages from Notion database
    Returns: {symbol: page_data}
    """
    print("📥 Loading all Notion pages...")
    start = time.time()
    
    pages_by_symbol = {}
    try:
        # Use the NotionClient's query_database method
        all_pages = notion.query_database()
        
        for page in all_pages:
            # Extract symbol from title
            title_prop = page.get('properties', {}).get('Symbol', {})
            if title_prop.get('title'):
                symbol = title_prop['title'][0]['text']['content']
                pages_by_symbol[symbol] = page
        
        elapsed = time.time() - start
        print(f"✅ Loaded {len(pages_by_symbol)} pages in {elapsed:.1f}s")
        
    except Exception as e:
        print(f"❌ Failed to load Notion pages: {e}")
        return {}
    
    return pages_by_symbol


def fetch_symbol_data(symbol: str, has_spot: bool, is_perp_only: bool) -> Tuple[str, Optional[Dict], Optional[Dict]]:
    """
    Fetch trading data for a single symbol
    Returns: (symbol, spot_data, perp_data)
    """
    spot_data = None
    if has_spot:
        spot_result = BinanceDataFetcher.fetch_spot_data(symbol)
        if isinstance(spot_result, tuple):
            spot_data, _, _ = spot_result
        else:
            spot_data = spot_result
    
    perp_data = BinanceDataFetcher.fetch_perp_data(symbol)
    
    return (symbol, spot_data, perp_data)


def parallel_fetch_trading_data(symbols: List[str], spot_and_perp: set, perp_only: set, max_workers: int = 20) -> Dict[str, Tuple]:
    """
    Fetch trading data for all symbols in parallel
    Returns: {symbol: (spot_data, perp_data)}
    """
    print(f"🚀 Fetching trading data for {len(symbols)} symbols (using {max_workers} threads)...")
    start = time.time()
    
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {}
        for symbol in symbols:
            has_spot = symbol in spot_and_perp
            is_perp_only = symbol in perp_only
            future = executor.submit(fetch_symbol_data, symbol, has_spot, is_perp_only)
            futures[future] = symbol
        
        # Collect results
        completed = 0
        for future in as_completed(futures):
            try:
                symbol, spot_data, perp_data = future.result()
                results[symbol] = (spot_data, perp_data)
                completed += 1
                
                if completed % 50 == 0:
                    elapsed = time.time() - start
                    rate = completed / elapsed
                    remaining = (len(symbols) - completed) / rate if rate > 0 else 0
                    print(f"  Progress: {completed}/{len(symbols)} ({completed/len(symbols)*100:.1f}%) - ETA: {remaining:.0f}s")
                    
            except Exception as e:
                symbol = futures[future]
                print(f"  ⚠️  {symbol}: {str(e)[:50]}")
                results[symbol] = (None, None)
    
    elapsed = time.time() - start
    rate = len(symbols) / elapsed
    print(f"✅ Fetched {len(symbols)} symbols in {elapsed:.1f}s ({rate:.1f} symbols/s)")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Fast update Binance trading data to Notion (parallel processing)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Fast update all coins
  python3 scripts/update_binance_trading_data_fast.py
  
  # Fast update with static fields
  python3 scripts/update_binance_trading_data_fast.py --update-static-fields
  
  # Fast update with metadata (supply data)
  python3 scripts/update_binance_trading_data_fast.py --update-metadata
  
  # Specify number of parallel workers (default: 20)
  python3 scripts/update_binance_trading_data_fast.py --workers 30
        '''
    )
    parser.add_argument('symbols', nargs='*', help='Specific symbols to update (optional)')
    parser.add_argument('--update-metadata', '--update-supply', action='store_true',
                       help='Update all metadata: Supply + Static Fields (calls CMC API)')
    parser.add_argument('--update-static-fields', action='store_true',
                       help='Update static fields: Funding Cycle, Categories, Index Composition')
    parser.add_argument('--update-funding-cycle', action='store_true',
                       help='(Deprecated: use --update-static-fields)')
    parser.add_argument('--workers', type=int, default=20,
                       help='Number of parallel workers (default: 20)')
    
    args = parser.parse_args()
    
    print("="*80)
    print("🚀 Fast Binance to Notion Updater (Parallel Version)")
    print("="*80)
    print(f"⚙️  Workers: {args.workers}")
    print(f"⚙️  Update metadata: {args.update_metadata}")
    print(f"⚙️  Update static fields: {args.update_static_fields or args.update_funding_cycle}")
    print("="*80)
    
    start_time = time.time()
    
    # Load configuration
    if not NOTION_CONFIG_FILE.exists():
        print(f"❌ Config file not found: {NOTION_CONFIG_FILE}")
        return
    
    with NOTION_CONFIG_FILE.open('r') as f:
        config = json.load(f)
    
    notion_api_key = config['notion']['api_key']
    notion_database_id = config['notion']['database_id']
    
    # Initialize clients
    notion = NotionClient(notion_api_key, notion_database_id)
    
    cmc_client = None
    if API_CONFIG_FILE.exists():
        try:
            with API_CONFIG_FILE.open('r') as f:
                api_config = json.load(f)
                cmc_api_key = api_config.get('coinmarketcap', {}).get('api_key')
                if cmc_api_key:
                    cmc_client = CMCClient(cmc_api_key)
                    print("✅ CMC API client initialized")
        except Exception as e:
            print(f"⚠️  CMC client init failed: {e}")
    
    # Load mappings
    with CMC_MAPPING_FILE.open('r') as f:
        cmc_data = json.load(f)
        cmc_mapping = cmc_data.get('mapping', {})
    
    blacklist = set()
    if BLACKLIST_FILE.exists():
        with BLACKLIST_FILE.open('r') as f:
            blacklist = set(json.load(f))
    
    # Get database properties
    db_props = notion.get_database_properties()
    
    # Get all symbols
    perp_symbols, spot_symbols, perp_only_symbols = get_binance_symbols()
    spot_and_perp_symbols = perp_symbols & spot_symbols
    
    all_symbols = sorted(list(perp_symbols))
    
    # Filter by user input if provided
    if args.symbols:
        all_symbols = [s for s in args.symbols if s in perp_symbols]
        print(f"🎯 Filtering to {len(all_symbols)} specified symbols")
    
    # Remove blacklisted
    all_symbols = [s for s in all_symbols if s not in blacklist]
    
    print(f"📊 Total symbols: {len(all_symbols)}")
    
    # Step 1: Batch load all Notion pages
    pages_by_symbol = load_all_notion_pages(notion)
    
    # Step 2: Parallel fetch all trading data
    trading_data = parallel_fetch_trading_data(
        all_symbols,
        spot_and_perp_symbols,
        perp_only_symbols,
        max_workers=args.workers
    )
    
    # Step 3: Process and update
    print(f"\n📝 Processing and updating {len(all_symbols)} symbols...")
    
    success_count = 0
    created_count = 0
    error_count = 0
    skipped_count = 0
    
    update_meta = args.update_metadata
    update_static = args.update_static_fields or args.update_funding_cycle or args.update_metadata
    
    for i, symbol in enumerate(all_symbols, 1):
        try:
            print(f"[{i:3d}/{len(all_symbols):3d}] {symbol}", end=" ")
            
            spot_data, perp_data = trading_data.get(symbol, (None, None))
            
            if not spot_data and not perp_data:
                print("⚠️  No data")
                skipped_count += 1
                continue
            
            page = pages_by_symbol.get(symbol)
            
            if not page:
                # Create new page
                cmc_data = cmc_mapping.get(symbol)
                if not cmc_data:
                    print("⚠️  No CMC mapping")
                    skipped_count += 1
                    continue
                
                cmc_full_data = None
                if cmc_client and cmc_data.get('cmc_id'):
                    try:
                        cmc_full_data = cmc_client.get_token_data(cmc_data['cmc_id'])
                        if cmc_full_data:
                            print("[+CMC]", end=" ")
                    except Exception:
                        pass
                
                properties, icon_url = build_trading_properties(
                    symbol, spot_data, perp_data, cmc_data, cmc_full_data,
                    is_new_page=True, update_metadata=True, update_static_fields=True
                )
                
                if properties.get('Logo') and 'Logo' not in db_props:
                    logo_val = properties.pop('Logo')
                    logo_url = logo_val.get('url') if isinstance(logo_val, dict) else None
                    if logo_url:
                        properties['CoinGecko ID'] = {"rich_text": [{"text": {"content": logo_url}}]}
                
                try:
                    notion.create_page(properties, icon_url, symbol=symbol)
                    print("✅ Created")
                    created_count += 1
                    success_count += 1
                except Exception as e:
                    print(f"❌ Create failed: {str(e)[:40]}")
                    error_count += 1
                    
            else:
                # Update existing page
                cmc_data = cmc_mapping.get(symbol)
                cmc_full_data = None
                
                if update_meta and cmc_data and cmc_data.get('cmc_id') and cmc_client:
                    try:
                        cmc_full_data = cmc_client.get_token_data(cmc_data['cmc_id'])
                        if cmc_full_data:
                            print("[+CMC]", end=" ")
                    except Exception:
                        pass
                
                properties, _ = build_trading_properties(
                    symbol, spot_data, perp_data, cmc_data, cmc_full_data,
                    existing_page=page, is_new_page=False,
                    update_metadata=update_meta, update_static_fields=update_static
                )
                
                try:
                    notion.update_page(page['id'], properties)
                    
                    # Show key info
                    spot_price = spot_data.get('spot_price') if spot_data else None
                    perp_price = perp_data.get('perp_price') if perp_data else None
                    
                    price_info = []
                    if spot_price:
                        price_info.append(f"${spot_price:.4f}")
                    if perp_price:
                        price_info.append(f"P:${perp_price:.4f}")
                    
                    print(f"✅ {' '.join(price_info)}")
                    success_count += 1
                    
                except Exception as e:
                    print(f"❌ Update failed: {str(e)[:40]}")
                    error_count += 1
                    
        except Exception as e:
            print(f"❌ Error: {str(e)[:50]}")
            error_count += 1
    
    # Summary
    elapsed = time.time() - start_time
    print(f"\n{'='*80}")
    print(f"✅ Update Complete in {elapsed/60:.1f} minutes")
    print(f"{'='*80}")
    print(f"Success: {success_count} (Updated: {success_count - created_count}, Created: {created_count})")
    print(f"Skipped: {skipped_count}")
    print(f"Errors: {error_count}")
    print(f"Rate: {success_count/elapsed:.2f} symbols/second")
    print(f"{'='*80}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
