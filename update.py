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
sys.path.insert(0, str(Path(__file__).parent))

from scripts.update_binance_trading_data import (
    CMCClient,
    BinanceDataFetcher,
    NotionClient,
    build_trading_properties
)

# Constants
BASE_DIR = Path(__file__).parent
NOTION_CONFIG_FILE = BASE_DIR / "config" / "config.json"
API_CONFIG_FILE = BASE_DIR / "config" / "api_config.json"
CMC_MAPPING_FILE = BASE_DIR / "config" / "binance_cmc_mapping.json"
BLACKLIST_FILE = BASE_DIR / "config" / "blacklist.json"
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


def parallel_fetch_trading_data(symbols: List[str], spot_and_perp: set, perp_only: set, max_workers: int = 20, max_retries: int = 3) -> Dict[str, Tuple]:
    """
    Fetch trading data for all symbols in parallel with automatic retry for failed requests
    Returns: {symbol: (spot_data, perp_data)}
    """
    print(f"🚀 Fetching trading data for {len(symbols)} symbols (using {max_workers} threads)...")
    start = time.time()
    
    results = {}
    failed_symbols = []
    
    # First attempt - parallel fetch
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
            symbol = futures[future]
            try:
                symbol, spot_data, perp_data = future.result()
                
                # Check if we got any data
                if not spot_data and not perp_data:
                    failed_symbols.append(symbol)
                    results[symbol] = (None, None)
                else:
                    results[symbol] = (spot_data, perp_data)
                
                completed += 1
                
                if completed % 50 == 0:
                    elapsed = time.time() - start
                    rate = completed / elapsed
                    remaining = (len(symbols) - completed) / rate if rate > 0 else 0
                    print(f"  Progress: {completed}/{len(symbols)} ({completed/len(symbols)*100:.1f}%) - ETA: {remaining:.0f}s")
                    
            except Exception as e:
                print(f"  ⚠️  {symbol}: {str(e)[:50]}")
                failed_symbols.append(symbol)
                results[symbol] = (None, None)
    
    elapsed = time.time() - start
    rate = len(symbols) / elapsed
    print(f"✅ Initial fetch: {len(symbols) - len(failed_symbols)}/{len(symbols)} successful in {elapsed:.1f}s ({rate:.1f} symbols/s)")
    
    # Retry failed symbols
    if failed_symbols:
        print(f"\n🔄 Retrying {len(failed_symbols)} failed symbols (max {max_retries} attempts)...")
        
        retry_count = 0
        while failed_symbols and retry_count < max_retries:
            retry_count += 1
            print(f"\n  Attempt {retry_count}/{max_retries}: Retrying {len(failed_symbols)} symbols...")
            
            # Wait a bit before retry to avoid rate limiting
            time.sleep(2)
            
            retry_failed = []
            retry_start = time.time()
            
            # Retry with fewer workers to reduce network pressure
            retry_workers = max(5, max_workers // 4)
            
            with ThreadPoolExecutor(max_workers=retry_workers) as executor:
                futures = {}
                for symbol in failed_symbols:
                    has_spot = symbol in spot_and_perp
                    is_perp_only = symbol in perp_only
                    future = executor.submit(fetch_symbol_data, symbol, has_spot, is_perp_only)
                    futures[future] = symbol
                
                for future in as_completed(futures):
                    symbol = futures[future]
                    try:
                        symbol, spot_data, perp_data = future.result()
                        
                        if not spot_data and not perp_data:
                            retry_failed.append(symbol)
                        else:
                            results[symbol] = (spot_data, perp_data)
                            print(f"    ✅ {symbol} - retry successful")
                            
                    except Exception as e:
                        retry_failed.append(symbol)
                        print(f"    ⚠️  {symbol} - retry failed: {str(e)[:40]}")
            
            retry_elapsed = time.time() - retry_start
            recovered = len(failed_symbols) - len(retry_failed)
            
            if recovered > 0:
                print(f"  ✅ Recovered {recovered} symbols in {retry_elapsed:.1f}s")
            
            failed_symbols = retry_failed
            
            if not failed_symbols:
                break
        
        # Final summary
        total_elapsed = time.time() - start
        total_success = len(symbols) - len(failed_symbols)
        
        print(f"\n{'='*80}")
        print(f"📊 Fetch Summary:")
        print(f"  ✅ Successful: {total_success}/{len(symbols)} ({total_success/len(symbols)*100:.1f}%)")
        if failed_symbols:
            print(f"  ❌ Still failed: {len(failed_symbols)} symbols")
            print(f"  Failed symbols: {', '.join(failed_symbols[:20])}")
            if len(failed_symbols) > 20:
                print(f"                  ... and {len(failed_symbols) - 20} more")
        print(f"  ⏱️  Total time: {total_elapsed:.1f}s")
        print(f"{'='*80}\n")
    
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
        # Handle both formats: direct dict or wrapped in 'mapping' key
        if 'mapping' in cmc_data:
            cmc_mapping = cmc_data['mapping']
        else:
            cmc_mapping = cmc_data
    
    blacklist = set()
    if BLACKLIST_FILE.exists():
        with BLACKLIST_FILE.open('r') as f:
            blacklist_data = json.load(f)
            # Handle both formats: array or object with "blacklist" key
            if isinstance(blacklist_data, list):
                blacklist = set(blacklist_data)
            elif isinstance(blacklist_data, dict) and 'blacklist' in blacklist_data:
                blacklist = set(blacklist_data['blacklist'])
            else:
                blacklist = set()
    
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
    
    # Step 3: Prepare updates
    print(f"\n📝 Preparing updates for {len(all_symbols)} symbols...")
    
    update_meta = args.update_metadata
    update_static = args.update_static_fields or args.update_funding_cycle or args.update_metadata
    
    updates_to_process = []
    creates_to_process = []
    skipped_symbols = []
    
    # Prepare all updates/creates first
    for symbol in all_symbols:
        spot_data, perp_data = trading_data.get(symbol, (None, None))
        
        if not spot_data and not perp_data:
            skipped_symbols.append(symbol)
            print(f"  ⚠️  {symbol}: 跳过 - 没有交易数据")
            continue
        
        page = pages_by_symbol.get(symbol)
        
        if not page:
            # Prepare creation
            cmc_data = cmc_mapping.get(symbol)
            if not cmc_data:
                skipped_symbols.append(symbol)
                print(f"  ⚠️  {symbol}: 跳过 - 没有 CMC mapping")
                continue
            
            print(f"  ✅ {symbol}: 准备创建新页面")
            creates_to_process.append({
                'symbol': symbol,
                'spot_data': spot_data,
                'perp_data': perp_data,
                'cmc_data': cmc_data
            })
        else:
            # Prepare update
            cmc_data = cmc_mapping.get(symbol)
            updates_to_process.append({
                'symbol': symbol,
                'page': page,
                'spot_data': spot_data,
                'perp_data': perp_data,
                'cmc_data': cmc_data
            })
    
    print(f"  ✅ {len(updates_to_process)} pages to update")
    print(f"  ✅ {len(creates_to_process)} pages to create")
    print(f"  ⚠️  {len(skipped_symbols)} symbols skipped")
    
    # Step 4: Process updates in parallel
    def process_update(update_info):
        """Worker function to update a single page"""
        try:
            symbol = update_info['symbol']
            page = update_info['page']
            spot_data = update_info['spot_data']
            perp_data = update_info['perp_data']
            cmc_data = update_info['cmc_data']
            
            cmc_full_data = None
            if update_meta and cmc_data and cmc_data.get('cmc_id') and cmc_client:
                try:
                    cmc_full_data = cmc_client.get_token_data(cmc_data['cmc_id'])
                except Exception:
                    pass
            
            properties, _ = build_trading_properties(
                symbol, spot_data, perp_data, cmc_data, cmc_full_data,
                existing_page=page, is_new_page=False,
                update_metadata=update_meta, update_static_fields=update_static
            )
            
            notion.update_page(page['id'], properties)
            
            # Format display info
            spot_price = spot_data.get('spot_price') if spot_data else None
            perp_price = perp_data.get('perp_price') if perp_data else None
            oi = perp_data.get('open_interest_usd') if perp_data else None
            funding = perp_data.get('funding_rate') if perp_data else None
            
            info_parts = []
            if spot_price:
                info_parts.append(f"S:${spot_price:.4f}")
            if perp_price:
                info_parts.append(f"P:${perp_price:.4f}")
            if oi:
                info_parts.append(f"OI:${oi/1e9:.2f}B" if oi >= 1e9 else f"OI:${oi/1e6:.0f}M")
            if funding is not None:
                info_parts.append(f"FR:{funding*100:.4f}%")
            
            return ('success', symbol, ' '.join(info_parts))
            
        except Exception as e:
            return ('error', symbol, str(e)[:50])
    
    def process_create(create_info):
        """Worker function to create a single page"""
        try:
            symbol = create_info['symbol']
            spot_data = create_info['spot_data']
            perp_data = create_info['perp_data']
            cmc_data = create_info['cmc_data']
            
            cmc_full_data = None
            if cmc_client and cmc_data.get('cmc_id'):
                try:
                    cmc_full_data = cmc_client.get_token_data(cmc_data['cmc_id'])
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
            
            notion.create_page(properties, icon_url, symbol=symbol)
            
            return ('created', symbol, '')
            
        except Exception as e:
            return ('error', symbol, str(e)[:50])
    
    # Process updates in parallel
    print(f"\n🚀 Updating {len(updates_to_process)} pages in parallel (10 workers)...")
    update_start = time.time()
    
    success_count = 0
    created_count = 0
    error_count = 0
    failed_updates = []  # 收集失败的更新
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_update, update_info) for update_info in updates_to_process]
        
        completed = 0
        for future in as_completed(futures):
            status, symbol, info = future.result()
            completed += 1
            
            if status == 'success':
                success_count += 1
                if completed % 50 == 0 or completed == len(updates_to_process):
                    print(f"  [{completed}/{len(updates_to_process)}] {symbol} ✅ {info}")
            else:
                error_count += 1
                # 保存失败的更新信息，用于重试
                for update_info in updates_to_process:
                    if update_info['symbol'] == symbol:
                        failed_updates.append(update_info)
                        break
                print(f"  [{completed}/{len(updates_to_process)}] {symbol} ❌ {info}")
    
    update_elapsed = time.time() - update_start
    print(f"✅ Updated {success_count} pages in {update_elapsed:.1f}s ({success_count/update_elapsed:.2f} pages/s)")
    
    # 重试失败的更新
    max_retries = 3
    for retry_num in range(1, max_retries + 1):
        if not failed_updates:
            break
            
        print(f"\n🔄 Retry {retry_num}/{max_retries} for {len(failed_updates)} failed updates...")
        retry_start = time.time()
        
        retry_failed = []
        with ThreadPoolExecutor(max_workers=5) as executor:  # 减少并发数，避免再次失败
            futures = [executor.submit(process_update, update_info) for update_info in failed_updates]
            
            for future in as_completed(futures):
                status, symbol, info = future.result()
                
                if status == 'success':
                    success_count += 1
                    error_count -= 1
                    print(f"    ✅ {symbol} - retry successful")
                else:
                    # 保存仍然失败的更新
                    for update_info in failed_updates:
                        if update_info['symbol'] == symbol:
                            retry_failed.append(update_info)
                            break
                    print(f"    ⚠️  {symbol} - retry failed: {info[:40]}")
        
        retry_elapsed = time.time() - retry_start
        recovered = len(failed_updates) - len(retry_failed)
        
        if recovered > 0:
            print(f"  ✅ Recovered {recovered} pages in {retry_elapsed:.1f}s")
        
        failed_updates = retry_failed
        
        if not failed_updates:
            break
    
    # Process creates in parallel  
    if creates_to_process:
        print(f"\n🚀 Creating {len(creates_to_process)} pages in parallel (10 workers)...")
        create_start = time.time()
        failed_creates = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_create, create_info) for create_info in creates_to_process]
            
            completed = 0
            for future in as_completed(futures):
                status, symbol, info = future.result()
                completed += 1
                
                if status == 'created':
                    created_count += 1
                    success_count += 1
                    if completed % 50 == 0 or completed == len(creates_to_process):
                        print(f"  [{completed}/{len(creates_to_process)}] {symbol} ✅ Created")
                else:
                    error_count += 1
                    # 保存失败的创建信息
                    for create_info in creates_to_process:
                        if create_info['symbol'] == symbol:
                            failed_creates.append(create_info)
                            break
                    print(f"  [{completed}/{len(creates_to_process)}] {symbol} ❌ {info}")
        
        create_elapsed = time.time() - create_start
        print(f"✅ Created {created_count} pages in {create_elapsed:.1f}s ({created_count/create_elapsed:.2f} pages/s)")
        
        # 重试失败的创建
        for retry_num in range(1, max_retries + 1):
            if not failed_creates:
                break
                
            print(f"\n🔄 Retry {retry_num}/{max_retries} for {len(failed_creates)} failed creates...")
            retry_start = time.time()
            
            retry_failed = []
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(process_create, create_info) for create_info in failed_creates]
                
                for future in as_completed(futures):
                    status, symbol, info = future.result()
                    
                    if status == 'created':
                        created_count += 1
                        success_count += 1
                        error_count -= 1
                        print(f"    ✅ {symbol} - retry created successfully")
                    else:
                        for create_info in failed_creates:
                            if create_info['symbol'] == symbol:
                                retry_failed.append(create_info)
                                break
                        print(f"    ⚠️  {symbol} - retry failed: {info[:40]}")
            
            retry_elapsed = time.time() - retry_start
            recovered = len(failed_creates) - len(retry_failed)
            
            if recovered > 0:
                print(f"  ✅ Recovered {recovered} pages in {retry_elapsed:.1f}s")
            
            failed_creates = retry_failed
            
            if not failed_creates:
                break
    
    skipped_count = len(skipped_symbols)
    
    # Summary
    elapsed = time.time() - start_time
    print(f"\n{'='*80}")
    print(f"✅ Update Complete in {elapsed/60:.1f} minutes")
    print(f"{'='*80}")
    print(f"Success: {success_count} (Updated: {success_count - created_count}, Created: {created_count})")
    print(f"Skipped: {skipped_count}")
    if error_count > 0:
        print(f"Errors: {error_count}")
        if failed_updates:
            print(f"  Still failed updates: {', '.join([u['symbol'] for u in failed_updates])}")
        if 'failed_creates' in locals() and failed_creates:
            print(f"  Still failed creates: {', '.join([c['symbol'] for c in failed_creates])}")
    print(f"Rate: {success_count/elapsed:.2f} symbols/second")
    print(f"{'='*80}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
