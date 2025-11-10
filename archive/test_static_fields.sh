#!/bin/bash
# 测试新的静态字段更新功能

echo "==================================="
echo "测试静态字段更新功能"
echo "==================================="
echo ""

# 测试 1: 帮助信息
echo "📝 测试 1: 查看帮助信息"
python3 scripts/update_binance_trading_data.py --help | grep -A 2 "update-static-fields"
echo ""

# 测试 2: 语法检查
echo "✅ 测试 2: 语法检查"
python3 -m py_compile scripts/update_binance_trading_data.py && echo "  ✓ update_binance_trading_data.py 语法正确"
python3 -m py_compile update_menu.py && echo "  ✓ update_menu.py 语法正确"
echo ""

# 测试 3: 菜单显示
echo "🎯 测试 3: 交互式菜单"
echo "0" | python3 update_menu.py | grep -A 2 "静态字段"
echo ""

# 测试 4: 测试单个币种静态字段更新（实际测试，但只选一个币种）
echo "🔍 测试 4: 测试单个币种的静态字段更新"
echo "   运行命令: python3 scripts/update_binance_trading_data.py --update-static-fields BTC"
echo "   （按 Ctrl+C 取消或等待完成）"
echo ""
read -p "是否执行实际测试？(y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    python3 scripts/update_binance_trading_data.py --update-static-fields BTC
else
    echo "   跳过实际测试"
fi

echo ""
echo "==================================="
echo "✅ 所有测试完成"
echo "==================================="
