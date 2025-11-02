#!/usr/bin/env python3
"""Update only Binance trading data to Notion (no CoinGecko/CMC calls)

This script updates:
- Spot & Perp prices and 24h price changes
- 24h trading volumes
- Open Interest
- Funding rate & cycle
- Basis calculation

Does NOT update:
- Supply data (already from CMC)
- ATH/ATL data (from CoinGecko)
- Logo, website, genesis date (already from CMC)
"""

import requests
import json
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Configuration
ROOT = Path(__file__).resolve().parents[1]
NOTION_CONFIG_FILE = ROOT / 'config.json'
CMC_MAPPING_FILE = ROOT / 'binance_cmc_mapping.json'

class BinanceDataFetcher:
    """Fetches only Binance trading data"""
    
    @staticmethod
    def fetch_spot_data(symbol: str) -> Optional[Dict]:
        """Fetch spot market data"""
        try:
            url = "https://api.binance.com/api/v3/ticker/24hr"
            params = {"symbol": f"{symbol}USDT"}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                "spot_price": float(data["lastPrice"]),
                "spot_24h_change": float(data["priceChangePercent"]),
                "spot_volume_24h": float(data["quoteVolume"])
            }
        except Exception as e:
            print(f"  ⚠️  Spot data unavailable: {e}")
            return None
    
    @staticmethod
    def fetch_perp_data(symbol: str) -> Optional[Dict]:
        """Fetch perpetual futures data"""
        try:
            # Get price and 24h stats
            url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
            params = {"symbol": f"{symbol}USDT"}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            perp_price = float(data["lastPrice"])
            perp_data = {
                "perp_price": perp_price,
                "perp_24h_change": float(data["priceChangePercent"]),
                "perp_volume_24h": float(data["quoteVolume"])
            }
            
            # Get funding rate
            try:
                funding_url = "https://fapi.binance.com/fapi/v1/premiumIndex"
                funding_params = {"symbol": f"{symbol}USDT"}
                funding_response = requests.get(funding_url, params=funding_params, timeout=10)
                funding_response.raise_for_status()
                funding_data = funding_response.json()
                
                perp_data["funding_rate"] = float(funding_data["lastFundingRate"])
                perp_data["mark_price"] = float(funding_data["markPrice"])
                perp_data["index_price"] = float(funding_data["indexPrice"])
                
                # Calculate basis
                if perp_data["index_price"] > 0:
                    perp_data["basis"] = (perp_price - perp_data["index_price"]) / perp_data["index_price"]
            except Exception as e:
                print(f"  ⚠️  Funding rate unavailable: {e}")
            
            # Get open interest
            try:
                oi_url = "https://fapi.binance.com/fapi/v1/openInterest"
                oi_params = {"symbol": f"{symbol}USDT"}
                oi_response = requests.get(oi_url, params=oi_params, timeout=10)
                oi_response.raise_for_status()
                oi_data = oi_response.json()
                
                oi_tokens = float(oi_data["openInterest"])
                perp_data["open_interest"] = oi_tokens
                perp_data["open_interest_usd"] = oi_tokens * perp_price
            except Exception as e:
                print(f"  ⚠️  Open interest unavailable: {e}")
            
            # Detect funding cycle
            perp_data["funding_cycle"] = BinanceDataFetcher.detect_funding_cycle(symbol)
            
            return perp_data
            
        except Exception as e:
            print(f"  ⚠️  Perp data unavailable: {e}")
            return None
    
    @staticmethod
    def detect_funding_cycle(symbol: str) -> Optional[int]:
        """Detect funding rate cycle (4h or 8h)"""
        try:
            url = "https://fapi.binance.com/fapi/v1/fundingRate"
            params = {"symbol": f"{symbol}USDT", "limit": 2}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if len(data) >= 2:
                time_diff_ms = data[1]['fundingTime'] - data[0]['fundingTime']
                time_diff_hours = time_diff_ms / (1000 * 60 * 60)
                
                if 3.5 <= time_diff_hours <= 4.5:
                    return 4
                elif 7.5 <= time_diff_hours <= 8.5:
                    return 8
            
            return None
        except:
            return None


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


def build_trading_properties(symbol: str, spot_data: Dict, perp_data: Dict) -> Dict:
    """Build Notion properties for trading data only"""
    
    properties = {}
    
    # Spot market data
    if spot_data:
        if spot_data.get("spot_price") is not None:
            properties["Spot Price"] = {"number": spot_data["spot_price"]}
        
        if spot_data.get("spot_volume_24h") is not None:
            properties["Spot vol 24h"] = {"number": spot_data["spot_volume_24h"]}
    
    # Perp market data
    if perp_data:
        if perp_data.get("perp_price") is not None:
            properties["Perp Price"] = {"number": perp_data["perp_price"]}
        
        if perp_data.get("perp_volume_24h") is not None:
            properties["Perp vol 24h"] = {"number": perp_data["perp_volume_24h"]}
        
        if perp_data.get("open_interest_usd") is not None:
            properties["OI"] = {"number": perp_data["open_interest_usd"]}
        
        if perp_data.get("funding_rate") is not None:
            properties["Funding"] = {"number": perp_data["funding_rate"]}
        
        if perp_data.get("funding_cycle") is not None:
            properties["Funding Cycle"] = {"number": perp_data["funding_cycle"]}
        
        if perp_data.get("basis") is not None:
            properties["Basis"] = {"number": perp_data["basis"]}
    
    # Use perp 24h change for the single "Price change" field (prefer perp over spot)
    price_change = None
    if perp_data and perp_data.get("perp_24h_change") is not None:
        price_change = perp_data["perp_24h_change"]
    elif spot_data and spot_data.get("spot_24h_change") is not None:
        price_change = spot_data["spot_24h_change"]
    
    if price_change is not None:
        # Notion expects percentage as decimal (e.g., 5% = 0.05)
        properties["Price change"] = {"number": price_change / 100}
    
    return properties


def update_trading_data(symbols: List[str] = None, perp_only_flag: bool = False, perp_only_set: set = None):
    """Update Binance trading data to Notion"""
    
    print("🚀 Updating Binance trading data to Notion...\n")
    
    # Load configurations
    with NOTION_CONFIG_FILE.open('r') as f:
        notion_config = json.load(f)
    
    # Load CMC mapping to get all symbols
    with CMC_MAPPING_FILE.open('r', encoding='utf-8') as f:
        cmc_data = json.load(f)
        all_symbols = list(cmc_data['mapping'].keys())
    
    # Use provided symbols or all symbols
    if symbols:
        symbols_to_update = symbols
    elif perp_only_flag and perp_only_set:
        # If --perp-only flag is set, only update symbols in the perp-only set
        symbols_to_update = [s for s in all_symbols if s.upper() in perp_only_set]
        print(f"🔍 Filtering to perp-only tokens: {len(symbols_to_update)} out of {len(all_symbols)}\n")
    else:
        symbols_to_update = all_symbols
    
    print(f"📊 Will update {len(symbols_to_update)} symbols\n")
    
    # Initialize clients
    fetcher = BinanceDataFetcher()
    notion_client = NotionClient(
        notion_config['notion']['api_key'],
        notion_config['notion']['database_id']
    )
    
    # Update each symbol
    success_count = 0
    error_count = 0
    skipped_count = 0
    failed_symbols = []  # Track failed symbols for retry
    
    for i, symbol in enumerate(symbols_to_update, 1):
        try:
            print(f"[{i}/{len(symbols_to_update)}] {symbol}")
            
            # Check if page exists
            existing_page = notion_client.get_page_by_symbol(symbol)
            if not existing_page:
                print(f"  ⚠️  Page not found in Notion, skipping")
                skipped_count += 1
                continue
            
            # Fetch Binance data
            # Skip spot fetch for known perp-only tokens or when user requested perp-only mode
            is_perp_only = False
            if perp_only_flag:
                is_perp_only = True
            elif perp_only_set is not None:
                try:
                    if symbol.upper() in perp_only_set:
                        is_perp_only = True
                except Exception:
                    # defensive: if perp_only_set contains non-string items
                    pass

            if is_perp_only:
                print(f"  ℹ️  Skipping spot fetch for perp-only symbol: {symbol}")
                spot_data = None
            else:
                spot_data = fetcher.fetch_spot_data(symbol)

            perp_data = fetcher.fetch_perp_data(symbol)
            
            if not spot_data and not perp_data:
                print(f"  ⚠️  No data available, skipping")
                skipped_count += 1
                continue
            
            # Build properties
            properties = build_trading_properties(symbol, spot_data, perp_data)
            
            if not properties:
                print(f"  ⚠️  No properties to update, skipping")
                skipped_count += 1
                continue
            
            # Update Notion
            page_id = existing_page['id']
            notion_client.update_page(page_id, properties)
            
            # Show what was updated
            info_parts = []
            if spot_data and spot_data.get("spot_price"):
                info_parts.append(f"Spot: ${spot_data['spot_price']:.4f}")
            if perp_data and perp_data.get("perp_price"):
                info_parts.append(f"Perp: ${perp_data['perp_price']:.4f}")
            if perp_data and perp_data.get("funding_rate"):
                info_parts.append(f"FR: {perp_data['funding_rate']*100:.4f}%")
            
            info_str = " | ".join(info_parts) if info_parts else "updated"
            print(f"  ✅ {info_str}")
            
            success_count += 1
            
            # Rate limiting
            time.sleep(0.3)
            
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            error_count += 1
            failed_symbols.append(symbol)
    
    # Retry failed symbols
    if failed_symbols:
        print(f"\n🔄 Retrying {len(failed_symbols)} failed symbols...\n")
        retry_success = 0
        retry_failed = []
        
        for i, symbol in enumerate(failed_symbols, 1):
            try:
                print(f"[Retry {i}/{len(failed_symbols)}] {symbol}")
                
                # Check if page exists
                existing_page = notion_client.get_page_by_symbol(symbol)
                if not existing_page:
                    print(f"  ⚠️  Page not found in Notion, skipping")
                    retry_failed.append(symbol)
                    continue
                
                # Fetch Binance data
                is_perp_only = False
                if perp_only_flag:
                    is_perp_only = True
                elif perp_only_set is not None:
                    try:
                        if symbol.upper() in perp_only_set:
                            is_perp_only = True
                    except Exception:
                        pass

                if is_perp_only:
                    print(f"  ℹ️  Skipping spot fetch for perp-only symbol: {symbol}")
                    spot_data = None
                else:
                    spot_data = fetcher.fetch_spot_data(symbol)

                perp_data = fetcher.fetch_perp_data(symbol)
                
                if not spot_data and not perp_data:
                    print(f"  ⚠️  No data available, skipping")
                    retry_failed.append(symbol)
                    continue
                
                # Build properties
                properties = build_trading_properties(symbol, spot_data, perp_data)
                
                if not properties:
                    print(f"  ⚠️  No properties to update, skipping")
                    retry_failed.append(symbol)
                    continue
                
                # Update Notion
                page_id = existing_page['id']
                notion_client.update_page(page_id, properties)
                
                # Show what was updated
                info_parts = []
                if spot_data and spot_data.get("spot_price"):
                    info_parts.append(f"Spot: ${spot_data['spot_price']:.4f}")
                if perp_data and perp_data.get("perp_price"):
                    info_parts.append(f"Perp: ${perp_data['perp_price']:.4f}")
                if perp_data and perp_data.get("funding_rate"):
                    info_parts.append(f"FR: {perp_data['funding_rate']*100:.4f}%")
                
                info_str = " | ".join(info_parts) if info_parts else "updated"
                print(f"  ✅ {info_str}")
                
                retry_success += 1
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  ❌ Failed again: {e}")
                retry_failed.append(symbol)
        
        # Update final counts
        success_count += retry_success
        error_count = len(retry_failed)
        
        if retry_success > 0:
            print(f"\n✅ Retry successful: {retry_success} symbols")
        if retry_failed:
            print(f"❌ Still failed after retry: {', '.join(retry_failed)}")
    
    print(f"\n✨ Update complete!")
    print(f"  Success: {success_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Errors: {error_count}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Update Binance trading data to Notion')
    parser.add_argument('--symbols', type=str, help='Comma-separated list of symbols')
    parser.add_argument('--perp-only', action='store_true', help='Skip spot API calls for symbols known to be perp-only')
    parser.add_argument('--limit', type=int, help='Limit number of symbols to update')
    
    args = parser.parse_args()
    
    symbols = None
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
    
    if args.limit and not symbols:
        # Load symbols from mapping and apply limit
        with CMC_MAPPING_FILE.open('r', encoding='utf-8') as f:
            cmc_data = json.load(f)
            symbols = list(cmc_data['mapping'].keys())[:args.limit]

    # Build perp-only set from generated data file if available
    perp_only_set = None
    perp_only_json = ROOT / 'data' / 'aggregated_usdt_perp_only.json'
    if perp_only_json.exists():
        try:
            with perp_only_json.open('r', encoding='utf-8') as f:
                perp_list = json.load(f)
                perp_only_set = set()
                for r in perp_list:
                    # candidate keys: base, symbol, baseAsset
                    for k in ('base', 'symbol', 'baseAsset'):
                        v = r.get(k)
                        if v:
                            perp_only_set.add(str(v).strip().upper())
        except Exception:
            perp_only_set = None

    update_trading_data(symbols=symbols, perp_only_flag=args.perp_only, perp_only_set=perp_only_set)


if __name__ == '__main__':
    main()
