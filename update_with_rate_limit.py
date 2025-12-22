#!/usr/bin/env python3
"""
带速率限制的更新脚本
解决 Binance API 封禁问题

Binance REST API 限制:
- IP 限制: 2400 请求权重/分钟
- ticker/24hr: 40 权重
- premiumIndex: 10 权重
- openInterest: 1 权重

策略: 分批处理，每批 40 个币种，每批之间等待 90 秒
"""

import sys
import json
import time
from pathlib import Path

# Load configuration
BASE_DIR = Path(__file__).parent
config_file = BASE_DIR / 'config' / 'binance_cmc_mapping.json'

with open(config_file, 'r') as f:
    data = json.load(f)
    if 'mapping' in data:
        symbols = list(data['mapping'].keys())
    else:
        symbols = list(data.keys())

print(f"📊 总共 {len(symbols)} 个币种")
print()

# 分批参数
BATCH_SIZE = 40  # 每批处理的币种数
BATCH_DELAY = 90  # 批次间隔（秒）

# 计算批次
num_batches = (len(symbols) + BATCH_SIZE - 1) // BATCH_SIZE
print(f"📦 分成 {num_batches} 批，每批 {BATCH_SIZE} 个币种")
print(f"⏱️  每批间隔 {BATCH_DELAY} 秒")
print(f"⏱️  预计总耗时: {num_batches * BATCH_DELAY / 60:.1f} 分钟")
print()

# 询问确认
response = input("是否继续？(y/n): ").strip().lower()
if response != 'y':
    print("已取消")
    sys.exit(0)

print()
print("=" * 80)
print("开始分批更新")
print("=" * 80)

for batch_num in range(num_batches):
    start_idx = batch_num * BATCH_SIZE
    end_idx = min(start_idx + BATCH_SIZE, len(symbols))
    batch_symbols = symbols[start_idx:end_idx]
    
    print(f"\n🔄 批次 {batch_num + 1}/{num_batches}: 处理 {len(batch_symbols)} 个币种")
    print(f"   币种: {', '.join(batch_symbols[:10])}{' ...' if len(batch_symbols) > 10 else ''}")
    
    # 构建命令
    symbols_str = ' '.join(batch_symbols)
    cmd = f'python3 update.py {symbols_str}'
    
    print(f"   执行: python3 update.py [批次{batch_num + 1}的币种]")
    
    # 执行更新
    import subprocess
    result = subprocess.run(cmd, shell=True, cwd=str(BASE_DIR))
    
    if result.returncode != 0:
        print(f"   ⚠️  批次 {batch_num + 1} 执行失败")
    else:
        print(f"   ✅ 批次 {batch_num + 1} 完成")
    
    # 等待下一批（除了最后一批）
    if batch_num < num_batches - 1:
        print(f"   ⏳ 等待 {BATCH_DELAY} 秒...")
        time.sleep(BATCH_DELAY)

print()
print("=" * 80)
print("✅ 所有批次完成！")
print("=" * 80)
