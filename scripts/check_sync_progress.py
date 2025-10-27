#!/usr/bin/env python3
"""Check sync progress from log file"""
import sys
import time
from pathlib import Path

log_file = Path(__file__).parent.parent / 'sync_all.log'

if not log_file.exists():
    print("❌ Log file not found")
    sys.exit(1)

content = log_file.read_text()
lines = content.strip().split('\n')

# Count updates and errors
updated = sum(1 for line in lines if '✅ Updated:' in line)
created = sum(1 for line in lines if '✅ Created:' in line)
failed = sum(1 for line in lines if '❌ Failed:' in line)
total = updated + created

print(f"📊 Sync Progress:")
print(f"  ✅ Updated: {updated}")
print(f"  ➕ Created: {created}")
print(f"  ❌ Failed: {failed}")
print(f"  📈 Total: {total}")

# Show last few lines
print(f"\n📝 Last 10 operations:")
relevant_lines = [l for l in lines if any(x in l for x in ['✅ Updated:', '✅ Created:', '❌ Failed:', '✨ Sync complete'])]
for line in relevant_lines[-10:]:
    print(f"  {line}")
