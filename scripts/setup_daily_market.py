#!/usr/bin/env python3
"""
每日行情功能设置向导
帮助你快速配置每日行情数据库
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "config" / "daily_market_config.json"

print("=" * 80)
print("📊 每日行情功能 - 设置向导")
print("=" * 80)
print()

print("请回答以下问题来完成配置：\n")

# 获取数据库 ID
print("1️⃣  每日行情数据库 ID")
print("   提示：在 Notion 中打开你的'每日行情'数据库")
print("   从 URL 中复制数据库 ID")
print("   格式类似：https://notion.so/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
print()
database_id = input("   请输入数据库 ID: ").strip()

if not database_id:
    print("\n❌ 数据库 ID 不能为空！")
    exit(1)

# 确认字段
print("\n2️⃣  请确认你的数据库包含以下字段：")
print("   ✅ Date（日期类型）")
print("   ✅ 涨跌幅（文本类型）")
print()
confirm = input("   确认以上字段已创建？(y/n): ").strip().lower()

if confirm != 'y':
    print("\n⚠️  请先在 Notion 中创建这些字段，然后重新运行此脚本")
    exit(0)

# 保存配置
config = {
    "database_id": database_id,
    "description": "每日行情数据库配置",
    "update_times": ["09:00", "21:00"],
    "top_n": 5
}

with CONFIG_FILE.open('w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print("\n" + "=" * 80)
print("✅ 配置已保存！")
print("=" * 80)
print(f"\n配置文件：{CONFIG_FILE}")
print("\n配置内容：")
print(json.dumps(config, indent=2, ensure_ascii=False))
print("\n" + "=" * 80)
print("🚀 下一步：运行测试")
print("=" * 80)
print("\n运行以下命令测试功能：")
print(f"  python3 scripts/daily_market_summary.py")
print()
print("如果测试成功，可以设置定时任务：")
print("  每天早上 9:00 和晚上 9:00 自动运行")
print()
