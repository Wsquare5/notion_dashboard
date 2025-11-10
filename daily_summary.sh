#!/bin/bash
# 每日行情总结 - 快速运行脚本
# 用法: ./daily_summary.sh

echo "📊 开始生成每日行情总结..."
echo "⏰ $(date)"
echo ""

cd "$(dirname "$0")"
python3 scripts/daily_market_summary.py

echo ""
echo "✅ 完成！"
echo "⏰ $(date)"
