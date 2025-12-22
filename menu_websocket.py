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
    print("  [2] 🌐 完整更新（收集数据 + 更新Notion）")
    print("      • 收集所有618个币种的实时数据（WebSocket）")
    print("      • 自动更新到 Notion")
    print("      • 无封禁风险，安全可靠")
    print("      • 耗时：~6分钟")
    print()
    print("  [3] 🎯 指定币种更新")
    print("      • 输入币种符号，更新指定币种")
    print("      • 先收集数据，再更新 Notion")
    print()
    print("  [4] 📊 仅收集 WebSocket 数据（不更新Notion）")
    print("      • 收集所有币种的实时数据")
    print("      • 保存到 data/websocket_collected_data.json")
    print()
    print("  [5] 📈 每日行情总结")
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
        
        choice = input("请选择操作 [0-5]: ").strip()
        
        if choice == '0':
            print("\n👋 再见！")
            sys.exit(0)
        
        elif choice == '1':
            # 快速更新（使用已有数据）
            if not check_websocket_data_exists(script_dir):
                print("\n⚠️  未找到 WebSocket 数据文件")
                print("请先选择选项 [2] 或 [4] 收集数据")
                input("\n按 Enter 键继续...")
                continue
            
            cmd = f"cd {script_dir} && python3 update_from_websocket.py"
            if run_command(cmd, "⚡️ 使用 WebSocket 数据快速更新 Notion"):
                input("\n按 Enter 键继续...")
        
        elif choice == '2':
            # 完整更新（收集 + 更新）
            print("\n🌐 开始完整更新流程...")
            print("步骤 1/2: 收集 WebSocket 数据")
            
            cmd1 = f"cd {script_dir} && python3 collect_websocket_data.py"
            if run_command(cmd1, "📡 收集所有币种的实时数据"):
                print("\n步骤 2/2: 更新 Notion")
                cmd2 = f"cd {script_dir} && python3 update_from_websocket.py"
                if run_command(cmd2, "📝 更新 Notion 数据库"):
                    print("\n✅ 完整更新流程完成！")
            
            input("\n按 Enter 键继续...")
        
        elif choice == '3':
            # 指定币种更新
            symbols = get_symbols_input()
            if symbols:
                print(f"\n🎯 开始更新指定币种：{symbols}")
                print("步骤 1/2: 收集指定币种的数据")
                
                cmd1 = f"cd {script_dir} && python3 collect_websocket_data.py {symbols}"
                if run_command(cmd1, f"📡 收集 {symbols} 的实时数据"):
                    print("\n步骤 2/2: 更新 Notion")
                    cmd2 = f"cd {script_dir} && python3 update_from_websocket.py {symbols}"
                    if run_command(cmd2, f"📝 更新 {symbols} 到 Notion"):
                        print("\n✅ 指定币种更新完成！")
                
                input("\n按 Enter 键继续...")
        
        elif choice == '4':
            # 仅收集数据
            cmd = f"cd {script_dir} && python3 collect_websocket_data.py"
            if run_command(cmd, "📡 收集所有币种的 WebSocket 数据"):
                print("\n💾 数据已保存到：data/websocket_collected_data.json")
                print("💡 提示：可以选择选项 [1] 快速更新到 Notion")
                input("\n按 Enter 键继续...")
        
        elif choice == '5':
            # 每日行情总结
            if not check_websocket_data_exists(script_dir):
                print("\n⚠️  未找到 WebSocket 数据文件")
                print("请先选择选项 [2] 或 [4] 收集数据")
                input("\n按 Enter 键继续...")
                continue
            
            cmd = f"cd {script_dir} && python3 scripts/daily_market_summary.py"
            if run_command(cmd, "📊 生成每日行情总结"):
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
