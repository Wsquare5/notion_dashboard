#!/bin/bash
# 完整更新 - 包含供应量等元数据（推荐每天运行1次）
# 用法: ./full_update.sh

echo "🚀 开始完整更新（包含元数据）..."
echo "⏰ $(date)"
echo ""

cd "$(dirname "$0")"
python3 update.py --workers 20 --update-metadata 2>&1 | tee logs/update_full_$(date +%Y%m%d_%H%M%S).log

echo ""
echo "✅ 完整更新完成！"
echo "⏰ $(date)"
