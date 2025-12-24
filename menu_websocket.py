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
    print("🚀 Binance Trading Data Update Menu")
    print("="*80)
    print("\n请选择更新模式：\n")
    print("  [1] ⚡️ 快速更新（使用已有数据）")
    print("      • 使用本地 WebSocket 数据更新 Notion")
    print("      • 适用于刚收集完数据后的快速更新")
    print("      • 更新：价格、成交量、资金费率、MC、FDV")
    print("      • 耗时：~1分钟")
    print()
    print("  [2] 🔄 同步新币种（推荐每周一次）")
    print("      • 从币安发现并创建新上市的币种")
    print("      • 自动匹配 CMC ID 并获取元数据")
    print("      • 收集实时数据并完整更新")
    print("      • 耗时：~10分钟")
    print()
    print("  [3] 🌐 WebSocket 完整更新")
    print("      • 收集所有币种的实时数据（WebSocket）")
    print("      • 更新：价格、成交量、资金费率、MC、FDV")
    print("      • 无封禁风险，可随时运行")
    print("      • 耗时：~6分钟")
    print()
    print("  [4] 🔧 REST API 完整更新（包含 OI/Index Composition）")
    print("      • 使用 Binance REST API 获取完整数据")
    print("      • 更新：价格、成交量、OI、资金费率、Basis、Index Composition")
    print("      • 自动计算 MC、FDV")
    print("      • VPS 环境相对安全，推荐每日运行一次")
    print("      • 耗时：~8-10分钟")
    print()
    print("  [5] 🎯 指定币种更新")
    print("      • 输入币种符号，更新指定币种")
    print("      • 使用 REST API 获取数据")
    print()
    print("  [6] 📈 每日行情总结")
    print("      • 生成涨跌幅前5名总结并写入 Notion")
    print("      • 需要先收集 WebSocket 数据")
    print()
    print("  [7] 🪙 更新流通供应量（低频）")
    print("      • 从 CoinMarketCap 安全地更新所有币种的流通量")
    print("      • 内置延迟，无封禁风险，推荐每周运行一次")
    print("      • 耗时: ~15-20分钟")
    print()
    print("  [0] 退出")
    print("\n" + "="*80)
    print("💡 提示：选项 [3] 使用 WebSocket 无速率限制；选项 [4] 获取更完整数据但有速率限制")
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
        
        choice = input("请选择操作 [0-7]: ").strip()
        
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
            # WebSocket 完整更新
            # 1. 运行 collect_websocket_data.py 收集数据
            cmd1 = f"cd {script_dir} && python3 collect_websocket_data.py"
            if not run_command(cmd1, "步骤 1/2: 收集所有币种的 WebSocket 数据..."):
                input("\n按 Enter 键继续...")
                continue

            # 2. 运行 update_from_websocket.py 更新 Notion
            cmd2 = f"cd {script_dir} && python3 update_from_websocket.py"
            run_command(cmd2, "步骤 2/2: 将所有数据更新到 Notion...")

        elif choice == '4':
            # REST API 完整更新
            cmd = f"cd {script_dir} && python3 scripts/update_binance_trading_data.py --update-static-fields --skip-new-pages"
            run_command(cmd, "使用 REST API 获取完整数据并更新 Notion...")

        elif choice == '5':
            # 指定币种更新 - 使用 REST API
            symbols = get_symbols_input()
            if not symbols:
                input("\n按 Enter 键继续...")
                continue
            
            # 使用 REST API 更新指定币种
            cmd = f"cd {script_dir} && python3 scripts/update_binance_trading_data.py --update-static-fields {symbols}"
            run_command(cmd, f"使用 REST API 更新 {symbols}...")

        elif choice == '6':
            # 每日行情总结
            if not check_websocket_data_exists(script_dir):
                print("\n⚠️  未找到 WebSocket 数据文件")
                print("请先选择选项 [2] 或 [3] 收集数据")
                input("\n按 Enter 键继续...")
                continue
            
            cmd = f"cd {script_dir} && python3 scripts/daily_market_summary.py"
            run_command(cmd, "生成每日行情总结...")

        elif choice == '7':
            # 更新流通供应量
            cmd = f"cd {script_dir} && python3 update_circulating_supply.py"
            run_command(cmd, "从 CoinMarketCap 更新流通供应量...")
            
        else:
            print("\n❌ 无效输入，请输入 0 到 7 之间的数字。")
        
        input("\n按 Enter 键返回主菜单...")

if __name__ == "__main__":
    main()
