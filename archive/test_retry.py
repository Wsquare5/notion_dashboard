#!/usr/bin/env python3
"""
测试重试机制 - 使用少量币种验证重试逻辑
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scripts.update_binance_trading_data_fast import parallel_fetch_trading_data

# Test with a few symbols including some that might fail
test_symbols = ['BTC', 'ETH', 'SOL', '1000BONK', 'AGLD', 'APR', 'INVALID_SYMBOL']

spot_and_perp = {'BTC', 'ETH', 'SOL'}
perp_only = {'1000BONK', 'AGLD', 'APR'}

print("Testing retry mechanism with:")
print(f"  Valid symbols: BTC, ETH, SOL, 1000BONK")
print(f"  Possibly failed: AGLD, APR")
print(f"  Invalid: INVALID_SYMBOL")
print("\n" + "="*80 + "\n")

# Test with 5 workers and max 2 retries
results = parallel_fetch_trading_data(
    symbols=test_symbols,
    spot_and_perp=spot_and_perp,
    perp_only=perp_only,
    max_workers=5,
    max_retries=2
)

print("\n" + "="*80)
print("Results:")
for symbol, (spot_data, perp_data) in results.items():
    if spot_data or perp_data:
        spot_price = spot_data.get('spot_price') if spot_data else None
        perp_price = perp_data.get('perp_price') if perp_data else None
        print(f"  ✅ {symbol:15s}: Spot=${spot_price or 'N/A'} Perp=${perp_price or 'N/A'}")
    else:
        print(f"  ❌ {symbol:15s}: No data")
print("="*80)
