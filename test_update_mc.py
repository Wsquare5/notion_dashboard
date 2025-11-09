#!/usr/bin/env python3
"""Test MC calculation for specific symbols"""

import json
import requests
import sys

def load_config():
    with open('config.json', 'r') as f:
        config = json.load(f)
    return config['notion']['api_key'], config['notion']['database_id']

def load_mapping():
    with open('binance_cmc_mapping.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['mapping']

def get_binance_data(symbol):
    """Get spot and perp data from Binance"""
    spot_price = None
    perp_price = None
    
    # Try spot
    try:
        resp = requests.get(f'https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT', timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            spot_price = float(data['lastPrice'])
    except:
        pass
    
    # Try perp
    try:
        resp = requests.get(f'https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}USDT', timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            perp_price = float(data['lastPrice'])
    except:
        pass
    
    return spot_price, perp_price

def get_notion_page(symbol, api_key, database_id):
    """Get page from Notion"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json'
    }
    
    url = f'https://api.notion.com/v1/databases/{database_id}/query'
    payload = {
        'filter': {
            'property': 'Symbol',
            'title': {'equals': symbol}
        }
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    results = response.json().get('results', [])
    
    return results[0] if results else None

def update_notion_page(page_id, properties, api_key):
    """Update Notion page"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json'
    }
    
    url = f'https://api.notion.com/v1/pages/{page_id}'
    payload = {'properties': properties}
    
    response = requests.patch(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()

def main():
    symbols = ['STEEM', 'KNC', 'ESPORTS', 'EPT', 'CGPT']
    
    print("Loading config and mapping...")
    api_key, database_id = load_config()
    mapping = load_mapping()
    
    print(f"\nTesting MC calculation for {len(symbols)} symbols\n")
    print("=" * 80)
    
    for symbol in symbols:
        print(f"\n🔍 {symbol}")
        print("-" * 80)
        
        try:
            # Get Notion page
            print("  [1] Fetching Notion page...")
            page = get_notion_page(symbol, api_key, database_id)
            if not page:
                print(f"  ❌ Page not found in Notion")
                continue
            
            props = page['properties']
            circ = props.get('Circulating Supply', {}).get('number')
            current_mc = props.get('MC', {}).get('number')
            
            print(f"  [2] Current data:")
            print(f"      - Circulating Supply: {circ}")
            print(f"      - Current MC: {current_mc}")
            
            # Get Binance prices
            print("  [3] Fetching Binance prices...")
            spot_price, perp_price = get_binance_data(symbol)
            print(f"      - Spot Price: {spot_price}")
            print(f"      - Perp Price: {perp_price}")
            
            # Calculate MC
            if circ and circ > 0:
                price = perp_price if perp_price else spot_price
                if price:
                    new_mc = circ * price
                    print(f"  [4] Calculated MC: {new_mc:,.2f}")
                    
                    # Check if multiplier exists
                    multiplier = mapping.get(symbol, {}).get('multiplier', 1)
                    if multiplier > 1:
                        new_mc = new_mc / multiplier
                        print(f"      (divided by multiplier {multiplier})")
                    
                    # Update Notion
                    print(f"  [5] Updating Notion...")
                    properties = {
                        'MC': {'number': round(new_mc, 2)}
                    }
                    
                    if spot_price:
                        properties['Spot Price'] = {'number': spot_price}
                    if perp_price:
                        properties['Perp Price'] = {'number': perp_price}
                    
                    update_notion_page(page['id'], properties, api_key)
                    print(f"  ✅ Updated! MC: {new_mc:,.2f}")
                else:
                    print(f"  ⚠️  No price available")
            else:
                print(f"  ⚠️  No circulating supply")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        print()
    
    print("=" * 80)
    print("\n✅ Test complete!")

if __name__ == '__main__':
    main()
