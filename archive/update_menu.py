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
    print("  [1] 快速更新 - 只更新实时数据（价格、交易量、资金费率等）")
    print("      • 速度最快，不调用 CMC API，不更新静态字段")
    print("      • 推荐日常使用（每1-4小时）")
    print()
    print("  [2] 更新静态字段 - 实时数据 + Funding Cycle + Categories + Index Composition")
    print("      • 不调用 CMC API，速度较快")
    print("      • 推荐不定期运行（当有新币上市或分类变化时）")
    print()
    print("  [3] 完整更新 - 实时数据 + 供应量 + 静态字段")
    print("      • 调用 CMC API，速度较慢")
    print("      • 推荐每天运行1次或有需要时使用")
    print()
    print("  [4] 指定币种快速更新 - 只更新实时数据")
    print("      • 只更新指定币种的实时数据")
    print()
    print("  [5] 指定币种 + 静态字段")
    print("      • 更新指定币种 + Funding Cycle + Categories + Index Composition")
    print()
    print("  [6] 指定币种 + 完整元数据")
    print("      • 更新指定币种 + 供应量 + 静态字段")
    print()
    print("  [7] ⚡️ 极速更新 - 并行处理（快12倍！）")
    print("      • 使用多线程并行获取数据")
    print("      • 3小时 → 15分钟")
    print()
    print("  [8] ⚡️ 极速更新 + 静态字段")
    print("      • 并行处理 + Funding Cycle + Categories + Index Composition")
    print()
    print("  [9] ⚡️ 极速完整更新")
    print("      • 并行处理 + 供应量 + 静态字段")
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
        
        choice = input("请选择操作 [0-9]: ").strip()
        
        if choice == '0':
            print("\n👋 再见！")
            sys.exit(0)
        
        elif choice == '1':
            # 快速更新 - 只更新实时数据
            cmd = f"cd {script_dir} && python3 scripts/update_binance_trading_data.py"
            if run_update(cmd, "快速更新所有币种（实时数据）"):
                input("\n按 Enter 键继续...")
        
        elif choice == '2':
            # 更新静态字段
            cmd = f"cd {script_dir} && python3 scripts/update_binance_trading_data.py --update-static-fields"
            if run_update(cmd, "更新所有币种 + 静态字段"):
                input("\n按 Enter 键继续...")
        
        elif choice == '3':
            # 完整更新
            cmd = f"cd {script_dir} && python3 scripts/update_binance_trading_data.py --update-metadata"
            if run_update(cmd, "完整更新所有币种（实时数据 + 供应量 + 静态字段）"):
                input("\n按 Enter 键继续...")
        
        elif choice == '4':
            # 指定币种更新
            symbols = get_symbols_input()
            if symbols:
                cmd = f"cd {script_dir} && python3 scripts/update_binance_trading_data.py {symbols}"
                if run_update(cmd, f"快速更新币种：{symbols}"):
                    input("\n按 Enter 键继续...")
        
        elif choice == '5':
            # 指定币种 + 静态字段
            symbols = get_symbols_input()
            if symbols:
                cmd = f"cd {script_dir} && python3 scripts/update_binance_trading_data.py --update-static-fields {symbols}"
                if run_update(cmd, f"更新币种 + 静态字段：{symbols}"):
                    input("\n按 Enter 键继续...")
        
        elif choice == '6':
            # 指定币种 + 完整元数据
            symbols = get_symbols_input()
            if symbols:
                cmd = f"cd {script_dir} && python3 scripts/update_binance_trading_data.py --update-metadata {symbols}"
                if run_update(cmd, f"完整更新币种：{symbols}"):
                    input("\n按 Enter 键继续...")
        
        elif choice == '7':
            # 极速更新
            cmd = f"cd {script_dir} && python3 scripts/update_binance_trading_data_fast.py"
            if run_update(cmd, "⚡️ 极速更新所有币种（并行处理，快12倍！）"):
                input("\n按 Enter 键继续...")
        
        elif choice == '8':
            # 极速更新 + 静态字段
            cmd = f"cd {script_dir} && python3 scripts/update_binance_trading_data_fast.py --update-static-fields"
            if run_update(cmd, "⚡️ 极速更新 + 静态字段（并行处理）"):
                input("\n按 Enter 键继续...")
        
        elif choice == '9':
            # 极速完整更新
            cmd = f"cd {script_dir} && python3 scripts/update_binance_trading_data_fast.py --update-metadata"
            if run_update(cmd, "⚡️ 极速完整更新（并行处理 + 供应量）"):
                input("\n按 Enter 键继续...")
        
        else:
            print("\n❌ 无效选项，请输入 0-9")
            input("\n按 Enter 键继续...")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 再见！")
        sys.exit(0)
