#!/bin/bash
# 快速更新 - 只更新交易数据（推荐每 4-8 小时运行）
# 用法: ./quick_update.sh

echo "🚀 开始快速更新..."
echo "⏰ $(date)"
echo ""

cd "$(dirname "$0")"
python3 update.py --workers 20 2>&1 | tee logs/update_$(date +%Y%m%d_%H%M%S).log

echo ""
echo "✅ 更新完成！"
echo "⏰ $(date)"
