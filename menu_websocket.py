#!/usr/bin/env python3
"""
Interactive menu for updating Binance trading data to Notion (WebSocket Version)
完全避免 Binance REST API 封禁问题
"""

import subprocess
import sys
import os
from pathlib import Path

def print_menu():
    """Print the main menu"""
    print("\n" + "="*80)
    print("🚀 Binance Trading Data Update Menu (WebSocket版)")
    print("="*80)
    print("\n请选择更新模式：\n")
    print("  [1] ⚡️ 快速更新（推荐日常使用）")
    print("      • 使用已有的 WebSocket 数据更新 Notion")
    print("      • 适用于刚收集完数据后的更新")
    print("      • 耗时：~1分钟")
    print()
    print("  [2] 🔄 同步新币种并完整更新（推荐每周一次）")
    print("      • 从币安获取最新上市的币种")
    print("      • 收集所有币种的实时数据（WebSocket）")
    print("      • 自动更新到 Notion")
    print("      • 耗时：~10分钟")
    print()
    print("  [3] 🌐 收集数据并更新（不含新币）")
    print("      • 收集当前列表内所有币种的实时数据（WebSocket）")
    print("      • 自动更新到 Notion")
    print("      • 耗时：~6分钟")
    print()
    print("  [4] 🎯 指定币种更新")
    print("      • 输入币种符号，更新指定币种")
    print("      • 先收集数据，再更新 Notion")
    print()
    print("  [5] 📊 仅收集 WebSocket 数据（不更新Notion）")
    print("      • 收集所有币种的实时数据")
    print("      • 保存到 data/websocket_collected_data.json")
    print()
    print("  [6] 📈 每日行情总结")
    print("      • 生成涨跌幅前5名总结并写入 Notion")
    print("      • 需要先收集 WebSocket 数据")
    print()
    print("  [0] 退出")
    print("\n" + "="*80)
    print("💡 提示：WebSocket方式无速率限制，可以随时运行！")
    print("="*80)

def run_command(command, description):
    """Run command with description"""
    print(f"\n🔄 {description}")
    print(f"📝 执行命令: {command}\n")
    print("="*80)
    
    try:
        result = subprocess.run(command, shell=True, check=True)
        print("\n" + "="*80)
        print("✅ 操作完成！")
        return True
    except subprocess.CalledProcessError as e:
        print("\n" + "="*80)
        print(f"❌ 操作失败，错误码: {e.returncode}")
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

def check_websocket_data_exists(script_dir):
    """Check if WebSocket data file exists"""
    data_file = Path(script_dir) / 'data' / 'websocket_collected_data.json'
    return data_file.exists()

def main():
    """Main menu loop"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    while True:
        print_menu()
        
        choice = input("请选择操作 [0-6]: ").strip()
        
        if choice == '0':
            print("\n👋 再见！")
            sys.exit(0)
        
        elif choice == '1':
            # 快速更新（使用已有数据）
            if not check_websocket_data_exists(script_dir):
                print("\n⚠️  未找到 WebSocket 数据文件")
                print("请先选择选项 [2], [3] 或 [5] 收集数据")
                input("\n按 Enter 键继续...")
                continue
            
            cmd = f"cd {script_dir} && python3 update_from_websocket.py"
            run_command(cmd, "使用本地数据更新 Notion...")

        elif choice == '2':
            # 同步新币种并完整更新
            # 1. 运行 update.py 获取最新币种列表
            cmd1 = f"cd {script_dir} && python3 update.py"
            if not run_command(cmd1, "步骤 1/3: 从币安同步最新币种列表..."):
                input("\n按 Enter 键继续...")
                continue
            
            # 2. 运行 collect_websocket_data.py 收集数据
            cmd2 = f"cd {script_dir} && python3 collect_websocket_data.py"
            if not run_command(cmd2, "步骤 2/3: 收集所有币种的 WebSocket 数据..."):
                input("\n按 Enter 键继续...")
                continue

            # 3. 运行 update_from_websocket.py 更新 Notion
            cmd3 = f"cd {script_dir} && python3 update_from_websocket.py"
            run_command(cmd3, "步骤 3/3: 将所有数据更新到 Notion...")

        elif choice == '3':
            # 收集数据并更新（不含新币）
            # 1. 运行 collect_websocket_data.py 收集数据
            cmd1 = f"cd {script_dir} && python3 collect_websocket_data.py"
            if not run_command(cmd1, "步骤 1/2: 收集所有币种的 WebSocket 数据..."):
                input("\n按 Enter 键继续...")
                continue

            # 2. 运行 update_from_websocket.py 更新 Notion
            cmd2 = f"cd {script_dir} && python3 update_from_websocket.py"
            run_command(cmd2, "步骤 2/2: 将所有数据更新到 Notion...")

        elif choice == '4':
            # 指定币种更新
            symbols = get_symbols_input()
            if not symbols:
                input("\n按 Enter 键继续...")
                continue
            
            # 1. 收集指定币种数据
            cmd1 = f"cd {script_dir} && python3 collect_websocket_data.py {symbols}"
            if not run_command(cmd1, f"步骤 1/2: 收集 {symbols} 的 WebSocket 数据..."):
                input("\n按 Enter 键继续...")
                continue

            # 2. 更新 Notion
            cmd2 = f"cd {script_dir} && python3 update_from_websocket.py --symbols {symbols}"
            run_command(cmd2, f"步骤 2/2: 更新 {symbols} 到 Notion...")

        elif choice == '5':
            # 仅收集数据
            cmd = f"cd {script_dir} && python3 collect_websocket_data.py"
            run_command(cmd, "仅收集所有币种的 WebSocket 数据...")

        elif choice == '6':
            # 每日行情总结
            if not check_websocket_data_exists(script_dir):
                print("\n⚠️  未找到 WebSocket 数据文件")
                print("请先选择选项 [2], [3] 或 [5] 收集数据")
                input("\n按 Enter 键继续...")
                continue
            
            cmd = f"cd {script_dir} && python3 daily_summary.py"
            run_command(cmd, "生成每日行情总结...")
            
        else:
            print("\n❌ 无效输入，请输入 0 到 6 之间的数字。")
        
        input("\n按 Enter 键返回主菜单...")

if __name__ == "__main__":
    main()
