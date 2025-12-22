#!/usr/bin/env python3
"""
Interactive menu for updating Binance trading data to Notion (WebSocket版)
"""

import subprocess
import sys
import os
from pathlib import Path

def print_menu():
    """Print the main menu"""
    print("\n" + "="*80)
    print("🚀 Binance Trading Data Update Menu")
    print("="*80)
    print("\n请选择更新模式：\n")
    print("  [1] ⚡️ 更新 Binance 基本交易数据（推荐日常使用）")
    print("      • 价格、交易量、资金费率等实时数据")
    print("      • WebSocket实时采集，无封禁风险")
    print("      • 约5-6分钟完成")
    print()
    print("  [2] 🎯 指定币种更新")
    print("      • 输入币种符号，更新指定币种")
    print("      • WebSocket实时数据")
    print()
    print("  [3] 📊 每日行情总结")
    print("      • 生成涨跌幅前5名总结并写入 Notion")
    print("      • 只统计有合约价格的币种")
    print()
    print("  [0] 退出")
    print("\n" + "="*80)
    print("💡 提示：已切换到WebSocket方式，无速率限制！")
    print("="*80)

def run_command(command, description):
    """Run command with description"""
    print(f"\n🔄 {description}")
    print(f"📝 执行命令: {command}\n")
    print("="*80)
    
    try:
        result = subprocess.run(command, shell=True, check=True)
        print("\n" + "="*80)
        print("✅ 完成！")
        return True
    except subprocess.CalledProcessError as e:
        print("\n" + "="*80)
        print(f"❌ 失败，错误码: {e.returncode}")
        return False
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        return False

def update_all_coins(script_dir):
    """更新所有币种 - WebSocket方式"""
    print("\n🌐 开始完整更新流程...")
    print("步骤 1/2: 收集 WebSocket 数据（所有618个币种）")
    
    cmd1 = f"cd {script_dir} && python3 collect_websocket_data.py"
    if run_command(cmd1, "📡 收集实时数据"):
        print("\n步骤 2/2: 更新 Notion")
        cmd2 = f"cd {script_dir} && python3 update_from_websocket.py"
        if run_command(cmd2, "📝 更新 Notion 数据库"):
            print("\n✅ 完整更新流程完成！")
            return True
    return False

def update_specific_coins(script_dir, symbols):
    """更新指定币种 - WebSocket方式"""
    print(f"\n🎯 开始更新指定币种：{symbols}")
    print("步骤 1/2: 收集指定币种的数据")
    
    cmd1 = f"cd {script_dir} && python3 collect_websocket_data.py {symbols}"
    if run_command(cmd1, f"📡 收集 {symbols} 的实时数据"):
        print("\n步骤 2/2: 更新 Notion")
        cmd2 = f"cd {script_dir} && python3 update_from_websocket.py {symbols}"
        if run_command(cmd2, f"📝 更新 {symbols} 到 Notion"):
            print("\n✅ 指定币种更新完成！")
            return True
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
        
        choice = input("请选择操作 [0-3]: ").strip()
        
        if choice == '0':
            print("\n👋 再见！")
            sys.exit(0)
        
        elif choice == '1':
            # 更新所有币种（WebSocket）
            if update_all_coins(script_dir):
                input("\n按 Enter 键继续...")
        
        elif choice == '2':
            # 指定币种更新（WebSocket）
            symbols = get_symbols_input()
            if symbols:
                if update_specific_coins(script_dir, symbols):
                    input("\n按 Enter 键继续...")
        
        elif choice == '3':
            # 每日行情总结
            cmd = f"cd {script_dir} && python3 scripts/daily_market_summary.py"
            if run_command(cmd, "📊 生成每日行情总结"):
                input("\n按 Enter 键继续...")
        
        else:
            print("\n❌ 无效选项，请输入 0-3")
            input("\n按 Enter 键继续...")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 再见！")
        sys.exit(0)
