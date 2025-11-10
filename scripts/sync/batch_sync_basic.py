#!/usr/bin/env python3
"""Batch sync without CoinGecko data to avoid rate limits

This script syncs basic trading data (prices, volumes, OI, funding rates) 
without CoinGecko supply/logo data to avoid rate limiting issues.
"""

import argparse
import sys
import time
from pathlib import Path

# Import our sync functions
sys.path.append(str(Path(__file__).resolve().parent))
from batch_sync_all_tokens import get_all_binance_usdt_pairs, get_priority_symbols
from binance_to_notion import NotionConfig, NotionClient, sync_token_to_notion
from enhanced_data_fetcher import TokenData, fetch_spot_data, fetch_perp_data

def fetch_basic_data(symbols: list) -> list:
    """Fetch basic trading data without CoinGecko data."""
    results = []
    
    for symbol in symbols:
        print(f"\n=== Fetching basic data for {symbol} ===")
        token_data = TokenData(base=symbol)
        
        # Fetch spot data
        spot_data = fetch_spot_data(symbol)
        if spot_data:
            token_data.spot_price = spot_data.get("spot_price")
            token_data.spot_volume_24h = spot_data.get("spot_volume_24h")
            if token_data.spot_price and token_data.spot_volume_24h:
                print(f"Spot: ${token_data.spot_price:.6f}, Vol: ${token_data.spot_volume_24h:,.0f}")
        
        # Fetch perp data
        perp_data = fetch_perp_data(symbol)
        if perp_data:
            token_data.perp_price = perp_data.get("perp_price")
            token_data.perp_volume_24h = perp_data.get("perp_volume_24h")
            token_data.open_interest = perp_data.get("open_interest")
            token_data.funding_rate = perp_data.get("funding_rate")
            token_data.index_price = perp_data.get("index_price")
            token_data.mark_price = perp_data.get("mark_price")
            token_data.basis = perp_data.get("basis")
            token_data.index_composition = perp_data.get("index_composition")
            token_data.index_composition_summary = perp_data.get("index_composition_summary")
            
            # Convert open interest to USD
            try:
                if token_data.open_interest and token_data.perp_price:
                    token_data.open_interest_usd = float(token_data.open_interest) * float(token_data.perp_price)
            except Exception:
                token_data.open_interest_usd = None
            
            if token_data.perp_price and token_data.perp_volume_24h:
                print(f"Perp: ${token_data.perp_price:.6f}, Vol: ${token_data.perp_volume_24h:,.0f}")
            if token_data.open_interest_usd:
                print(f"OI (USD): ${token_data.open_interest_usd:,.0f}")
            if token_data.funding_rate is not None:
                print(f"Funding Rate: {token_data.funding_rate:.6f} ({token_data.funding_rate*100:.4f}%)")
            if token_data.basis is not None:
                print(f"Basis: {token_data.basis:.6f} ({token_data.basis*100:.4f}%)")
            if token_data.index_composition_summary:
                print(f"Index Composition: {token_data.index_composition_summary}")
        
        results.append(token_data)
        
        # Rate limiting for Binance APIs
        time.sleep(0.5)
    
    return results

def sync_batch_basic(symbols: list, client: NotionClient, batch_num: int) -> dict:
    """Sync a batch of symbols to Notion with basic data only."""
    print(f"\n📦 Processing Batch {batch_num}: {len(symbols)} symbols")
    print(f"Symbols: {', '.join(symbols)}")
    
    # Fetch basic data for the batch
    print("📊 Fetching basic trading data...")
    try:
        token_data_list = fetch_basic_data(symbols)
    except Exception as e:
        print(f"❌ Error fetching data for batch {batch_num}: {e}")
        return {"success": 0, "failed": len(symbols), "errors": [str(e)]}
    
    if not token_data_list:
        print(f"❌ No data fetched for batch {batch_num}")
        return {"success": 0, "failed": len(symbols), "errors": ["No data fetched"]}
    
    # Sync each token
    print("📤 Syncing to Notion...")
    success_count = 0
    failed_count = 0
    errors = []
    
    for token_data in token_data_list:
        try:
            result = sync_token_to_notion(client, token_data)
            
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
    parser = argparse.ArgumentParser(description="Batch sync Binance tokens to Notion (basic data only)")
    parser.add_argument("--config", "-c",
                       default=str(Path(__file__).resolve().parents[1] / "config.json"),
                       help="Configuration file path")
    parser.add_argument("--batch-size", "-b", type=int, default=10,
                       help="Number of symbols to process in each batch")
    parser.add_argument("--start-from", "-s", type=int, default=0,
                       help="Start from which symbol index")
    parser.add_argument("--max-batches", "-m", type=int, default=None,
                       help="Maximum number of batches to process")
    parser.add_argument("--priority-only", "-p", action="store_true",
                       help="Only sync priority symbols")
    
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
    
    # Get symbols to sync
    if args.priority_only:
        print("\n🎯 Using priority symbols only...")
        priority_symbols = get_priority_symbols()
        all_pairs = get_all_binance_usdt_pairs()
        symbols_to_sync = [s for s in priority_symbols if s in all_pairs['both_markets']]
    else:
        all_pairs = get_all_binance_usdt_pairs()
        symbols_to_sync = all_pairs['both_markets']
    
    print(f"\n🚀 Starting basic data sync...")
    print(f"📊 Total symbols to sync: {len(symbols_to_sync)}")
    print(f"📦 Batch size: {args.batch_size}")
    print(f"🏁 Starting from index: {args.start_from}")
    print("⚠️ Note: Skipping CoinGecko data (supply, logo, ATH/ATL) to avoid rate limits")
    
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
            batch_result = sync_batch_basic(batch_symbols, client, batch_num)
            total_success += batch_result["success"]
            total_failed += batch_result["failed"]
            all_errors.extend(batch_result["errors"])
            
            print(f"\n📊 Batch {batch_num} Summary: ✅ {batch_result['success']} success, ❌ {batch_result['failed']} failed")
            
            # Short pause between batches
            if i + args.batch_size < len(symbols_to_sync) and batch_num < max_batches:
                print("⏱️ Waiting 5 seconds before next batch...")
                time.sleep(5)
            
        except Exception as e:
            print(f"💥 Batch {batch_num} failed completely: {e}")
            total_failed += len(batch_symbols)
            all_errors.append(f"Batch {batch_num}: {e}")
        
        batch_num += 1
    
    # Final summary
    print("\n" + "="*60)
    print("🎉 BASIC DATA SYNC COMPLETE")
    print("="*60)
    print(f"✅ Total successful: {total_success}")
    print(f"❌ Total failed: {total_failed}")
    print(f"📊 Success rate: {total_success/(total_success+total_failed)*100:.1f}%" if (total_success+total_failed) > 0 else "0%")
    
    if all_errors:
        print(f"\n💥 Errors encountered ({len(all_errors)}):")
        for error in all_errors[:10]:
            print(f"  • {error}")
        if len(all_errors) > 10:
            print(f"  ... and {len(all_errors)-10} more errors")
    
    print(f"\n🕒 Sync completed at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("💡 Tip: Run this again later with CoinGecko data when rate limits reset")

if __name__ == "__main__":
    main()