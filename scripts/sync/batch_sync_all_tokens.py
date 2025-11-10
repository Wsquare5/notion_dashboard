#!/usr/bin/env python3
"""Batch sync all Binance tokens to Notion

This script fetches all available USDT trading pairs from Binance
and syncs them to Notion in batches to avoid API rate limits.

Usage:
    python3 scripts/batch_sync_all_tokens.py --batch-size 10 --start-from 0
"""

import requests
import time
import argparse
import sys
from pathlib import Path
from typing import List, Set

# Import our sync functions
sys.path.append(str(Path(__file__).resolve().parent))
from binance_to_notion import NotionConfig, NotionClient, sync_token_to_notion
from enhanced_data_fetcher import fetch_enhanced_data

def get_all_binance_usdt_pairs() -> dict:
    """Get all USDT trading pairs from Binance spot and futures markets."""
    print("🔍 Fetching all Binance USDT trading pairs...")
    
    # Get spot pairs
    spot_url = 'https://api.binance.com/api/v3/exchangeInfo'
    spot_response = requests.get(spot_url, timeout=10)
    spot_data = spot_response.json()
    
    spot_symbols = set()
    for symbol_info in spot_data['symbols']:
        if symbol_info['symbol'].endswith('USDT') and symbol_info['status'] == 'TRADING':
            base = symbol_info['baseAsset']
            spot_symbols.add(base)
    
    # Get futures pairs
    perp_url = 'https://fapi.binance.com/fapi/v1/exchangeInfo'
    perp_response = requests.get(perp_url, timeout=10)
    perp_data = perp_response.json()
    
    perp_symbols = set()
    for symbol_info in perp_data['symbols']:
        if symbol_info['symbol'].endswith('USDT') and symbol_info['status'] == 'TRADING':
            base = symbol_info['baseAsset']
            perp_symbols.add(base)
    
    # Categorize symbols
    both_markets = spot_symbols & perp_symbols
    spot_only = spot_symbols - perp_symbols
    perp_only = perp_symbols - spot_symbols
    
    print(f"✅ Spot USDT pairs: {len(spot_symbols)}")
    print(f"✅ Futures USDT pairs: {len(perp_symbols)}")
    print(f"🎯 Both markets: {len(both_markets)}")
    print(f"📊 Spot only: {len(spot_only)}")
    print(f"📈 Futures only: {len(perp_only)}")
    
    return {
        'both_markets': sorted(list(both_markets)),
        'spot_only': sorted(list(spot_only)),
        'perp_only': sorted(list(perp_only))
    }

def get_priority_symbols() -> List[str]:
    """Get high-priority symbols to sync first (major cryptocurrencies)."""
    major_cryptos = [
        'BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'AVAX', 'DOT', 'MATIC', 'LINK',
        'UNI', 'LTC', 'BCH', 'NEAR', 'ATOM', 'FTM', 'ALGO', 'VET', 'ICP', 'HBAR',
        'ETC', 'FIL', 'THETA', 'XLM', 'TRX', 'AAVE', 'MKR', 'SNX', 'COMP', 'YFI'
    ]
    return major_cryptos

def sync_batch(symbols: List[str], client: NotionClient, batch_num: int) -> dict:
    """Sync a batch of symbols to Notion."""
    print(f"\n📦 Processing Batch {batch_num}: {len(symbols)} symbols")
    print(f"Symbols: {', '.join(symbols)}")
    
    # Fetch data for the batch
    print("📊 Fetching data...")
    try:
        token_data_list = fetch_enhanced_data(symbols)
    except Exception as e:
        print(f"❌ Error fetching data for batch {batch_num}: {e}")
        return {"success": 0, "failed": len(symbols), "errors": [str(e)]}
    
    if not token_data_list:
        print(f"❌ No data fetched for batch {batch_num}")
        return {"success": 0, "failed": len(symbols), "errors": ["No data fetched"]}
    
    # Sync each token
    print("📤 Syncing to Notion...")
    results = []
    success_count = 0
    failed_count = 0
    errors = []
    
    for token_data in token_data_list:
        try:
            result = sync_token_to_notion(client, token_data)
            results.append(result)
            
            if result["success"]:
                success_count += 1
                print(f"  ✅ {token_data.base}: {result['details'].get('action', 'synced')}")
            else:
                failed_count += 1
                error_msg = result.get('error', 'Unknown error')
                errors.append(f"{token_data.base}: {error_msg}")
                print(f"  ❌ {token_data.base}: {error_msg}")
            
            # Rate limiting - Notion allows 3 requests per second
            time.sleep(0.4)
            
        except Exception as e:
            failed_count += 1
            error_msg = str(e)
            errors.append(f"{token_data.base}: {error_msg}")
            print(f"  ❌ {token_data.base}: {error_msg}")
    
    return {
        "success": success_count,
        "failed": failed_count,
        "errors": errors
    }

def main():
    parser = argparse.ArgumentParser(description="Batch sync all Binance tokens to Notion")
    parser.add_argument("--config", "-c",
                       default=str(Path(__file__).resolve().parents[1] / "config.json"),
                       help="Configuration file path")
    parser.add_argument("--batch-size", "-b", type=int, default=10,
                       help="Number of symbols to process in each batch")
    parser.add_argument("--start-from", "-s", type=int, default=0,
                       help="Start from which symbol index (for resuming)")
    parser.add_argument("--max-batches", "-m", type=int, default=None,
                       help="Maximum number of batches to process")
    parser.add_argument("--priority-only", "-p", action="store_true",
                       help="Only sync priority symbols (major cryptocurrencies)")
    parser.add_argument("--category", choices=['both', 'spot', 'perp', 'all'], default='both',
                       help="Which category of symbols to sync")
    
    args = parser.parse_args()
    
    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        return
    
    try:
        config = NotionConfig.from_file(config_path)
        client = NotionClient(config)
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return
    
    # Get all symbols
    all_pairs = get_all_binance_usdt_pairs()
    
    if args.priority_only:
        print("\n🎯 Using priority symbols only...")
        priority_symbols = get_priority_symbols()
        # Filter priority symbols to only include those available on Binance
        if args.category == 'both':
            available_symbols = [s for s in priority_symbols if s in all_pairs['both_markets']]
        elif args.category == 'spot':
            available_symbols = [s for s in priority_symbols if s in all_pairs['spot_only'] + all_pairs['both_markets']]
        elif args.category == 'perp':
            available_symbols = [s for s in priority_symbols if s in all_pairs['perp_only'] + all_pairs['both_markets']]
        else:  # all
            all_available = set(all_pairs['both_markets'] + all_pairs['spot_only'] + all_pairs['perp_only'])
            available_symbols = [s for s in priority_symbols if s in all_available]
        symbols_to_sync = available_symbols
    else:
        if args.category == 'both':
            symbols_to_sync = all_pairs['both_markets']
        elif args.category == 'spot':
            symbols_to_sync = all_pairs['spot_only'] + all_pairs['both_markets']
        elif args.category == 'perp':
            symbols_to_sync = all_pairs['perp_only'] + all_pairs['both_markets']
        else:  # all
            symbols_to_sync = all_pairs['both_markets'] + all_pairs['spot_only'] + all_pairs['perp_only']
    
    print(f"\n🚀 Starting batch sync...")
    print(f"📊 Total symbols to sync: {len(symbols_to_sync)}")
    print(f"📦 Batch size: {args.batch_size}")
    print(f"🏁 Starting from index: {args.start_from}")
    
    # Process in batches
    symbols_to_sync = symbols_to_sync[args.start_from:]
    total_success = 0
    total_failed = 0
    all_errors = []
    
    batch_num = 1
    max_batches = args.max_batches or (len(symbols_to_sync) // args.batch_size + 1)
    
    for i in range(0, len(symbols_to_sync), args.batch_size):
        if batch_num > max_batches:
            break
            
        batch_symbols = symbols_to_sync[i:i + args.batch_size]
        
        try:
            batch_result = sync_batch(batch_symbols, client, batch_num)
            total_success += batch_result["success"]
            total_failed += batch_result["failed"]
            all_errors.extend(batch_result["errors"])
            
            print(f"\n📊 Batch {batch_num} Summary: ✅ {batch_result['success']} success, ❌ {batch_result['failed']} failed")
            
            # Longer pause between batches to avoid CoinGecko rate limiting (30 calls/min)
            if i + args.batch_size < len(symbols_to_sync) and batch_num < max_batches:
                print("⏱️ Waiting 30 seconds before next batch (CoinGecko rate limit)...")
                time.sleep(30)
            
        except Exception as e:
            print(f"💥 Batch {batch_num} failed completely: {e}")
            total_failed += len(batch_symbols)
            all_errors.append(f"Batch {batch_num}: {e}")
        
        batch_num += 1
    
    # Final summary
    print("\n" + "="*60)
    print("🎉 BATCH SYNC COMPLETE")
    print("="*60)
    print(f"✅ Total successful: {total_success}")
    print(f"❌ Total failed: {total_failed}")
    print(f"📊 Success rate: {total_success/(total_success+total_failed)*100:.1f}%" if (total_success+total_failed) > 0 else "0%")
    
    if all_errors:
        print(f"\n💥 Errors encountered ({len(all_errors)}):")
        for error in all_errors[:10]:  # Show first 10 errors
            print(f"  • {error}")
        if len(all_errors) > 10:
            print(f"  ... and {len(all_errors)-10} more errors")
    
    print(f"\n🕒 Sync completed at {time.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()