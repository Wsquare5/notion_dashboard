#!/usr/bin/env python3
"""
Test script to verify command line arguments work correctly
"""

import subprocess
import sys

def run_command(cmd):
    """Run a command and show its help or output"""
    print("=" * 80)
    print(f"Running: {cmd}")
    print("=" * 80)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print()

def main():
    print("\n🧪 Testing Command Line Arguments\n")
    
    # Test 1: Show help
    print("Test 1: Show help message")
    run_command("python3 scripts/update_binance_trading_data.py --help")
    
    print("\n✅ Tests complete!")
    print("\nUsage examples:")
    print("  1. Update all (no supply): python3 scripts/update_binance_trading_data.py")
    print("  2. Update all (with supply): python3 scripts/update_binance_trading_data.py --update-supply")
    print("  3. Update specific: python3 scripts/update_binance_trading_data.py BTC ETH SOL")
    print("  4. Update specific (with supply): python3 scripts/update_binance_trading_data.py --update-supply BTC ETH")

if __name__ == '__main__':
    main()
