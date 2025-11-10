#!/usr/bin/env python3
"""
测试并行Notion更新的性能 - 使用50个币种
"""
import subprocess
import time

# Top 50 coins by market cap
test_symbols = [
    'BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'AVAX', 'DOGE', 'DOT', 'MATIC',
    'LINK', 'UNI', 'ATOM', 'LTC', 'FIL', 'ETC', 'NEAR', 'AAVE', 'ARB', 'OP',
    'SUI', 'APT', 'INJ', 'TIA', 'SEI', 'HBAR', 'BCH', 'STX', 'RUNE', 'IMX',
    'RENDER', 'FET', 'GRT', 'ALGO', 'FLOW', 'ICP', 'MANA', 'SAND', 'AXS', 'ENJ',
    'GALA', 'CHZ', 'THETA', 'FTM', 'XTZ', 'EOS', 'KAVA', 'ONE', 'ZIL', 'CELO'
]

print("="*80)
print("⚡ 并行Notion更新性能测试")
print("="*80)
print(f"测试币种数：{len(test_symbols)}")
print(f"Workers: 10")
print("="*80 + "\n")

start = time.time()

cmd = [
    'python3',
    'scripts/update_binance_trading_data_fast.py',
    '--workers', '10'
] + test_symbols

result = subprocess.run(cmd, capture_output=True, text=True, cwd='/Users/wanjinwoo/Desktop/Work/trading/Binance')

elapsed = time.time() - start

print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

print("\n" + "="*80)
print("📊 性能统计")
print("="*80)
print(f"总耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
print(f"币种数: {len(test_symbols)}")
print(f"平均速度: {len(test_symbols)/elapsed:.2f} 币种/秒")
print(f"估算534币种耗时: {534/(len(test_symbols)/elapsed):.1f}秒 ({534/(len(test_symbols)/elapsed)/60:.1f}分钟)")
print("="*80)

# 对比
print("\n💡 性能对比:")
print("  旧版本（串行）: 96分钟 (0.09 symbols/s)")
print(f"  新版本（并行）: 预计~{534/(len(test_symbols)/elapsed)/60:.1f}分钟 ({len(test_symbols)/elapsed:.2f} symbols/s)")
print(f"  加速比: {96/(534/(len(test_symbols)/elapsed)/60):.1f}x")
print("="*80)
