#!/usr/bin/env python3
"""Enhanced Binance data fetcher with comprehensive market data for Notion dashboard.

This script fetches:
- Spot & Perp prices 
- 24h trading volume
- Open Interest
- Funding rate
- Index price and mark price
- Basis calculation (perp_price - index_price) / index_price
- Supply data from CoinGecko for local market cap calculation

Usage: python3 scripts/enhanced_data_fetcher.py --test-symbols BROCCOLI714,BROCCOLIF3B
"""

import requests
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any

# Global cache for CoinGecko coins list
_coingecko_coins_cache = None
_cache_timestamp = None
from dataclasses import dataclass, asdict

# Configuration
ROOT = Path(__file__).resolve().parents[1]
OVERRIDES_FILE = ROOT / 'overrides.json'
CMC_MAPPING_FILE = ROOT / 'binance_cmc_mapping.json'

# Global cache for local CMC mapping
_cmc_mapping_cache = None

@dataclass
class TokenData:
    base: str
    spot_price: Optional[float] = None
    perp_price: Optional[float] = None
    spot_24h_change: Optional[float] = None  # 现货24h价格变化
    perp_24h_change: Optional[float] = None  # 期货24h价格变化
    spot_volume_24h: Optional[float] = None
    perp_volume_24h: Optional[float] = None
    open_interest: Optional[float] = None
    open_interest_usd: Optional[float] = None
    funding_rate: Optional[float] = None
    funding_cycle: Optional[int] = None  # 资金费率周期（小时）
    index_price: Optional[float] = None
    mark_price: Optional[float] = None
    basis: Optional[float] = None
    
    # Index composition data
    index_composition: Optional[List[Dict[str, Any]]] = None
    index_composition_summary: Optional[str] = None
    
    # Supply data from CoinGecko (static, no need for real-time updates)
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None
    max_supply: Optional[float] = None
    
    # ATH/ATL data from CoinGecko (static)
    ath_price: Optional[float] = None
    ath_date: Optional[str] = None
    ath_market_cap: Optional[float] = None
    atl_price: Optional[float] = None
    atl_date: Optional[str] = None
    atl_market_cap: Optional[float] = None
    
    # Calculated market caps (local calculation)
    market_cap_calc: Optional[float] = None
    fdv_calc: Optional[float] = None
    
    # Additional token information
    logo_url: Optional[str] = None
    website: Optional[str] = None  # Official website URL
    genesis_date: Optional[str] = None  # Token launch date
    binance_listing_date: Optional[str] = None  # Binance listing date
    
    # CoinGecko mapping
    coingecko_id: Optional[str] = None


def load_overrides() -> Dict[str, str]:
    """Load symbol to CoinGecko ID overrides."""
    if OVERRIDES_FILE.exists():
        with OVERRIDES_FILE.open('r') as f:
            return json.load(f)
    return {}


def load_cmc_mapping() -> Dict[str, Dict]:
    """Load local CoinMarketCap mapping from binance_cmc_mapping.json.
    
    Returns:
        Dictionary mapping Binance symbols to CMC data (id, slug, symbol, match_type)
    """
    global _cmc_mapping_cache
    
    if _cmc_mapping_cache is not None:
        return _cmc_mapping_cache
    
    if CMC_MAPPING_FILE.exists():
        try:
            with CMC_MAPPING_FILE.open('r', encoding='utf-8') as f:
                data = json.load(f)
                _cmc_mapping_cache = data.get('mapping', {})
                print(f"✅ Loaded local CMC mapping for {len(_cmc_mapping_cache)} symbols")
                return _cmc_mapping_cache
        except Exception as e:
            print(f"⚠️ Failed to load CMC mapping: {e}")
            _cmc_mapping_cache = {}
            return {}
    else:
        print(f"⚠️ CMC mapping file not found: {CMC_MAPPING_FILE}")
        _cmc_mapping_cache = {}
        return {}


def binance_get(endpoint: str, params: Dict = None, base_url: str = "https://api.binance.com") -> Dict:
    """Make a request to Binance API with retry."""
    url = f"{base_url}{endpoint}"
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {endpoint}: {e}")
            if attempt < 2:
                time.sleep(1)
            else:
                raise
    return {}

def calculate_funding_cycle(symbol: str) -> int:
    """计算代币的资金费率周期"""
    try:
        symbol_usdt = f"{symbol}USDT"
        url = f'https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol_usdt}&limit=3'
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            if len(data) >= 2:
                # 计算时间间隔
                timestamp1 = int(data[0]['fundingTime'])
                timestamp2 = int(data[1]['fundingTime'])
                
                interval_ms = abs(timestamp1 - timestamp2)
                interval_hours = interval_ms / (1000 * 60 * 60)
                
                # 推断周期
                if 7.5 <= interval_hours <= 8.5:
                    return 8
                elif 3.5 <= interval_hours <= 4.5:
                    return 4  
                elif 5.5 <= interval_hours <= 6.5:
                    return 6
                else:
                    return 8  # 默认8小时
            else:
                return 8  # 默认8小时
        else:
            return 8  # 默认8小时
            
    except Exception as e:
        print(f"⚠️  计算 {symbol} 费率周期失败: {e}")
        return 8  # 默认8小时


def fetch_spot_data(symbol: str) -> Dict[str, Any]:
    """Fetch spot price and 24h volume."""
    try:
        ticker = binance_get("/api/v3/ticker/24hr", {"symbol": f"{symbol}USDT"})
        return {
            "spot_price": float(ticker["lastPrice"]),
            "spot_24h_change": float(ticker["priceChangePercent"]),  # 24h价格变化百分比
            "spot_volume_24h": float(ticker["quoteVolume"])  # 24h volume in USDT
        }
    except Exception as e:
        print(f"Error fetching spot data for {symbol}: {e}")
        return {}


def fetch_index_composition(symbol: str) -> Dict[str, Any]:
    """Fetch index price composition from Binance API."""
    try:
        composition_data = binance_get("/fapi/v1/constituents", 
                                     {"symbol": f"{symbol}USDT"}, 
                                     base_url="https://fapi.binance.com")
        
        if not composition_data:
            return {}
            
        constituents = composition_data.get("constituents", [])
        if not constituents:
            return {}
        
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
        print(f"Error fetching index composition for {symbol}: {e}")
        return {}


def fetch_perp_data(symbol: str) -> Dict[str, Any]:
    """Fetch perpetual contract data including funding rate and index composition."""
    try:
        # Get perp price and volume
        ticker = binance_get("/fapi/v1/ticker/24hr", 
                           {"symbol": f"{symbol}USDT"}, 
                           base_url="https://fapi.binance.com")
        
        # Get open interest
        oi_data = binance_get("/fapi/v1/openInterest", 
                             {"symbol": f"{symbol}USDT"}, 
                             base_url="https://fapi.binance.com")
        
        # Get funding rate and mark/index prices
        premium_data = binance_get("/fapi/v1/premiumIndex", 
                                 {"symbol": f"{symbol}USDT"}, 
                                 base_url="https://fapi.binance.com")
        
        result = {
            "perp_price": float(ticker["lastPrice"]),
            "perp_24h_change": float(ticker["priceChangePercent"]),  # 期货24h价格变化百分比
            "perp_volume_24h": float(ticker["quoteVolume"]),
            "open_interest": float(oi_data["openInterest"]),
        }
        
        if premium_data:
            result["funding_rate"] = float(premium_data["lastFundingRate"])
            result["mark_price"] = float(premium_data["markPrice"])
            result["index_price"] = float(premium_data["indexPrice"])
            
            # Calculate basis: (perp_price - index_price) / index_price
            if result["index_price"] and result["index_price"] > 0:
                result["basis"] = (result["perp_price"] - result["index_price"]) / result["index_price"]
        
        # Get index composition
        composition_data = fetch_index_composition(symbol)
        if composition_data:
            result["index_composition"] = composition_data.get("index_composition")
            result["index_composition_summary"] = composition_data.get("index_composition_summary")
        
        return result
        
    except Exception as e:
        print(f"Error fetching perp data for {symbol}: {e}")
        return {}


def fetch_coingecko_supply_data(coingecko_id: str) -> Dict[str, Any]:
    """Fetch supply, ATH/ATL, logo and additional data from CoinGecko (static data, no need for real-time updates)."""
    # CoinGecko Rate Limit: ~30 calls per minute (free tier)
    # So we need at least 2 seconds between requests
    time.sleep(2.1)
    
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        market_data = data.get("market_data", {})
        
        # Supply data
        result = {
            "circulating_supply": market_data.get("circulating_supply"),
            "total_supply": market_data.get("total_supply"),
            "max_supply": market_data.get("max_supply"),
        }
        
        # Logo data
        image_data = data.get("image", {})
        if image_data.get("small"):
            result["logo_url"] = image_data["small"]  # 128x128 size
        
        # Website data
        links_data = data.get("links", {})
        homepage = links_data.get("homepage", [])
        if homepage and homepage[0]:
            # Clean and validate the website URL
            website = homepage[0].strip()
            if website and not website.startswith(('mailto:', 'tel:')):
                if not website.startswith(('http://', 'https://')):
                    website = 'https://' + website
                result["website"] = website.rstrip('/')
        
        # Genesis/Launch date (use ATL date as approximation if genesis_date not available)
        genesis_date = data.get("genesis_date")
        if genesis_date:
            result["genesis_date"] = genesis_date
        else:
            # Use ATL date as approximation for launch date
            atl_date_data = market_data.get("atl_date", {})
            if atl_date_data and "usd" in atl_date_data:
                result["genesis_date"] = atl_date_data["usd"]
        
        # Try to estimate Binance listing date from tickers
        tickers = data.get("tickers", [])
        binance_tickers = [t for t in tickers if 'binance' in t.get('market', {}).get('name', '').lower()]
        if binance_tickers:
            # We can't get exact listing date from this API, but we know it's listed
            result["binance_listing_date"] = "Listed"  # Placeholder
        
        # ATH data
        ath_data = market_data.get("ath", {})
        if ath_data and "usd" in ath_data:
            result["ath_price"] = ath_data["usd"]
            
        ath_date_data = market_data.get("ath_date", {})
        if ath_date_data and "usd" in ath_date_data:
            result["ath_date"] = ath_date_data["usd"]
            
        # ATH market cap
        ath_market_cap = market_data.get("market_cap_ath", {})
        if ath_market_cap and "usd" in ath_market_cap:
            result["ath_market_cap"] = ath_market_cap["usd"]
        
        # ATL data  
        atl_data = market_data.get("atl", {})
        if atl_data and "usd" in atl_data:
            result["atl_price"] = atl_data["usd"]
            
        atl_date_data = market_data.get("atl_date", {})
        if atl_date_data and "usd" in atl_date_data:
            result["atl_date"] = atl_date_data["usd"]
            
        # ATL market cap
        atl_market_cap = market_data.get("market_cap_atl", {})
        if atl_market_cap and "usd" in atl_market_cap:
            result["atl_market_cap"] = atl_market_cap["usd"]
        
        return result
        
    except Exception as e:
        print(f"Error fetching CoinGecko data for {coingecko_id}: {e}")
        return {}


def calculate_market_caps(token_data: TokenData) -> TokenData:
    """Calculate market cap and FDV based on price and supply."""
    # Use spot price if available, otherwise perp price
    price = token_data.spot_price or token_data.perp_price
    
    if not price:
        return token_data
    
    # Market Cap = Price × Circulating Supply
    if token_data.circulating_supply and token_data.circulating_supply > 0:
        token_data.market_cap_calc = price * token_data.circulating_supply
    
    # FDV = Price × Total Supply (or Max Supply if Total Supply is None)
    supply_for_fdv = token_data.total_supply or token_data.max_supply
    if supply_for_fdv and supply_for_fdv > 0:
        token_data.fdv_calc = price * supply_for_fdv
    
    return token_data


def get_coingecko_coins_list():
    """Get CoinGecko coins list with caching."""
    global _coingecko_coins_cache, _cache_timestamp
    
    # Cache for 1 hour
    if _coingecko_coins_cache and _cache_timestamp and (time.time() - _cache_timestamp < 3600):
        return _coingecko_coins_cache
    
    # CoinGecko Rate Limit: ~30 calls per minute (free tier)
    time.sleep(2.1)
    
    try:
        print("📥 Fetching CoinGecko coins list...")
        url = "https://api.coingecko.com/api/v3/coins/list"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            _coingecko_coins_cache = response.json()
            _cache_timestamp = time.time()
            print(f"✅ Cached {len(_coingecko_coins_cache)} coins from CoinGecko")
            return _coingecko_coins_cache
        else:
            print(f"❌ Failed to fetch CoinGecko coins list: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching CoinGecko coins list: {e}")
        return None


def find_coingecko_by_symbol(symbol: str) -> str:
    """Find CoinGecko ID by matching symbol.
    
    优先使用本地 CMC mapping (binance_cmc_mapping.json)，如果没有再查询 CoinGecko API。
    
    Args:
        symbol: Binance symbol (e.g., BTC, 1000SATS, 1MBABYDOGE)
        
    Returns:
        CoinGecko ID if found, otherwise None
    """
    try:
        # 1. 优先从本地 CMC mapping 中查找
        cmc_mapping = load_cmc_mapping()
        if symbol in cmc_mapping:
            entry = cmc_mapping[symbol]
            # 如果有 cmc_slug，我们假设它与 CoinGecko ID 兼容（大多数情况下是一致的）
            # 注意：CMC slug 和 CoinGecko ID 不一定完全一样，但很多主流币是一致的
            # 这里我们优先使用 cmc_slug，如果需要可以后续维护一个 CMC->CoinGecko 的映射
            if entry.get('cmc_slug'):
                cmc_slug = entry['cmc_slug']
                print(f"✅ Found local CMC mapping: {symbol} -> {cmc_slug}")
                return cmc_slug
        
        # 2. 回退到 CoinGecko API 查找
        coins_list = get_coingecko_coins_list()
        if not coins_list:
            return None
        
        # Priority mapping for major cryptocurrencies
        major_coins = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum', 
            'BNB': 'binancecoin',
            'SOL': 'solana',
            'XRP': 'ripple',
            'ADA': 'cardano',
            'AVAX': 'avalanche-2',
            'DOT': 'polkadot',
            'MATIC': 'matic-network',
            'LINK': 'chainlink',
            'UNI': 'uniswap',
            'LTC': 'litecoin',
            'BCH': 'bitcoin-cash',
            'NEAR': 'near',
            'ATOM': 'cosmos',
            'FTM': 'fantom',
            'ALGO': 'algorand',
            'VET': 'vechain',
            'ICP': 'internet-computer',
            'HBAR': 'hedera-hashgraph',
            'ETC': 'ethereum-classic',
            'FIL': 'filecoin',
            'THETA': 'theta-token',
            'XLM': 'stellar',
            'TRX': 'tron',
            'AAVE': 'aave',
            'MKR': 'maker',
            'SNX': 'havven',
            'COMP': 'compound-governance-token',
            'YFI': 'yearn-finance'
        }
        
        # Check if it's a major coin first
        if symbol.upper() in major_coins:
            coin_id = major_coins[symbol.upper()]
            print(f"✅ Found major coin match: {symbol} -> {coin_id}")
            return coin_id
        
        # Handle special cases like 1000SATS, 1MBABYDOGE
        search_symbols = [symbol.upper()]
        
        # Add variations for special prefixes
        if symbol.upper().startswith('1000'):
            search_symbols.append(symbol[4:].upper())  # 1000SATS -> SATS
        elif symbol.upper().startswith('1M'):
            search_symbols.append(symbol[2:].upper())  # 1MBABYDOGE -> BABYDOGE
        
        # Try to find by symbol, prioritizing coins with higher market cap
        matches = []
        for search_symbol in search_symbols:
            for coin in coins_list:
                if coin['symbol'].upper() == search_symbol:
                    matches.append(coin)
        
        if matches:
            # For now, just take the first match
            # In the future, we could prioritize by market cap or other factors
            best_match = matches[0]
            print(f"✅ Found CoinGecko match: {symbol} -> {best_match['id']} (symbol: {best_match['symbol']})")
            return best_match['id']
                        
        print(f"❌ No CoinGecko match found for {symbol}")
        return None
        
    except Exception as e:
        print(f"❌ Error searching CoinGecko for {symbol}: {e}")
        return None


def fetch_enhanced_data(symbols: List[str]) -> List[TokenData]:
    """Fetch comprehensive data for given symbols."""
    overrides = load_overrides()
    results = []
    
    for symbol in symbols:
        print(f"\n=== Fetching data for {symbol} ===")
        token_data = TokenData(base=symbol)
        
        # Get CoinGecko ID from overrides or by symbol search
        coingecko_id = overrides.get(symbol.upper())
        if coingecko_id:
            token_data.coingecko_id = coingecko_id
            print(f"Using CoinGecko ID from overrides: {coingecko_id}")
        else:
            # Try to find by symbol
            coingecko_id = find_coingecko_by_symbol(symbol)
            if coingecko_id:
                token_data.coingecko_id = coingecko_id
        
        # Fetch spot data
        spot_data = fetch_spot_data(symbol)
        if spot_data:
            token_data.spot_price = spot_data.get("spot_price")
            token_data.spot_24h_change = spot_data.get("spot_24h_change")
            token_data.spot_volume_24h = spot_data.get("spot_volume_24h")
            if token_data.spot_price and token_data.spot_volume_24h:
                print(f"Spot: ${token_data.spot_price:.6f}, Vol: ${token_data.spot_volume_24h:,.0f}")
            else:
                print(f"Spot: ${token_data.spot_price or 'N/A'}, Vol: ${token_data.spot_volume_24h or 'N/A'}")
        
        # Fetch perp data
        perp_data = fetch_perp_data(symbol)
        if perp_data:
            token_data.perp_price = perp_data.get("perp_price")
            token_data.perp_24h_change = perp_data.get("perp_24h_change")
            token_data.perp_volume_24h = perp_data.get("perp_volume_24h")
            token_data.open_interest = perp_data.get("open_interest")
            token_data.funding_rate = perp_data.get("funding_rate")
            # 计算费率周期
            if token_data.funding_rate is not None:
                token_data.funding_cycle = calculate_funding_cycle(symbol)
            token_data.index_price = perp_data.get("index_price")
            token_data.mark_price = perp_data.get("mark_price")
            token_data.basis = perp_data.get("basis")
            token_data.index_composition = perp_data.get("index_composition")
            token_data.index_composition_summary = perp_data.get("index_composition_summary")
            # Convert open interest (in token units) to USD using perp price
            try:
                if token_data.open_interest and token_data.perp_price:
                    token_data.open_interest_usd = float(token_data.open_interest) * float(token_data.perp_price)
            except Exception:
                token_data.open_interest_usd = None
            
            if token_data.perp_price and token_data.perp_volume_24h:
                print(f"Perp: ${token_data.perp_price:.6f}, Vol: ${token_data.perp_volume_24h:,.0f}")
            else:
                print(f"Perp: ${token_data.perp_price or 'N/A'}, Vol: ${token_data.perp_volume_24h or 'N/A'}")
            if token_data.open_interest_usd:
                print(f"OI (USD): ${token_data.open_interest_usd:,.0f}")
            elif token_data.open_interest:
                print(f"OI: ${token_data.open_interest:,.0f}")
            else:
                print("OI: N/A")
            if token_data.funding_rate is not None:
                print(f"Funding Rate: {token_data.funding_rate:.6f} ({token_data.funding_rate*100:.4f}%)")
            if token_data.basis is not None:
                print(f"Basis: {token_data.basis:.6f} ({token_data.basis*100:.4f}%)")
            if token_data.index_composition_summary:
                print(f"Index Composition: {token_data.index_composition_summary}")
        
        # Fetch supply, ATH/ATL, logo and additional data from CoinGecko (static data)
        if coingecko_id:
            supply_data = fetch_coingecko_supply_data(coingecko_id)
            if supply_data:
                # Supply data
                token_data.circulating_supply = supply_data.get("circulating_supply")
                token_data.total_supply = supply_data.get("total_supply")
                token_data.max_supply = supply_data.get("max_supply")
                
                # Print supply info with None checks
                circ_supply = f"{token_data.circulating_supply:,.0f}" if token_data.circulating_supply else "N/A"
                total_supply = f"{token_data.total_supply:,.0f}" if token_data.total_supply else "N/A"
                print(f"Supply - Circulating: {circ_supply}, Total: {total_supply}")
                
                # Logo and additional info
                token_data.logo_url = supply_data.get("logo_url")
                token_data.genesis_date = supply_data.get("genesis_date")
                token_data.binance_listing_date = supply_data.get("binance_listing_date")
                
                if token_data.logo_url:
                    print(f"Logo: {token_data.logo_url}")
                if token_data.genesis_date:
                    print(f"Genesis: {token_data.genesis_date}")
                if token_data.binance_listing_date:
                    print(f"Binance: {token_data.binance_listing_date}")
                
                # ATH/ATL data
                token_data.ath_price = supply_data.get("ath_price")
                token_data.ath_date = supply_data.get("ath_date")
                token_data.ath_market_cap = supply_data.get("ath_market_cap")
                token_data.atl_price = supply_data.get("atl_price")
                token_data.atl_date = supply_data.get("atl_date")
                token_data.atl_market_cap = supply_data.get("atl_market_cap")
                
                if token_data.ath_price:
                    print(f"ATH: ${token_data.ath_price:.6f} ({token_data.ath_date})")
                if token_data.atl_price:
                    print(f"ATL: ${token_data.atl_price:.6f} ({token_data.atl_date})")
        
        # Calculate market caps
        token_data = calculate_market_caps(token_data)
        if token_data.market_cap_calc:
            print(f"Market Cap (calc): ${token_data.market_cap_calc:,.0f}")
        if token_data.fdv_calc:
            print(f"FDV (calc): ${token_data.fdv_calc:,.0f}")
        
        results.append(token_data)
        
        # Rate limiting for Binance APIs (more lenient)
        time.sleep(0.5)
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Enhanced Binance data fetcher")
    parser.add_argument("--test-symbols", 
                       default="BROCCOLI714,BROCCOLIF3B",
                       help="Comma-separated list of symbols to test")
    parser.add_argument("--output", "-o",
                       default=str(ROOT / "data" / "enhanced_test_data.json"),
                       help="Output file path")
    
    args = parser.parse_args()
    symbols = [s.strip().upper() for s in args.test_symbols.split(",")]
    
    print(f"Testing enhanced data collection with symbols: {symbols}")
    
    # Fetch data
    results = fetch_enhanced_data(symbols)
    
    # Convert to dict for JSON serialization
    output_data = [asdict(token) for token in results]
    
    # Save to file
    output_path = Path(args.output)
    output_path.parent.mkdir(exist_ok=True)
    
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== Results saved to {output_path} ===")
    print(f"Processed {len(results)} symbols")
    
    # Summary
    print("\n=== Summary ===")
    for token in results:
        print(f"{token.base}:")
        print(f"  - Spot: ${token.spot_price:.6f} (Vol: ${token.spot_volume_24h:,.0f})" if token.spot_price else "  - Spot: N/A")
        print(f"  - Perp: ${token.perp_price:.6f} (Vol: ${token.perp_volume_24h:,.0f})" if token.perp_price else "  - Perp: N/A")
        print(f"  - Funding: {token.funding_rate*100:.4f}%" if token.funding_rate else "  - Funding: N/A")
        print(f"  - Basis: {token.basis*100:.4f}%" if token.basis else "  - Basis: N/A")
        print(f"  - Market Cap: ${token.market_cap_calc:,.0f}" if token.market_cap_calc else "  - Market Cap: N/A")


if __name__ == "__main__":
    main()