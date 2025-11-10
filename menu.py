#!/usr/bin/env python3
"""
Interactive menu for updating Binance trading data to Notion
"""

import subprocess
import sys
import os

def print_menu():
    """Print the main menu"""
    print("\n" + "="*80)
    print("🚀 Binance Trading Data Update Menu")
    print("="*80)
    print("\n请选择更新模式：\n")
    print("  [1] ⚡️ 更新 Binance 基本交易数据")
    print("      • 价格、交易量、资金费率等实时数据")
    print("      • 极速并行处理（8分钟完成）")
    print("      • 推荐日常使用")
    print()
    print("  [2] ⚡️ 更新 Binance + 静态字段")
    print("      • 基本交易数据 + Funding Cycle + Categories + Index Composition")
    print("      • 不调用 CMC API，速度快")
    print("      • 推荐不定期运行（有新币上市或分类变化时）")
    print()
    print("  [3] ⚡️ 更新完整的 Binance + 静态字段 + CMC 供应量")
    print("      • 基本交易数据 + 静态字段 + CMC 供应量")
    print("      • 调用 CMC API，最完整的数据")
    print("      • 推荐每天运行1次")
    print()
    print("  [4] 🎯 指定币种完整更新")
    print("      • 输入币种符号，完整更新指定币种")
    print("      • 包含实时数据 + 静态字段 + CMC 供应量")
    print()
    print("  [5] 📊 每日行情总结")
    print("      • 生成涨跌幅前5名总结并写入 Notion")
    print("      • 只统计有合约价格的币种")
    print()
    print("  [0] 退出")
    print("\n" + "="*80)

def run_update(command, description):
    """Run update command with description"""
    print(f"\n🔄 {description}")
    print(f"📝 执行命令: {command}\n")
    print("="*80)
    
    try:
        result = subprocess.run(command, shell=True, check=True)
        print("\n" + "="*80)
        print("✅ 更新完成！")
        return True
    except subprocess.CalledProcessError as e:
        print("\n" + "="*80)
        print(f"❌ 更新失败，错误码: {e.returncode}")
        return False
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        return False

def get_symbols_input():
    """Get symbol list from user input"""
    print("\n请输入币种符号（用空格分隔，例如：BTC ETH SOL）")
    symbols = input("币种符号: ").strip().upper()
    if not symbols:
        print("❌ 未输入币种")
        return None
    return symbols

def main():
    """Main menu loop"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    while True:
        print_menu()
        
        choice = input("请选择操作 [0-5]: ").strip().upper()
        
        if choice == '0':
            print("\n👋 再见！")
            sys.exit(0)
        
        elif choice == '1':
            # 更新 Binance 基本交易数据（极速）
            cmd = f"cd {script_dir} && python3 update.py"
            if run_update(cmd, "⚡️ 更新 Binance 基本交易数据"):
                input("\n按 Enter 键继续...")
        
        elif choice == '2':
            # 更新 Binance + 静态字段（极速）
            cmd = f"cd {script_dir} && python3 update.py --update-static-fields"
            if run_update(cmd, "⚡️ 更新 Binance + 静态字段"):
                input("\n按 Enter 键继续...")
        
        elif choice == '3':
            # 完整更新（极速 + CMC）
            cmd = f"cd {script_dir} && python3 update.py --update-metadata"
            if run_update(cmd, "⚡️ 更新完整的 Binance + 静态字段 + CMC 供应量"):
                input("\n按 Enter 键继续...")
        
        elif choice == '4':
            # 指定币种完整更新
            symbols = get_symbols_input()
            if symbols:
                cmd = f"cd {script_dir} && python3 update.py --update-metadata {symbols}"
                if run_update(cmd, f"🎯 指定币种完整更新：{symbols}"):
                    input("\n按 Enter 键继续...")
        
        elif choice == '5':
            # 每日行情总结
            cmd = f"cd {script_dir} && python3 scripts/daily_market_summary.py"
            if run_update(cmd, "📊 生成每日行情总结"):
                input("\n按 Enter 键继续...")
        
        else:
            print("\n❌ 无效选项，请输入 0-5")
            input("\n按 Enter 键继续...")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 再见！")
        sys.exit(0)
