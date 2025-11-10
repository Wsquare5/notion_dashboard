#!/usr/bin/env python3
"""
测试快速更新脚本实际更新的字段
对比更新前后的数据，确认所有交易数据都有更新
"""

import json
import requests
import time
from pathlib import Path

CONFIG_FILE = Path('config.json')

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def get_notion_page(symbol: str, api_key: str, database_id: str):
    """获取Notion页面数据"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json'
    }
    
    url = f'https://api.notion.com/v1/databases/{database_id}/query'
    payload = {
        'filter': {
            'property': 'Symbol',
            'title': {'equals': symbol}
        }
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    results = response.json().get('results', [])
    
    return results[0] if results else None

def extract_properties(page):
    """提取页面的关键属性"""
    if not page:
        return None
    
    props = page.get('properties', {})
    
    def get_number(prop_name):
        return props.get(prop_name, {}).get('number')
    
    def get_text(prop_name):
        rich_text = props.get(prop_name, {}).get('rich_text', [])
        return rich_text[0]['text']['content'] if rich_text else None
    
    return {
        'Spot Price': get_number('Spot Price'),
        'Perp Price': get_number('Perp Price'),
        'Spot vol 24h': get_number('Spot vol 24h'),
        'Perp vol 24h': get_number('Perp vol 24h'),
        'Price change': get_number('Price change'),
        'OI': get_number('OI'),
        'Funding': get_number('Funding'),
        'Basis': get_number('Basis'),
        'MC': get_number('MC'),
        'Circulating Supply': get_number('Circulating Supply'),
        'Total Supply': get_number('Total Supply'),
        'FDV': get_number('FDV'),
        'Funding Cycle': get_number('Funding Cycle'),
        'Categories': props.get('Categories', {}).get('multi_select', []),
        'Index Composition': get_text('Index Composition'),
        'last_edited_time': page.get('last_edited_time')
    }

def compare_data(before, after, symbol):
    """对比更新前后的数据"""
    print(f"\n{'='*80}")
    print(f"📊 {symbol} 字段更新对比")
    print(f"{'='*80}")
    
    if not before or not after:
        print("❌ 数据获取失败")
        return
    
    # 定义字段分类
    trading_fields = ['Spot Price', 'Perp Price', 'Spot vol 24h', 'Perp vol 24h', 
                     'Price change', 'OI', 'Funding', 'Basis', 'MC']
    supply_fields = ['Circulating Supply', 'Total Supply', 'FDV']
    static_fields = ['Funding Cycle', 'Categories', 'Index Composition']
    
    print("\n🔄 实时交易数据（应该更新）:")
    print("-" * 80)
    updated_count = 0
    unchanged_count = 0
    
    for field in trading_fields:
        before_val = before.get(field)
        after_val = after.get(field)
        
        if before_val != after_val:
            status = "✅ 已更新"
            updated_count += 1
            symbol_str = "🔄"
        else:
            status = "⚠️  未变化"
            unchanged_count += 1
            symbol_str = "  "
        
        # 格式化数值显示
        if isinstance(before_val, (int, float)) and isinstance(after_val, (int, float)):
            if field in ['Funding', 'Basis', 'Price change']:
                # 百分比显示
                before_str = f"{before_val*100:.4f}%" if before_val else "N/A"
                after_str = f"{after_val*100:.4f}%" if after_val else "N/A"
            elif field in ['MC', 'OI', 'Spot vol 24h', 'Perp vol 24h']:
                # 大数值用逗号分隔
                before_str = f"${before_val:,.2f}" if before_val else "N/A"
                after_str = f"${after_val:,.2f}" if after_val else "N/A"
            else:
                # 价格显示
                before_str = f"${before_val:.6f}" if before_val else "N/A"
                after_str = f"${after_val:.6f}" if after_val else "N/A"
            
            print(f"{symbol_str} {field:20} {before_str:>20} → {after_str:>20} {status}")
        else:
            print(f"{symbol_str} {field:20} {str(before_val):>20} → {str(after_val):>20} {status}")
    
    print(f"\n📈 供应量数据（不应更新，除非使用 --update-metadata）:")
    print("-" * 80)
    for field in supply_fields:
        before_val = before.get(field)
        after_val = after.get(field)
        
        if before_val != after_val:
            status = "🔄 已更新"
        else:
            status = "✅ 未变化（正确）"
        
        if isinstance(before_val, (int, float)) and isinstance(after_val, (int, float)):
            if field in ['FDV']:
                before_str = f"${before_val:,.2f}" if before_val else "N/A"
                after_str = f"${after_val:,.2f}" if after_val else "N/A"
            else:
                before_str = f"{before_val:,.2f}" if before_val else "N/A"
                after_str = f"{after_val:,.2f}" if after_val else "N/A"
            print(f"   {field:20} {before_str:>20} → {after_str:>20} {status}")
        else:
            print(f"   {field:20} {str(before_val):>20} → {str(after_val):>20} {status}")
    
    print(f"\n🔧 静态字段（不应更新，除非使用 --update-static-fields）:")
    print("-" * 80)
    for field in static_fields:
        before_val = before.get(field)
        after_val = after.get(field)
        
        if before_val != after_val:
            status = "🔄 已更新"
        else:
            status = "✅ 未变化（正确）"
        
        if field == 'Categories':
            before_str = ', '.join([c['name'] for c in before_val]) if before_val else "N/A"
            after_str = ', '.join([c['name'] for c in after_val]) if after_val else "N/A"
            print(f"   {field:20} {before_str[:20]:>20} → {after_str[:20]:>20} {status}")
        else:
            before_str = str(before_val)[:30] if before_val else "N/A"
            after_str = str(after_val)[:30] if after_val else "N/A"
            print(f"   {field:20} {before_str:>20} → {after_str:>20} {status}")
    
    # 总结
    print(f"\n{'='*80}")
    print(f"✅ 实时数据更新: {updated_count}/{len(trading_fields)} 个字段")
    print(f"⚠️  实时数据未变化: {unchanged_count}/{len(trading_fields)} 个字段")
    
    if unchanged_count > 0:
        print(f"\n💡 提示：部分字段未变化可能是因为：")
        print(f"   1. 市场数据本身没有变化（价格/交易量稳定）")
        print(f"   2. API 返回了相同的值")
        print(f"   3. 该币种只有现货或只有合约，部分字段为空")
    
    print(f"\n⏰ 更新时间对比:")
    print(f"   更新前: {before.get('last_edited_time')}")
    print(f"   更新后: {after.get('last_edited_time')}")
    print(f"{'='*80}\n")

def main():
    # 测试币种列表
    test_symbols = ['BTC', 'ETH', 'SOL']
    
    print("="*80)
    print("🧪 快速更新字段测试")
    print("="*80)
    print(f"\n测试币种: {', '.join(test_symbols)}")
    print(f"测试目标: 验证快速更新脚本是否更新所有交易数据字段\n")
    
    # 加载配置
    config = load_config()
    api_key = config['notion']['api_key']
    database_id = config['notion']['database_id']
    
    # 步骤1: 获取更新前的数据
    print("📥 步骤 1/3: 获取更新前的数据...")
    before_data = {}
    for symbol in test_symbols:
        page = get_notion_page(symbol, api_key, database_id)
        before_data[symbol] = extract_properties(page)
        print(f"   ✅ {symbol}")
    
    # 步骤2: 执行快速更新
    print(f"\n🚀 步骤 2/3: 执行快速更新...")
    import subprocess
    symbols_str = ' '.join(test_symbols)
    cmd = f"python3 scripts/update_binance_trading_data_fast.py {symbols_str}"
    print(f"   命令: {cmd}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"   ❌ 更新失败:")
        print(result.stderr)
        return
    
    print("   ✅ 更新完成")
    
    # 等待一下确保Notion更新完成
    print(f"\n⏳ 等待 3 秒确保 Notion 更新完成...")
    time.sleep(3)
    
    # 步骤3: 获取更新后的数据
    print(f"📥 步骤 3/3: 获取更新后的数据...")
    after_data = {}
    for symbol in test_symbols:
        page = get_notion_page(symbol, api_key, database_id)
        after_data[symbol] = extract_properties(page)
        print(f"   ✅ {symbol}")
    
    # 对比数据
    for symbol in test_symbols:
        compare_data(before_data[symbol], after_data[symbol], symbol)
    
    print("\n" + "="*80)
    print("✅ 测试完成！")
    print("="*80)

if __name__ == '__main__':
    main()
