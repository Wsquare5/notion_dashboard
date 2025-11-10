#!/usr/bin/env python3
"""Binance to Notion Integration Script

This script integrates enhanced Binance trading data with Notion databases.
Supports the dual-table architecture:
1. Real-time Trading Data - Frequently updated trading metrics
2. Token Basic Info - Static token information

Usage:
    python3 scripts/binance_to_notion.py --config config.json --symbols BROCCOLI714,BROCCOLIF3B
"""

import requests
import json
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Import our enhanced data fetcher
import sys
sys.path.append(str(Path(__file__).resolve().parent))
from enhanced_data_fetcher import fetch_enhanced_data, TokenData

# Configuration
ROOT = Path(__file__).resolve().parents[1]

@dataclass
class NotionConfig:
    """Notion API configuration"""
    api_key: str
    database_id: str  # Single database with multiple views
    
    @classmethod
    def from_file(cls, config_path: Path) -> 'NotionConfig':
        """Load configuration from JSON file"""
        with config_path.open('r') as f:
            config = json.load(f)
        return cls(
            api_key=config['notion']['api_key'],
            database_id=config['notion']['database_id']
        )


class NotionClient:
    """Notion API client for database operations"""
    
    def __init__(self, config: NotionConfig):
        self.config = config
        self.headers = {
            'Authorization': f'Bearer {config.api_key}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
        self.base_url = 'https://api.notion.com/v1'
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make API request to Notion"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, headers=self.headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Notion API error: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            raise
    
    def query_database(self, database_id: str, filter_data: Dict = None) -> List[Dict]:
        """Query database for existing records"""
        endpoint = f"/databases/{database_id}/query"
        data = {}
        if filter_data:
            data['filter'] = filter_data
            
        response = self._request('POST', endpoint, data)
        return response.get('results', [])
    
    def find_page_by_symbol(self, database_id: str, symbol: str) -> Optional[Dict]:
        """Find existing page by symbol (using Symbol field)"""
        filter_data = {
            "property": "Symbol",
            "title": {
                "equals": symbol
            }
        }
        
        results = self.query_database(database_id, filter_data)
        return results[0] if results else None
    
    def create_page(self, database_id: str, properties: Dict, icon_url: str = None) -> Dict:
        """Create new page in database"""
        endpoint = "/pages"
        data = {
            "parent": {"database_id": database_id},
            "properties": properties
        }
        
        # Add icon if provided
        if icon_url:
            data["icon"] = {
                "external": {"url": icon_url}
            }
        
        return self._request('POST', endpoint, data)
    
    def update_page(self, page_id: str, properties: Dict, icon_url: str = None) -> Dict:
        """Update existing page"""
        endpoint = f"/pages/{page_id}"
        data = {"properties": properties}
        
        # Add icon if provided
        if icon_url:
            data["icon"] = {
                "external": {"url": icon_url}
            }
        
        return self._request('PATCH', endpoint, data)

def format_complete_properties(token_data: TokenData) -> Dict:
    """Format complete token data for single database with all fields"""
    now = datetime.now(timezone.utc).isoformat()
    
    properties = {
        # Basic identification - 使用数据库中的实际字段名
        "Symbol": {
            "title": [{"text": {"content": token_data.base}}]
        }
    }
    
    # Price fields - 使用实际字段名
    if token_data.spot_price:
        properties["Spot Price"] = {"number": token_data.spot_price}
    if token_data.perp_price:
        properties["Perp Price"] = {"number": token_data.perp_price}
    if hasattr(token_data, 'spot_24h_change') and token_data.spot_24h_change is not None:
        properties["Spot Price change"] = {"number": token_data.spot_24h_change / 100}  # 除以100因为Notion字段设置为percent格式
    if hasattr(token_data, 'perp_24h_change') and token_data.perp_24h_change is not None:
        properties["Perp Price change"] = {"number": token_data.perp_24h_change / 100}  # 除以100因为Notion字段设置为percent格式
    if token_data.basis is not None:
        properties["Basis"] = {"number": token_data.basis}
    
    # Trading data fields - 使用实际字段名
    if token_data.spot_volume_24h:
        properties["Spot vol 24h"] = {"number": token_data.spot_volume_24h}
    if token_data.perp_volume_24h:
        properties["Perp vol 24h"] = {"number": token_data.perp_volume_24h}
    # Open Interest: convert to USD value if available
    if getattr(token_data, 'open_interest_usd', None) is not None:
        properties["OI"] = {"number": token_data.open_interest_usd}
    elif token_data.open_interest:
        # fallback to raw open_interest if USD conversion not available
        properties["OI"] = {"number": token_data.open_interest}
    if token_data.funding_rate is not None:
        properties["Funding"] = {"number": token_data.funding_rate}
    if hasattr(token_data, 'funding_cycle') and token_data.funding_cycle is not None:
        properties["Funding Cycle"] = {"number": token_data.funding_cycle}
    
    # Index composition fields - 使用实际字段名
    if token_data.index_composition_summary:
        properties["Index Composition"] = {
            "rich_text": [{"text": {"content": token_data.index_composition_summary}}]
        }
    
    # Supply and market cap fields - 使用实际字段名
    if token_data.circulating_supply:
        properties["Circulating Supply"] = {"number": token_data.circulating_supply}
    if token_data.total_supply:
        properties["Total Supply"] = {"number": token_data.total_supply}
    if token_data.max_supply:
        properties["Max Supply"] = {"number": token_data.max_supply}
    if token_data.market_cap_calc:
        properties["MC"] = {"number": token_data.market_cap_calc}
    if token_data.fdv_calc:
        properties["FDV"] = {"number": token_data.fdv_calc}
    
    # ATH/ATL fields - 使用实际字段名
    if token_data.ath_price:
        properties["ATH Price"] = {"number": token_data.ath_price}
    if token_data.ath_date:
        try:
            ath_date = datetime.fromisoformat(token_data.ath_date.replace('Z', '+00:00'))
            properties["ATH Date"] = {"date": {"start": ath_date.strftime('%Y-%m-%d')}}
        except:
            pass
    if token_data.atl_price:
        properties["ATL Price"] = {"number": token_data.atl_price}
    if token_data.atl_date:
        try:
            atl_date = datetime.fromisoformat(token_data.atl_date.replace('Z', '+00:00'))
            properties["ATL Date"] = {"date": {"start": atl_date.strftime('%Y-%m-%d')}}
        except:
            pass
    if token_data.ath_market_cap:
        properties["ATH MC"] = {"number": token_data.ath_market_cap}
    if token_data.atl_market_cap:
        properties["ATL MC"] = {"number": token_data.atl_market_cap}
    
    # CoinGecko ID
    if token_data.coingecko_id:
        properties["CoinGecko ID"] = {
            "rich_text": [{"text": {"content": token_data.coingecko_id}}]
        }
    
    # Genesis Date
    if token_data.genesis_date:
        try:
            genesis_date = datetime.fromisoformat(token_data.genesis_date.replace('Z', '+00:00'))
            properties["Genesis Date"] = {"date": {"start": genesis_date.strftime('%Y-%m-%d')}}
        except:
            pass
    
    # Binance Listing
    if token_data.binance_listing_date:
        properties["Binance Listing"] = {
            "rich_text": [{"text": {"content": token_data.binance_listing_date}}]
        }
    
    # Website URL (需要在Notion数据库中添加 URL 类型的 "Website" 字段)
    if token_data.website:
        properties["Website"] = {
            "url": token_data.website
        }
    
    return properties


def sync_token_to_notion(client: NotionClient, token_data: TokenData) -> Dict:
    """Sync single token data to single Notion database"""
    result = {"symbol": token_data.base, "success": False, "details": {}}
    
    try:
        print(f"  Syncing {token_data.base}...")
        
        # Format properties for single database structure
        properties = format_complete_properties(token_data)
        
        try:
            # Try to find existing page first
            existing_page = client.find_page_by_symbol(
                client.config.database_id,
                token_data.base
            )
            
            if existing_page:
                # Update existing page with icon
                client.update_page(existing_page['id'], properties, token_data.logo_url)
                result["details"]["action"] = "updated"
                print(f"    ✅ Updated existing page")
            else:
                # Create new page with icon
                client.create_page(client.config.database_id, properties, token_data.logo_url)
                result["details"]["action"] = "created"
                print(f"    ✅ Created new page")
                
        except Exception as query_error:
            print(f"    ⚠️ Query failed, attempting direct creation: {query_error}")
            # If query fails (common with multi-data-source DBs), create new page
            try:
                client.create_page(client.config.database_id, properties, token_data.logo_url)
                result["details"]["action"] = "created (query failed)"
                print(f"    ✅ Created new page after query failure")
            except Exception as create_error:
                print(f"    ❌ Create also failed: {create_error}")
                raise create_error
        
        result["success"] = True
        print(f"  ✅ Successfully synced {token_data.base}")
        
    except Exception as e:
        result["error"] = str(e)
        print(f"  ❌ Failed to sync {token_data.base}: {e}")
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Sync Binance data to Notion")
    parser.add_argument("--config", "-c",
                       default=str(ROOT / "config.json"),
                       help="Configuration file path")
    parser.add_argument("--symbols", "-s",
                       default="BROCCOLI714,BROCCOLIF3B",
                       help="Comma-separated list of symbols to sync")
    parser.add_argument("--update-basic-info", "-b",
                       action="store_true",
                       help="Update basic info (static data) as well")
    
    args = parser.parse_args()
    
    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        print("\n📝 Please create a config.json file with the following structure:")
        print("""
{
  "notion": {
    "api_key": "secret_your_notion_api_key_here",
    "database_id": "your_single_database_id_here"
  }
}
        """)
        return
    
    try:
        config = NotionConfig.from_file(config_path)
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return
    
    # Parse symbols
    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    print(f"🚀 Starting Notion sync for symbols: {symbols}")
    
    if args.update_basic_info:
        print("📋 Will update basic info (static data) as well")
    else:
        print("⚡ Will only update trading data (real-time data)")
    
    # Fetch enhanced data
    print("\n📊 Fetching data from Binance and CoinGecko...")
    token_data_list = fetch_enhanced_data(symbols)
    
    if not token_data_list:
        print("❌ No data fetched. Exiting.")
        return
    
    # Initialize Notion client
    print("\n🔗 Connecting to Notion...")
    client = NotionClient(config)
    
    # Sync each token
    print("\n📤 Syncing data to Notion...")
    results = []
    
    for token_data in token_data_list:
        print(f"\n📋 Processing {token_data.base}...")
        result = sync_token_to_notion(client, token_data)
        results.append(result)
        
        # Rate limiting - Notion allows 3 requests per second
        time.sleep(0.35)
    
    # Summary
    print("\n" + "="*50)
    print("📊 SYNC SUMMARY")
    print("="*50)
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    
    if successful:
        print("\n🎉 Successfully synced:")
        for result in successful:
            details = result["details"]
            action = details.get("action", "synced")
            print(f"  • {result['symbol']}: {action}")
    
    if failed:
        print("\n💥 Failed to sync:")
        for result in failed:
            print(f"  • {result['symbol']}: {result.get('error', 'Unknown error')}")
    
    print(f"\n🕒 Sync completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
