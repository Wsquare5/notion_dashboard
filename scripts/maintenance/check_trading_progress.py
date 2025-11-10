#!/usr/bin/env python3
"""Check trading data update progress"""
import sys
from pathlib import Path

log_file = Path(__file__).parent.parent / 'update_trading.log'

if not log_file.exists():
    print("❌ Log file not found")
    sys.exit(1)

content = log_file.read_text()
lines = content.strip().split('\n')

# Count results
success = sum(1 for line in lines if '✅' in line and ('Spot:' in line or 'Perp:' in line))
skipped = sum(1 for line in lines if '⚠️  Page not found' in line or '⚠️  No data available' in line)
failed = sum(1 for line in lines if '❌ Failed:' in line)

print(f"📊 Trading Data Update Progress:")
print(f"  ✅ Success: {success}")
print(f"  ⚠️  Skipped: {skipped}")
print(f"  ❌ Failed: {failed}")
print(f"  📈 Total processed: {success + skipped + failed}")

# Show last 10 operations
print(f"\n📝 Last 10 operations:")
symbol_lines = [l for l in lines if l.startswith('[')]
for line in symbol_lines[-10:]:
    print(f"  {line}")
