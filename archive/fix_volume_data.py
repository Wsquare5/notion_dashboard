#!/usr/bin/env python3
"""
修复perp-only数据中的交易量问题
将基础资产交易量转换为USDT交易额
"""

import json
from pathlib import Path

def fix_volume_data(input_file: str, output_file: str):
    """修复交易量数据"""
    
    # 读取原始数据
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📊 处理 {len(data)} 个代币的交易量数据...")
    
    fixed_count = 0
    
    for token in data:
        symbol = token['symbol']
        price = token.get('perp_price')
        volume = token.get('perp_24h_volume')
        
        if price and volume and price > 0:
            # 当前数据文件中存储的都是基础资产数量，需要转换为USDT成交额
            usd_volume = volume * price
            print(f"  {symbol}: {volume:,.0f} × ${price} = ${usd_volume:,.0f}")
            token['perp_24h_volume'] = usd_volume
            fixed_count += 1
    
    # 保存修复后的数据
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 修复完成:")
    print(f"  修复了 {fixed_count} 个代币的交易量数据")
    print(f"  数据已保存到: {output_file}")

if __name__ == "__main__":
    input_file = "data/perp_only_all_data.json"
    output_file = "data/perp_only_fixed_volume.json"
    
    fix_volume_data(input_file, output_file)