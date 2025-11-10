#!/usr/bin/env python3
"""Update only Binance trading data to Notion (no CoinGecko/CMC calls)

This script updates:
- Spot & Perp prices and 24h price changes
- 24h trading volumes
- Open Interest
- Funding rate & cycle
- Basis calculation
- Index composition data

Does NOT update:
- Supply data (already from CMC)
- ATH/ATL data (from CoinGecko)
- Logo, website, genesis date (already from CMC)
"""

import requests
import os
import json
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Configuration
ROOT = Path(__file__).resolve().parents[1]
NOTION_CONFIG_FILE = ROOT / 'config' / 'config.json'
CMC_MAPPING_FILE = ROOT / 'config' / 'binance_cmc_mapping.json'
PERP_ONLY_CACHE_FILE = ROOT / 'data' / 'perp_only_cache.json'
API_CONFIG_FILE = ROOT / 'config' / 'api_config.json'
BLACKLIST_FILE = ROOT / 'config' / 'blacklist.json'


class CMCClient:
    """CoinMarketCap API client for fetching token metadata"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://pro-api.coinmarketcap.com/v1"
        self.headers = {
            'X-CMC_PRO_API_KEY': api_key,
            'Accept': 'application/json'
        }
    
    def get_token_data(self, cmc_id: int) -> Optional[Dict]:
        """Get both metadata and quote for a single token"""
        if not cmc_id:
            return None
        
        try:
            # Get metadata (logo, website, genesis date, etc.)
            metadata_url = f"{self.base_url}/cryptocurrency/info"
            metadata_params = {'id': str(cmc_id)}
            metadata_response = requests.get(metadata_url, headers=self.headers, params=metadata_params, timeout=30)
            metadata_response.raise_for_status()
            metadata_result = metadata_response.json()
            
            # Get quote (price, market cap, supply, etc.)
            quote_url = f"{self.base_url}/cryptocurrency/quotes/latest"
            quote_params = {'id': str(cmc_id)}
            quote_response = requests.get(quote_url, headers=self.headers, params=quote_params, timeout=30)
            quote_response.raise_for_status()
            quote_result = quote_response.json()
            
            if (metadata_result.get('status', {}).get('error_code') == 0 and 
                quote_result.get('status', {}).get('error_code') == 0):
                metadata = metadata_result.get('data', {}).get(str(cmc_id), {})
                quote = quote_result.get('data', {}).get(str(cmc_id), {})
                return {'metadata': metadata, 'quote': quote}
            else:
                return None
                
        except Exception as e:
            print(f"  ⚠️  CMC data unavailable: {e}")
            return None


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
            return ({
                "spot_price": float(data["lastPrice"]),
                "spot_24h_change": float(data["priceChangePercent"]),
                "spot_volume_24h": float(data["quoteVolume"])
            }, None, None)
        except Exception as e:
            # Try to extract HTTP status and message when available
            status = None
            text = None
            try:
                if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
                    status = e.response.status_code
                    text = e.response.text
                elif hasattr(e, 'response') and getattr(e, 'response') is not None:
                    status = getattr(e.response, 'status_code', None)
                    text = getattr(e.response, 'text', None)
            except Exception:
                pass

            print(f"  ⚠️  Spot data unavailable: {e}")
            return (None, status, text)
    
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
            
            # Detect funding cycle (optional, controlled by caller)
            # Note: This is set to None here and will be fetched only if update_metadata=True
            perp_data["funding_cycle"] = None
            
            # Get index composition
            index_composition_data = BinanceDataFetcher.fetch_index_composition(symbol)
            if index_composition_data:
                perp_data["index_composition"] = index_composition_data.get("index_composition")
                perp_data["index_composition_summary"] = index_composition_data.get("index_composition_summary")
            
            return perp_data
            
        except Exception as e:
            print(f"  ⚠️  Perp data unavailable: {e}")
            return None
    
    @staticmethod
    def detect_funding_cycle(symbol: str) -> Optional[int]:
        """Detect funding rate cycle (1h, 4h, or 8h)"""
        try:
            url = "https://fapi.binance.com/fapi/v1/fundingRate"
            params = {"symbol": f"{symbol}USDT", "limit": 2}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if len(data) >= 2:
                time_diff_ms = data[1]['fundingTime'] - data[0]['fundingTime']
                time_diff_hours = time_diff_ms / (1000 * 60 * 60)
                
                # Support 1h, 4h, and 8h cycles
                if 0.5 <= time_diff_hours <= 1.5:
                    return 1
                elif 3.5 <= time_diff_hours <= 4.5:
                    return 4
                elif 7.5 <= time_diff_hours <= 8.5:
                    return 8
            
            return None
        except:
            return None

    @staticmethod
    def fetch_index_composition(symbol: str) -> Optional[Dict]:
        """Fetch index price composition from Binance API."""
        try:
            url = "https://fapi.binance.com/fapi/v1/constituents"
            params = {"symbol": f"{symbol}USDT"}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            composition_data = response.json()
            
            if not composition_data:
                return None
                
            constituents = composition_data.get("constituents", [])
            if not constituents:
                return None
            
            # Create composition summary for easy reading
            exchange_weights = {}
            for constituent in constituents:
                exchange = constituent.get("exchange", "unknown")
                weight = float(constituent.get("weight", 0))
                exchange_weights[exchange] = weight
            
            # Sort by weight descending
            sorted_exchanges = sorted(exchange_weights.items(), key=lambda x: x[1], reverse=True)
            summary_parts = [f"{exchange} ({weight*100:.0f}%)" for exchange, weight in sorted_exchanges]
            summary = ", ".join(summary_parts[:5])  # Top 5 exchanges
            if len(sorted_exchanges) > 5:
                summary += f", +{len(sorted_exchanges)-5} more"
            
            return {
                "index_composition": constituents,
                "index_composition_summary": summary
            }
            
        except Exception as e:
            print(f"  ⚠️  Index composition unavailable: {e}")
            return None
    
    @staticmethod
    def fetch_categories(symbol: str) -> Optional[list]:
        """Fetch categories/tags from Binance Perpetual API
        
        Returns:
            List of category strings, or None if not available
        """
        try:
            url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Find the symbol
            for s in data['symbols']:
                if s['symbol'] == f"{symbol}USDT":
                    categories = s.get('underlyingSubType', [])
                    return categories if categories else None
            
            return None
            
        except Exception as e:
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

    def get_database_properties(self) -> set:
        """Return a set of property names for the configured database"""
        url = f"{self.base_url}/databases/{self.database_id}"
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            props = set(data.get('properties', {}).keys())
            return props
        except Exception as e:
            print(f"⚠️  Failed to fetch database schema: {e}")
            return set()
    
    def get_page_by_symbol(self, symbol: str) -> Optional[Dict]:
        """Find page by symbol
        
        Returns:
            - Page dict if found
            - None if not found
            - Raises exception if query fails (to distinguish from "not found")
        """
        filter_params = {
            "property": "Symbol",
            "title": {
                "equals": symbol
            }
        }
        
        try:
            results = self.query_database(filter_params)
            
            # If multiple pages found (duplicates), return the oldest one (first created)
            if len(results) > 1:
                print(f"⚠️  Found {len(results)} pages for {symbol}, using oldest", end=" ")
                # Sort by created_time and return the oldest
                results_sorted = sorted(results, key=lambda p: p.get('created_time', ''))
                return results_sorted[0]
            
            return results[0] if results else None
            
        except Exception as e:
            # Re-raise exception so caller knows query failed (not just "not found")
            raise Exception(f"Query failed for {symbol}: {e}")
    
    def create_page(self, properties: Dict, icon_url: str = None, symbol: str = None) -> Dict:
        """Create new page with optional icon
        
        Args:
            properties: Page properties
            icon_url: Optional icon URL
            symbol: Symbol name (for duplicate check)
        """
        # Double-check: query one more time before creating to prevent race conditions
        if symbol:
            try:
                existing = self.get_page_by_symbol(symbol)
                if existing:
                    print(f"⚠️  Page already exists (found in final check), updating instead", end=" ")
                    return self.update_page(existing['id'], properties, icon_url)
            except Exception as e:
                # If query fails, log but proceed with creation
                print(f"⚠️  Final check query failed: {str(e)[:40]}...", end=" ")
        
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
            raise
    
    def update_page(self, page_id: str, properties: Dict, icon_url: str = None) -> Dict:
        """Update existing page with optional icon"""
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
            raise


def build_trading_properties(symbol: str, spot_data: Dict, perp_data: Dict, cmc_data: Dict = None, cmc_full_data: Dict = None, existing_page: Dict = None, is_new_page: bool = False, update_metadata: bool = False, update_static_fields: bool = False) -> tuple:
    """Build Notion properties for trading data and CMC metadata
    
    Args:
        symbol: Token symbol
        spot_data: Spot market data from Binance
        perp_data: Perpetual futures data from Binance
        cmc_data: Basic CMC mapping (cmc_id, cmc_slug) - used to determine if page should be created
        cmc_full_data: Full CMC data (metadata and quote) - fetched from CMC API
        existing_page: Existing Notion page data (for updates) - used to read Circulating Supply
        is_new_page: Whether this is for a new page (includes metadata fields like Logo, Website, etc.)
        update_metadata: Whether to update metadata fields (Supply data from CMC API)
        update_static_fields: Whether to update static fields (Funding Cycle, Categories, Index Composition)
    
    Returns:
        tuple: (properties dict, icon_url str or None)
    """
    
    properties = {}
    icon_url = None
    
    # Prepare CMC metadata/quote shortcuts if provided
    metadata = {}
    quote = {}
    if cmc_full_data:
        metadata = cmc_full_data.get('metadata', {}) or {}
        quote = cmc_full_data.get('quote', {}) or {}

    # Logo (only for new pages)
    # Note: Notion property ordering is defined by the database; sending Logo first
    # often places it earlier when creating a page. We also return icon_url to set the page icon.
    if is_new_page and metadata.get('logo'):
        logo_url = metadata.get('logo')
        if logo_url:
            properties["Logo"] = {"url": logo_url}
            icon_url = logo_url

    # Symbol (required for new pages)
    if is_new_page and cmc_data:
        properties["Symbol"] = {
            "title": [{"text": {"content": symbol}}]
        }
    
    # CMC static metadata (only for new pages)
    if is_new_page and cmc_full_data:
        # Logo URL handled above (Logo property + icon_url)
        # Also keep legacy CoinGecko ID field for backward compatibility
        if metadata.get('logo') and not properties.get('Logo'):
            icon_url = metadata.get('logo')
            properties["CoinGecko ID"] = {
                "rich_text": [{"text": {"content": icon_url}}]
            }
        
        # Website
        if metadata.get('urls', {}).get('website'):
            website = metadata['urls']['website'][0]
            if website:
                properties["Website"] = {"url": website}
        
        # Genesis Date
        if metadata.get('date_added'):
            try:
                date_str = metadata['date_added'].split('T')[0]
                properties["Genesis Date"] = {"date": {"start": date_str}}
            except:
                pass
    
    # CMC dynamic data (supply & FDV - only update if update_metadata=True or is_new_page)
    # Note: If not updating, MC calculation will use existing Notion supply data
    if cmc_full_data and quote and (update_metadata or is_new_page):
        # Circulating Supply
        circ = quote.get('circulating_supply') or quote.get('self_reported_circulating_supply')
        if circ and circ > 0:
            properties["Circulating Supply"] = {"number": round(circ, 2)}
        
        # Total Supply
        if quote.get('total_supply'):
            properties["Total Supply"] = {"number": round(quote['total_supply'], 2)}
        
        # Max Supply
        if quote.get('max_supply'):
            properties["Max Supply"] = {"number": round(quote['max_supply'], 2)}
        
        # FDV
        if quote.get('quote', {}).get('USD'):
            usd_data = quote['quote']['USD']
            if usd_data.get('fully_diluted_market_cap'):
                properties["FDV"] = {"number": round(usd_data['fully_diluted_market_cap'], 2)}
    
    # Spot market data
    spot_price = None
    if spot_data:
        if spot_data.get("spot_price") is not None:
            spot_price = spot_data["spot_price"]
            properties["Spot Price"] = {"number": spot_price}
        
        if spot_data.get("spot_volume_24h") is not None:
            properties["Spot vol 24h"] = {"number": spot_data["spot_volume_24h"]}
        # Spot 24h percent change -> store in DB's `Price change` (as fraction)
        if spot_data.get("spot_24h_change") is not None:
            try:
                properties["Price change"] = {"number": round(spot_data["spot_24h_change"] / 100.0, 6)}
            except Exception:
                pass
    
    # Perp market data
    has_perp_price = False
    if perp_data:
        if perp_data.get("perp_price") is not None:
            properties["Perp Price"] = {"number": perp_data["perp_price"]}
            has_perp_price = True
        
        if perp_data.get("perp_volume_24h") is not None:
            properties["Perp vol 24h"] = {"number": perp_data["perp_volume_24h"]}
        
        if perp_data.get("open_interest_usd") is not None:
            properties["OI"] = {"number": perp_data["open_interest_usd"]}
        
        if perp_data.get("funding_rate") is not None:
            properties["Funding"] = {"number": perp_data["funding_rate"]}
        
        # Funding Cycle - only update if update_static_fields=True or is_new_page
        if (update_static_fields or is_new_page):
            funding_cycle = BinanceDataFetcher.detect_funding_cycle(symbol)
            if funding_cycle is not None:
                properties["Funding Cycle"] = {"number": funding_cycle}
        
        if perp_data.get("basis") is not None:
            properties["Basis"] = {"number": perp_data["basis"]}
        
        # Index Composition - only update if update_static_fields=True or is_new_page
        if (update_static_fields or is_new_page) and perp_data.get("index_composition_summary") is not None:
            properties["Index Composition"] = {
                "rich_text": [{"text": {"content": perp_data["index_composition_summary"]}}]
            }
        # Perp 24h percent change -> fallback to `Price change` if spot wasn't set
        if perp_data.get("perp_24h_change") is not None and "Price change" not in properties:
            try:
                properties["Price change"] = {"number": round(perp_data["perp_24h_change"] / 100.0, 6)}
            except Exception:
                pass
    
    # 🔧 Calculate MC and FDV for 1000X series
    # For 1000X symbols (1000PEPE, 1000BONK, etc.), we need to divide by the multiplier
    # because the price is multiplied but supply is for the base token
    multiplier = 1
    if cmc_data and cmc_data.get('multiplier'):
        multiplier = cmc_data['multiplier']
    
    # 🔧 Calculate MC = Circulating Supply * Price (from Binance) / Multiplier
    # Get Circulating Supply from: 1) CMC quote data (for new pages or updates with CMC data)
    #                              2) existing Notion page (fallback if CMC unavailable or returns None)
    circulating_supply = None
    if quote:  # Try CMC quote data first
        circulating_supply = quote.get('circulating_supply') or quote.get('self_reported_circulating_supply')
    
    # Fallback: read from existing Notion page if CMC didn't provide data
    if not circulating_supply and existing_page:
        circ_prop = existing_page.get('properties', {}).get('Circulating Supply', {})
        circulating_supply = circ_prop.get('number')
    
    if circulating_supply and circulating_supply > 0:
        # Determine which price to use: Perp Price > Spot Price
        price_for_mc = None
        if has_perp_price and perp_data and perp_data.get("perp_price"):
            price_for_mc = perp_data["perp_price"]
        elif spot_price:
            price_for_mc = spot_price
        
        if price_for_mc:
            # For 1000X symbols: divide by multiplier
            mc_value = (circulating_supply * price_for_mc) / multiplier
            properties["MC"] = {"number": round(mc_value, 2)}
    
    # 🔧 Adjust FDV for 1000X series
    # If FDV was set from CMC data and this is a 1000X symbol, we need to recalculate it
    if multiplier > 1 and "FDV" in properties:
        # FDV from CMC is based on base token, but we're using 1000X price
        # Need to recalculate: FDV = Total Supply * Price / Multiplier
        total_supply = None
        if quote:
            total_supply = quote.get('total_supply') or quote.get('max_supply')
        
        # Fallback: read from existing Notion page if CMC didn't provide data
        if not total_supply and existing_page:
            ts_prop = existing_page.get('properties', {}).get('Total Supply', {})
            total_supply = ts_prop.get('number')
        
        if total_supply and total_supply > 0:
            price_for_fdv = None
            if has_perp_price and perp_data and perp_data.get("perp_price"):
                price_for_fdv = perp_data["perp_price"]
            elif spot_price:
                price_for_fdv = spot_price
            
            if price_for_fdv:
                fdv_value = (total_supply * price_for_fdv) / multiplier
                properties["FDV"] = {"number": round(fdv_value, 2)}
    
    # Binance Categories (fetch from Perpetual API)
    # Only update if update_static_fields=True or is_new_page
    if (update_static_fields or is_new_page):
        categories = BinanceDataFetcher.fetch_categories(symbol)
        if categories:
            # Convert list to comma-separated string for Notion multi-select or rich text
            properties["Categories"] = {
                "multi_select": [{"name": cat} for cat in categories]
            }
    
    return properties, icon_url


def auto_match_new_symbols(cmc_mapping: Dict, cmc_api_key: str) -> Dict:
    """
    Automatically match new Binance symbols to CoinMarketCap
    Returns updated mapping if any new symbols were found
    """
    print("\n🔍 Checking for new Binance symbols...")
    
    # Get all Binance symbols
    all_binance_symbols = set()
    try:
        # Perp symbols
        perp_response = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo", timeout=10)
        perp_response.raise_for_status()
        for s in perp_response.json()['symbols']:
            if s['symbol'].endswith('USDT') and s['status'] == 'TRADING':
                all_binance_symbols.add(s['symbol'].replace('USDT', ''))
        
        # Spot symbols
        spot_response = requests.get("https://api.binance.com/api/v3/exchangeInfo", timeout=10)
        spot_response.raise_for_status()
        for s in spot_response.json()['symbols']:
            if s['symbol'].endswith('USDT') and s['status'] == 'TRADING':
                all_binance_symbols.add(s['symbol'].replace('USDT', ''))
    except Exception as e:
        print(f"  ⚠️  Failed to fetch Binance symbols: {e}")
        return cmc_mapping
    
    # Find new symbols (not in mapping or with null cmc_id)
    new_symbols = []
    for symbol in sorted(all_binance_symbols):
        if symbol not in cmc_mapping or not cmc_mapping[symbol].get('cmc_id'):
            new_symbols.append(symbol)
    
    if not new_symbols:
        print(f"  ✅ No new symbols to match (total: {len(all_binance_symbols)})")
        return cmc_mapping
    
    print(f"  🆕 Found {len(new_symbols)} new symbols to match")
    
    # Match new symbols via CMC API
    headers = {
        'X-CMC_PRO_API_KEY': cmc_api_key,
        'Accept': 'application/json'
    }
    
    matched = 0
    for symbol in new_symbols:
        try:
            # Search CMC for the symbol
            url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/map"
            params = {'symbol': symbol, 'limit': 10}
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status', {}).get('error_code') == 0:
                matches = data.get('data', [])
                if matches:
                    # Prefer active coins
                    active_matches = [m for m in matches if m.get('is_active') == 1]
                    best_match = active_matches[0] if active_matches else matches[0]
                    
                    cmc_mapping[symbol] = {
                        'cmc_id': best_match['id'],
                        'cmc_slug': best_match['slug'],
                        'cmc_symbol': best_match['symbol'],
                        'match_type': 'auto'
                    }
                    matched += 1
                    print(f"     ✅ {symbol} → {best_match['slug']} (ID: {best_match['id']})")
                else:
                    cmc_mapping[symbol] = {
                        'cmc_id': None,
                        'cmc_slug': None,
                        'cmc_symbol': None,
                        'match_type': 'none'
                    }
            
            time.sleep(0.3)  # Rate limiting
            
        except Exception as e:
            print(f"     ⚠️  {symbol}: {str(e)[:60]}")
            cmc_mapping[symbol] = {
                'cmc_id': None,
                'cmc_slug': None,
                'cmc_symbol': None,
                'match_type': 'none'
            }
    
    if matched > 0:
        # Save updated mapping
        mapping_data = {
            "metadata": {
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_symbols": len(cmc_mapping)
            },
            "mapping": cmc_mapping
        }
        with CMC_MAPPING_FILE.open('w') as f:
            json.dump(mapping_data, f, indent=2, ensure_ascii=False)
        print(f"  💾 Saved {matched} new matches to mapping file")
    
    return cmc_mapping


def classify_symbols() -> Dict[str, List[str]]:
    """Classify symbols into perp-only and spot+perp categories"""
    print("🔍 Classifying symbols by market availability...")
    
    # Get all perpetual contracts
    try:
        perp_response = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo", timeout=10)
        perp_response.raise_for_status()
        perp_symbols = {s['symbol'].replace('USDT', '') for s in perp_response.json()['symbols'] 
                       if s['symbol'].endswith('USDT') and s['status'] == 'TRADING'}
        print(f"  ✅ Found {len(perp_symbols)} perpetual contracts")
    except Exception as e:
        print(f"  ❌ Failed to fetch perpetual contracts: {e}")
        return {"perp_only": [], "spot_and_perp": []}
    
    # Get all spot pairs
    try:
        spot_response = requests.get("https://api.binance.com/api/v3/exchangeInfo", timeout=10)
        spot_response.raise_for_status()
        spot_symbols = {s['symbol'].replace('USDT', '') for s in spot_response.json()['symbols'] 
                       if s['symbol'].endswith('USDT') and s['status'] == 'TRADING'}
        print(f"  ✅ Found {len(spot_symbols)} spot pairs")
    except Exception as e:
        print(f"  ❌ Failed to fetch spot pairs: {e}")
        return {"perp_only": [], "spot_and_perp": []}
    
    # Classify
    perp_only = sorted(list(perp_symbols - spot_symbols))
    spot_and_perp = sorted(list(perp_symbols & spot_symbols))
    
    print(f"  📊 Classification complete:")
    print(f"     • Perp-only: {len(perp_only)} symbols")
    print(f"     • Spot+Perp: {len(spot_and_perp)} symbols")
    
    return {
        "perp_only": perp_only,
        "spot_and_perp": spot_and_perp
    }


def main():
    """Main function to update Binance trading data to Notion"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Update Binance trading data to Notion',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Update all coins (prices, volumes, funding rate, OI, basis only)
  python3 scripts/update_binance_trading_data.py
  
  # Update all coins + static fields (Funding Cycle, Categories, Index Composition)
  python3 scripts/update_binance_trading_data.py --update-static-fields
  
  # Update all coins + metadata (supply data + static fields, calls CMC API)
  python3 scripts/update_binance_trading_data.py --update-metadata
  
  # Update specific coins only
  python3 scripts/update_binance_trading_data.py BTC ETH SOL
  
  # Update specific coins with static fields
  python3 scripts/update_binance_trading_data.py --update-static-fields BTC ETH
        '''
    )
    parser.add_argument('symbols', nargs='*', help='Specific symbols to update (optional)')
    parser.add_argument('--update-metadata', '--update-supply', action='store_true', 
                       help='Update all metadata: Supply (Circ/Total/Max) + Static Fields (slower, calls CMC API)')
    parser.add_argument('--update-static-fields', action='store_true',
                       help='Update static fields: Funding Cycle, Categories, Index Composition (no CMC API call)')
    # Keep for backward compatibility
    parser.add_argument('--update-funding-cycle', action='store_true',
                       help='(Deprecated: use --update-static-fields) Update Funding Cycle only')
    
    args = parser.parse_args()
    
    # Load configuration
    if not NOTION_CONFIG_FILE.exists():
        print(f"❌ Config file not found: {NOTION_CONFIG_FILE}")
        return
    
    with NOTION_CONFIG_FILE.open('r') as f:
        config = json.load(f)
    
    notion_api_key = config['notion']['api_key']
    notion_database_id = config['notion']['database_id']
    
    if not notion_api_key or not notion_database_id:
        print("❌ Notion API key or database ID not found in config")
        return
    
    # Initialize Notion client
    notion = NotionClient(notion_api_key, notion_database_id)
    
    # Initialize CMC client (optional, only for creating new pages)
    cmc_client = None
    if API_CONFIG_FILE.exists():
        try:
            with API_CONFIG_FILE.open('r') as f:
                api_config = json.load(f)
                cmc_api_key = api_config.get('coinmarketcap', {}).get('api_key')
                if cmc_api_key:
                    cmc_client = CMCClient(cmc_api_key)
                    print("✅ CMC API client initialized")
                else:
                    print("⚠️  CMC API key not found, new pages will not have CMC metadata")
        except Exception as e:
            print(f"⚠️  Failed to initialize CMC client: {e}")
    else:
        print("⚠️  API config file not found, new pages will not have CMC metadata")
    
    # Get database properties (to check whether 'Logo' property exists)
    db_props = notion.get_database_properties()
    if db_props:
        print(f"✅ Notion database properties loaded ({len(db_props)} fields)")
    else:
        print("⚠️  Could not load Notion database schema; will fallback to legacy logo field if needed")
    # Load blacklist
    blacklist = set()
    if BLACKLIST_FILE.exists():
        try:
            with BLACKLIST_FILE.open('r') as f:
                blacklist_data = json.load(f)
                blacklist = set(blacklist_data.get('blacklist', []))
            if blacklist:
                print(f"🚫 Loaded blacklist: {len(blacklist)} symbols ({', '.join(sorted(blacklist))})")
        except Exception as e:
            print(f"⚠️  Failed to load blacklist: {e}")
    
    # Load CMC mapping
    cmc_mapping = {}
    if CMC_MAPPING_FILE.exists():
        with CMC_MAPPING_FILE.open('r') as f:
            raw = json.load(f)
            # support two formats: {"mapping": {...}} or plain dict
            if isinstance(raw, dict) and 'mapping' in raw and isinstance(raw['mapping'], dict):
                cmc_mapping = raw['mapping']
            elif isinstance(raw, dict):
                cmc_mapping = raw
            else:
                cmc_mapping = {}
        print(f"📋 Loaded CMC mapping entries: {len(cmc_mapping)}")
    else:
        print("⚠️  CMC mapping file not found, will skip CMC data")
    
    # Auto-match new Binance symbols to CMC
    if cmc_client and cmc_mapping is not None:
        try:
            cmc_mapping = auto_match_new_symbols(cmc_mapping, cmc_client.api_key)
        except Exception as e:
            print(f"⚠️  Auto-matching failed: {e}")

    # Load perp-only cache if exists
    perp_only_cache = set()
    if PERP_ONLY_CACHE_FILE.exists():
        try:
            with PERP_ONLY_CACHE_FILE.open('r') as pf:
                raw = json.load(pf)
                if isinstance(raw, list):
                    perp_only_cache = set(raw)
        except Exception as e:
            print(f"⚠️  Failed to load perp-only cache: {e}")

    # Initialize retry-created counters to avoid NameError in final reporting
    retry_created = 0
    skipped_retry_created = 0
    
    # Classify symbols by market availability
    classification = classify_symbols()
    perp_only_symbols = set(classification['perp_only'])
    spot_and_perp_symbols = set(classification['spot_and_perp'])

    # Merge persisted cache into runtime perp-only set
    perp_only_symbols |= perp_only_cache
    
    # Combine all symbols to process
    # If classification returned empty (e.g., spot exchangeInfo blocked), fall back to CMC mapping keys
    if not (perp_only_symbols or spot_and_perp_symbols):
        all_symbols = sorted(list(cmc_mapping.keys()))
    else:
        all_symbols = sorted(list(perp_only_symbols | spot_and_perp_symbols))

    # Command line symbols override (if provided)
    if args.symbols:
        all_symbols = [s.upper() for s in args.symbols]
        print(f"🎯 Processing specific symbols: {', '.join(all_symbols)}")
    # DRY run: override list with env var DRY_SYMBOLS (comma separated) for quick tests
    elif os.getenv('DRY_SYMBOLS'):
        dry = os.getenv('DRY_SYMBOLS')
        dry_list = [s.strip().upper() for s in dry.split(',') if s.strip()]
        if dry_list:
            print(f"⚗️  DRY RUN enabled — processing only: {', '.join(dry_list)}")
            all_symbols = dry_list
    
    # Print update mode
    if args.update_metadata:
        print(f"📊 Processing {len(all_symbols)} symbols total (with metadata: Supply + Funding Cycle)")
    elif args.update_funding_cycle:
        print(f"📊 Processing {len(all_symbols)} symbols total (with Funding Cycle update)")
    else:
        print(f"📊 Processing {len(all_symbols)} symbols total (prices/volumes/funding only)")
    
    # Statistics
    success_count = 0
    created_count = 0
    skipped_count = 0
    error_count = 0
    failed_symbols = []
    skipped_symbols = []  # Track skipped symbols for retry
    
    # Process each symbol
    for i, symbol in enumerate(all_symbols, 1):
        try:
            print(f"[{i:3d}/{len(all_symbols):3d}] {symbol}", end=" ")
            
            # Check blacklist - skip completely
            if symbol in blacklist:
                print(f"🚫 Blacklisted - skipped")
                skipped_count += 1
                continue
            
            # Add small delay between each request to avoid rate limiting and proxy errors
            # 200ms * 625 symbols = ~125 seconds total (about 2 minutes overhead)
            if i > 1:
                time.sleep(0.2)  # 200ms delay between each symbol
            
            # Determine market type
            is_perp_only = symbol in perp_only_symbols
            has_spot = symbol in spot_and_perp_symbols
            
            # Check if page exists in Notion
            page = None
            try:
                page = notion.get_page_by_symbol(symbol)
            except Exception as e:
                # Network error when querying Notion
                print(f"⚠️  Notion query failed ({str(e)[:50]}...)")
                skipped_count += 1
                skipped_symbols.append(symbol)
                continue
            
            # Fetch trading data based on market availability
            spot_data = None
            spot_error_code = None
            spot_error_text = None
            if has_spot:
                spot_result = BinanceDataFetcher.fetch_spot_data(symbol)
                # fetch_spot_data now returns (data, status, text)
                if isinstance(spot_result, tuple):
                    spot_data, spot_error_code, spot_error_text = spot_result
                else:
                    spot_data = spot_result
            elif is_perp_only:
                print(f"[Perp-only]", end=" ")
            
            perp_data = BinanceDataFetcher.fetch_perp_data(symbol)

            # If spot data missing but perp data exists, and spot failure indicates symbol not found,
            # mark as perp-only and persist to cache for future runs.
            try:
                if (spot_data is None) and perp_data is not None:
                    # Consider it a true "no spot listing" if spot_error_code is 400/404 or if response text hints symbol not found
                    msg = (spot_error_text or "").lower() if spot_error_text else ""
                    if spot_error_code in (400, 404) or 'symbol' in msg and 'not' in msg and 'found' in msg:
                        if symbol not in perp_only_cache:
                            perp_only_cache.add(symbol)
                            # persist cache
                            try:
                                with PERP_ONLY_CACHE_FILE.open('w') as pf:
                                    json.dump(sorted(list(perp_only_cache)), pf, indent=2)
                                print(f" [cached perp-only]", end=" ")
                            except Exception as e:
                                print(f" ⚠️ failed to persist perp-only cache: {e}")
            except Exception:
                pass
            
            if not spot_data and not perp_data:
                print(f"⚠️  Skipped: No data available")
                skipped_count += 1
                skipped_symbols.append(symbol)
                continue
            
            # If page doesn't exist, create it with CMC data
            if not page:
                cmc_data = cmc_mapping.get(symbol)
                if not cmc_data:
                    print(f"⚠️  Skipped: No Notion page and no CMC mapping")
                    skipped_count += 1
                    skipped_symbols.append(symbol)
                    continue
                
                # Fetch full CMC data if client is available and cmc_id exists
                cmc_full_data = None
                if cmc_client and cmc_data.get('cmc_id'):
                    try:
                        cmc_full_data = cmc_client.get_token_data(cmc_data['cmc_id'])
                        if cmc_full_data:
                            print(f"[+CMC]", end=" ")
                    except Exception as e:
                        print(f"[CMC err]", end=" ")
                
                # Build properties with both trading data and CMC metadata
                # New pages always get full metadata (supply + funding cycle)
                properties, icon_url = build_trading_properties(symbol, spot_data, perp_data, cmc_data, cmc_full_data, is_new_page=True, update_metadata=True, update_static_fields=True)

                # If DB doesn't have a 'Logo' property, move logo URL into legacy 'CoinGecko ID' field
                if properties.get('Logo') and 'Logo' not in db_props:
                    try:
                        logo_val = properties.pop('Logo')
                        logo_url = logo_val.get('url') if isinstance(logo_val, dict) else None
                        if logo_url:
                            properties['CoinGecko ID'] = {"rich_text": [{"text": {"content": logo_url}}]}
                    except Exception:
                        pass

                try:
                    notion.create_page(properties, icon_url, symbol=symbol)
                    print(f"🆕 Created new page", end=" | ")
                    created_count += 1
                except Exception as e:
                    print(f"❌ Failed to create: {str(e)[:50]}")
                    error_count += 1
                    failed_symbols.append(symbol)
                    continue
            else:
                # Update existing page
                cmc_data = cmc_mapping.get(symbol)
                cmc_full_data = None
                
                # Fetch CMC supply data only if --update-metadata flag is set
                if args.update_metadata and cmc_data and cmc_data.get('cmc_id') and cmc_client:
                    try:
                        cmc_full_data = cmc_client.get_token_data(cmc_data['cmc_id'])
                        if cmc_full_data:
                            print(f"[+CMC]", end=" ")
                    except Exception:
                        print(f"[CMC err]", end=" ")
                
                # Build properties - pass update flags
                # update_metadata=True: update supply data (calls CMC API) + also updates static fields
                # update_static_fields=True: update funding cycle, categories, index composition only
                # Backward compatibility: --update-funding-cycle maps to --update-static-fields
                update_meta = args.update_metadata
                update_static = args.update_static_fields or args.update_funding_cycle or args.update_metadata
                properties, _ = build_trading_properties(symbol, spot_data, perp_data, cmc_data, cmc_full_data, existing_page=page, is_new_page=False, update_metadata=update_meta, update_static_fields=update_static)
                
                # Check if page already has an icon
                existing_icon = page.get('icon')
                icon_url_to_set = None
                
                if not existing_icon:
                    # Try to get logo URL from CoinGecko ID field (where CMC logo URLs are stored)
                    cg_prop = page.get('properties', {}).get('CoinGecko ID', {})
                    if cg_prop.get('rich_text') and len(cg_prop['rich_text']) > 0:
                        content = cg_prop['rich_text'][0].get('text', {}).get('content', '')
                        if content.startswith('http') and 'coinmarketcap.com' in content:
                            icon_url_to_set = content
                            print(f"[+Icon]", end=" ")
                
                try:
                    notion.update_page(page['id'], properties, icon_url_to_set)
                except Exception as e:
                    print(f"❌ Failed to update: {str(e)[:50]}")
                    error_count += 1
                    failed_symbols.append(symbol)
                    continue
            
            # Print success info
            spot_price = spot_data.get('spot_price') if spot_data else None
            perp_price = perp_data.get('perp_price') if perp_data else None
            funding_rate = perp_data.get('funding_rate') if perp_data else None
            
            price_info = []
            if spot_price:
                price_info.append(f"Spot: ${spot_price:.4f}")
            if perp_price:
                price_info.append(f"Perp: ${perp_price:.4f}")
            if funding_rate:
                price_info.append(f"FR: {funding_rate*100:.3f}%")
            
            print(f"✅ {' | '.join(price_info)}")
            success_count += 1
            
        except Exception as e:
            print(f"❌ Error: {e}")
            error_count += 1
            failed_symbols.append(symbol)
    
    # Final statistics
    print(f"\n=== Update Complete ===")
    print(f"Success: {success_count} (Updated: {success_count - created_count}, Created: {created_count})")
    print(f"Skipped: {skipped_count}")
    print(f"Errors: {error_count}")
    
    # Retry failed symbols until all succeed (max 5 rounds)
    retry_round = 1
    while failed_symbols and retry_round <= 5:
        print(f"\n🔄 Retry round {retry_round}: {len(failed_symbols)} failed symbols...")
        time.sleep(2)  # Wait before retry
        
        retry_failed = []
        retry_success = 0
        retry_created = 0
        
        for symbol in failed_symbols:
            try:
                print(f"Retry {symbol}", end=" ")
                
                page = notion.get_page_by_symbol(symbol)
                spot_result = BinanceDataFetcher.fetch_spot_data(symbol)
                if isinstance(spot_result, tuple):
                    spot_data, _, _ = spot_result
                else:
                    spot_data = spot_result
                perp_data = BinanceDataFetcher.fetch_perp_data(symbol)
                
                if not spot_data and not perp_data:
                    print("⚠️  No data")
                    continue
                
                if not page:
                    # Try to create new page
                    cmc_data = cmc_mapping.get(symbol)
                    if not cmc_data:
                        print("⚠️  No CMC data")
                        continue
                    
                    # Fetch full CMC data if available
                    cmc_full_data = None
                    if cmc_client and cmc_data.get('cmc_id'):
                        try:
                            cmc_full_data = cmc_client.get_token_data(cmc_data['cmc_id'])
                        except Exception:
                            pass
                    
                    properties, icon_url = build_trading_properties(symbol, spot_data, perp_data, cmc_data, cmc_full_data, is_new_page=True, update_metadata=True, update_static_fields=True)

                    # If DB doesn't have a 'Logo' property, move logo URL into legacy 'CoinGecko ID' field
                    if properties.get('Logo') and 'Logo' not in db_props:
                        try:
                            logo_val = properties.pop('Logo')
                            logo_url = logo_val.get('url') if isinstance(logo_val, dict) else None
                            if logo_url:
                                properties['CoinGecko ID'] = {"rich_text": [{"text": {"content": logo_url}}]}
                        except Exception:
                            pass

                    notion.create_page(properties, icon_url, symbol=symbol)
                    print("✅ Created")
                    retry_created += 1
                else:
                    # Update existing page - fetch CMC data for MC calculation
                    cmc_data = cmc_mapping.get(symbol)
                    cmc_full_data = None
                    # Determine update flags for retry (use same as main loop)
                    update_meta_retry = args.update_metadata
                    update_static_retry = args.update_static_fields or args.update_funding_cycle or args.update_metadata
                    
                    if update_meta_retry and cmc_client and cmc_data and cmc_data.get('cmc_id'):
                        try:
                            cmc_full_data = cmc_client.get_token_data(cmc_data['cmc_id'])
                        except Exception:
                            pass
                    
                    properties, _ = build_trading_properties(symbol, spot_data, perp_data, cmc_data, cmc_full_data, existing_page=page, is_new_page=False, update_metadata=update_meta_retry, update_static_fields=update_static_retry)
                    
                    # Check if page already has an icon
                    existing_icon = page.get('icon')
                    icon_url_to_set = None
                    
                    if not existing_icon:
                        # Try to get logo URL from CoinGecko ID field
                        cg_prop = page.get('properties', {}).get('CoinGecko ID', {})
                        if cg_prop.get('rich_text') and len(cg_prop['rich_text']) > 0:
                            content = cg_prop['rich_text'][0].get('text', {}).get('content', '')
                            if content.startswith('http') and 'coinmarketcap.com' in content:
                                icon_url_to_set = content
                    
                    notion.update_page(page['id'], properties, icon_url_to_set)
                    print("✅ Updated")
                
                retry_success += 1
                error_count -= 1
                success_count += 1
                    
            except Exception as e:
                print(f"❌ Still failing: {str(e)[:60]}...")
                retry_failed.append(symbol)
        
        print(f"  Retry result: {retry_success}/{len(failed_symbols)} recovered (Created: {retry_created})")
        failed_symbols = retry_failed
        retry_round += 1
    
    if failed_symbols:
        print(f"\n⚠️  {len(failed_symbols)} symbols still failed after retries: {', '.join(failed_symbols[:10])}")
        if len(failed_symbols) > 10:
            print(f"    ... and {len(failed_symbols) - 10} more")
    
    # Retry skipped symbols until all succeed (max 5 rounds)
    skipped_retry_round = 1
    while skipped_symbols and skipped_retry_round <= 5:
        print(f"\n🔄 Retry skipped (round {skipped_retry_round}): {len(skipped_symbols)} symbols...")
        time.sleep(2)  # Wait before retry
        
        skipped_retry_failed = []
        skipped_retry_success = 0
        skipped_retry_created = 0
        
        for symbol in skipped_symbols:
            try:
                print(f"Retry {symbol}", end=" ")
                
                # Try to get Notion page
                page = notion.get_page_by_symbol(symbol)
                
                # Fetch trading data
                spot_result = BinanceDataFetcher.fetch_spot_data(symbol)
                if isinstance(spot_result, tuple):
                    spot_data, _, _ = spot_result
                else:
                    spot_data = spot_result
                perp_data = BinanceDataFetcher.fetch_perp_data(symbol)
                
                if not spot_data and not perp_data:
                    print("⚠️  No data")
                    continue
                
                if not page:
                    # Try to create new page
                    cmc_data = cmc_mapping.get(symbol)
                    if not cmc_data:
                        print("⚠️  No CMC data")
                        continue
                    
                    # Fetch full CMC data if available
                    cmc_full_data = None
                    if cmc_client and cmc_data.get('cmc_id'):
                        try:
                            cmc_full_data = cmc_client.get_token_data(cmc_data['cmc_id'])
                        except Exception:
                            pass
                    
                    properties, icon_url = build_trading_properties(symbol, spot_data, perp_data, cmc_data, cmc_full_data, is_new_page=True, update_metadata=True, update_static_fields=True)

                    # If DB doesn't have a 'Logo' property, move logo URL into legacy 'CoinGecko ID' field
                    if properties.get('Logo') and 'Logo' not in db_props:
                        try:
                            logo_val = properties.pop('Logo')
                            logo_url = logo_val.get('url') if isinstance(logo_val, dict) else None
                            if logo_url:
                                properties['CoinGecko ID'] = {"rich_text": [{"text": {"content": logo_url}}]}
                        except Exception:
                            pass

                    notion.create_page(properties, icon_url, symbol=symbol)
                    print("✅ Created")
                    skipped_retry_created += 1
                else:
                    # Update existing page - fetch CMC data for MC calculation
                    cmc_data = cmc_mapping.get(symbol)
                    cmc_full_data = None
                    # Determine update flags for retry (use same as main loop)
                    update_meta_skipped_retry = args.update_metadata
                    update_static_skipped_retry = args.update_static_fields or args.update_funding_cycle or args.update_metadata
                    
                    if update_meta_skipped_retry and cmc_client and cmc_data and cmc_data.get('cmc_id'):
                        try:
                            cmc_full_data = cmc_client.get_token_data(cmc_data['cmc_id'])
                        except Exception:
                            pass
                    
                    properties, _ = build_trading_properties(symbol, spot_data, perp_data, cmc_data, cmc_full_data, existing_page=page, is_new_page=False, update_metadata=update_meta_skipped_retry, update_static_fields=update_static_skipped_retry)
                    
                    # Check if page already has an icon
                    existing_icon = page.get('icon')
                    icon_url_to_set = None
                    
                    if not existing_icon:
                        # Try to get logo URL from CoinGecko ID field
                        cg_prop = page.get('properties', {}).get('CoinGecko ID', {})
                        if cg_prop.get('rich_text') and len(cg_prop['rich_text']) > 0:
                            content = cg_prop['rich_text'][0].get('text', {}).get('content', '')
                            if content.startswith('http') and 'coinmarketcap.com' in content:
                                icon_url_to_set = content
                    
                    notion.update_page(page['id'], properties, icon_url_to_set)
                    print("✅ Updated")
                
                skipped_retry_success += 1
                skipped_count -= 1
                success_count += 1
                    
            except Exception as e:
                print(f"❌ Still failing: {str(e)[:60]}...")
                skipped_retry_failed.append(symbol)
        
        print(f"  Retry result: {skipped_retry_success}/{len(skipped_symbols)} recovered (Created: {skipped_retry_created})")
        skipped_symbols = skipped_retry_failed
        skipped_retry_round += 1
    
    if skipped_symbols:
        print(f"\n⚠️  {len(skipped_symbols)} symbols still skipped after retries: {', '.join(skipped_symbols[:10])}")
        if len(skipped_symbols) > 10:
            print(f"    ... and {len(skipped_symbols) - 10} more")
    
    print(f"\n=== Final Statistics ===")
    print(f"✅ Total Success: {success_count} (Created: {created_count + retry_created + skipped_retry_created})")
    print(f"⚠️  Skipped: {skipped_count}")
    print(f"❌ Errors: {error_count}")


if __name__ == "__main__":
    main()
