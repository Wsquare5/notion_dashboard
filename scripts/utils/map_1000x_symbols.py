#!/usr/bin/env python3
"""
自动映射 1000X 系列币种到基础币种的 CMC ID
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CMC_MAPPING_FILE = ROOT / 'binance_cmc_mapping.json'


def get_base_symbol_and_multiplier(symbol: str) -> tuple:
    """
    获取基础币种和倍数
    
    Examples:
        1000000BOB -> (BOB, 1000000)
        1000PEPE -> (PEPE, 1000)
        1MBABYDOGE -> (BABYDOGE, 1000000)  # 1M = 1,000,000
        1000X -> None (这是完整币名，不是乘数币)
    """
    # 1000X 是完整的币种名称，不是乘数币
    if symbol == '1000X':
        return None, None
    
    if symbol.startswith('1000000'):
        return symbol[7:], 1000000
    elif symbol.startswith('1000'):
        return symbol[4:], 1000
    elif symbol.startswith('1M'):
        return symbol[2:], 1000000
    else:
        return None, None


def main():
    """主函数"""
    print("🔗 自动映射 1000X 系列币种到基础币种\n")
    
    # 加载 mapping
    with open(CMC_MAPPING_FILE) as f:
        data = json.load(f)
        mapping = data.get('mapping', {})
    
    # 找出所有 1000X 系列
    x1000_symbols = [s for s in mapping.keys() 
                     if s.startswith('1000') or s.startswith('1M')]
    
    print(f"📋 找到 {len(x1000_symbols)} 个 1000X 系列币种\n")
    
    matched = 0
    not_found = 0
    
    for symbol in sorted(x1000_symbols):
        base_symbol, multiplier = get_base_symbol_and_multiplier(symbol)
        
        if not base_symbol:
            continue
        
        # 检查当前状态
        current_cmc_id = mapping[symbol].get('cmc_id')
        
        # 如果已经有 CMC ID，跳过（除非是手动设置的特殊情况）
        if current_cmc_id and symbol != '1000X':
            print(f"⏭️  {symbol:20} 已有 CMC ID: {current_cmc_id}")
            continue
        
        # 查找基础币种
        base_info = mapping.get(base_symbol)
        
        if base_info and base_info.get('cmc_id'):
            base_cmc_id = base_info['cmc_id']
            base_slug = base_info.get('cmc_slug')
            base_symbol_cmc = base_info.get('cmc_symbol')
            
            # 更新 1000X 币种的 mapping
            mapping[symbol] = {
                'cmc_id': base_cmc_id,
                'cmc_slug': base_slug,
                'cmc_symbol': base_symbol_cmc,
                'match_type': 'x1000_auto',
                'base_symbol': base_symbol,
                'multiplier': multiplier
            }
            
            matched += 1
            print(f"✅ {symbol:20} → {base_symbol} (CMC ID: {base_cmc_id}, ÷{multiplier})")
        else:
            not_found += 1
            print(f"❌ {symbol:20} → {base_symbol} (基础币种未找到 CMC ID)")
    
    # 保存更新
    if matched > 0:
        data['mapping'] = mapping
        with open(CMC_MAPPING_FILE, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ 已保存 {matched} 个自动映射到 {CMC_MAPPING_FILE}")
    else:
        print(f"\n⚠️  没有新的映射需要保存")
    
    print(f"\n📊 统计:")
    print(f"   成功映射: {matched}")
    print(f"   基础币种未找到: {not_found}")


if __name__ == "__main__":
    main()
