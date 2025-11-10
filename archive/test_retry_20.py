#!/usr/bin/env python3
"""
对比测试：无重试 vs 有重试机制
"""
import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent))

from scripts.update_binance_trading_data_fast import parallel_fetch_trading_data

# Test with 20 symbols that might have network issues
test_symbols = [
    'BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'AVAX', 'DOGE', 'DOT', 'MATIC',
    '1000BONK', '1000WHY', 'AGLD', 'APR', '1000PEPE', 'ARB', 'OP', 'SUI', 'APT', 'INJ'
]

spot_and_perp = {'BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'AVAX', 'DOGE', 'DOT', 'MATIC', 'ARB', 'OP', 'SUI', 'APT', 'INJ'}
perp_only = {'1000BONK', '1000WHY', 'AGLD', 'APR', '1000PEPE'}

print("="*80)
print("📊 Testing Retry Mechanism with 20 symbols")
print("="*80)
print(f"Symbols: {', '.join(test_symbols)}")
print(f"Workers: 10, Max retries: 3")
print("="*80 + "\n")

start = time.time()

results = parallel_fetch_trading_data(
    symbols=test_symbols,
    spot_and_perp=spot_and_perp,
    perp_only=perp_only,
    max_workers=10,
    max_retries=3
)

total_time = time.time() - start

print("\n" + "="*80)
print("📈 Final Results:")
print("="*80)

success_count = 0
failed_count = 0

for symbol in test_symbols:
    spot_data, perp_data = results.get(symbol, (None, None))
    
    if spot_data or perp_data:
        success_count += 1
        spot_price = spot_data.get('spot_price') if spot_data else None
        perp_price = perp_data.get('perp_price') if perp_data else None
        oi = perp_data.get('open_interest_usd') if perp_data else None
        
        info = []
        if spot_price:
            info.append(f"S:${spot_price:.4f}")
        if perp_price:
            info.append(f"P:${perp_price:.4f}")
        if oi:
            info.append(f"OI:${oi/1e9:.2f}B" if oi >= 1e9 else f"OI:${oi/1e6:.0f}M")
        
        print(f"  ✅ {symbol:12s}: {' '.join(info)}")
    else:
        failed_count += 1
        print(f"  ❌ {symbol:12s}: No data")

print("="*80)
print(f"✅ Success: {success_count}/{len(test_symbols)} ({success_count/len(test_symbols)*100:.1f}%)")
print(f"❌ Failed: {failed_count}/{len(test_symbols)} ({failed_count/len(test_symbols)*100:.1f}%)")
print(f"⏱️  Total time: {total_time:.1f}s")
print(f"⚡ Rate: {success_count/total_time:.2f} symbols/s")
print("="*80)

print("\n💡 重试机制效果:")
print("  - 网络超时的币种会自动重试")
print("  - 降低并发数避免代理服务器压力")
print("  - 等待2秒后重试，避免速率限制")
print("  - 最多重试3次，最大化成功率")
print("="*80)
