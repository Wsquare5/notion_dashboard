#!/usr/bin/env python3
"""Inspect Notion database schema"""

import requests
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTION_CONFIG_FILE = ROOT / 'config.json'

def load_notion_config():
    with NOTION_CONFIG_FILE.open('r') as f:
        return json.load(f)

def inspect_database():
    config = load_notion_config()
    
    headers = {
        'Authorization': f'Bearer {config["notion"]["api_key"]}',
        'Notion-Version': '2022-06-28'
    }
    
    url = f'https://api.notion.com/v1/databases/{config["notion"]["database_id"]}'
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    db_info = response.json()
    
    print("📊 Notion Database Schema:\n")
    print(f"Title: {db_info.get('title', [{}])[0].get('text', {}).get('content', 'N/A')}\n")
    
    properties = db_info.get('properties', {})
    
    print(f"Properties ({len(properties)} total):\n")
    for prop_name, prop_data in properties.items():
        prop_type = prop_data.get('type', 'unknown')
        print(f"  • {prop_name}: {prop_type}")

if __name__ == '__main__':
    inspect_database()
