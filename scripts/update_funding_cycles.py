#!/usr/bin/env python3
"""
为现有数据添加正确的费率周期信息
"""

import json
import requests
import time
from pathlib import Path

def calculate_funding_cycle(symbol):
    """计算单个代币的费率周期"""
    try:
        symbol_usdt = f'{symbol}USDT'
        url = f'https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol_usdt}&limit=3'
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if len(data) >= 2:
                # 计算时间间隔
                timestamp1 = int(data[0]['fundingTime'])
                timestamp2 = int(data[1]['fundingTime'])
                
                interval_ms = abs(timestamp1 - timestamp2)
                interval_hours = interval_ms / (1000 * 60 * 60)
                
                # 推断周期
                if 7.5 <= interval_hours <= 8.5:
                    return 8
                elif 3.5 <= interval_hours <= 4.5:
                    return 4  
                elif 5.5 <= interval_hours <= 6.5:
                    return 6
                else:
                    return 8  # 默认8小时
            else:
                return 8  # 默认8小时
        else:
            return 8  # 默认8小时
            
    except Exception as e:
        print(f"⚠️  计算 {symbol} 费率周期失败: {e}")
        return 8  # 默认8小时

def update_funding_cycles(data_file):
    """更新数据中的费率周期"""
    
    # 读取数据
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"🔄 开始计算 {len(data)} 个代币的费率周期...")
    
    cycle_stats = {}
    updated_count = 0
    
    for i, token in enumerate(data, 1):
        symbol = token['symbol']
        print(f"  ({i}/{len(data)}) 计算 {symbol}...")
        
        try:
            cycle = calculate_funding_cycle(symbol)
            token['funding_cycle'] = cycle
            
            cycle_stats[cycle] = cycle_stats.get(cycle, 0) + 1
            updated_count += 1
            
            print(f"    → {cycle}小时")
            
            # 控制API调用频率
            time.sleep(0.3)
            
            # 每10个代币休息一下
            if i % 10 == 0:
                print(f"    ⏳ 已处理 {i} 个，休息 2 秒...")
                time.sleep(2)
                
        except Exception as e:
            print(f"    ❌ 失败: {e}")
            token['funding_cycle'] = 8  # 默认值
    
    # 保存更新后的数据
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 费率周期更新完成:")
    print(f"  成功更新: {updated_count}/{len(data)} 个代币")
    
    print(f"\n📊 费率周期分布:")
    for cycle, count in sorted(cycle_stats.items()):
        print(f"  {cycle}小时: {count}个代币")

if __name__ == "__main__":
    data_file = "data/perp_only_fixed_volume.json"
    update_funding_cycles(data_file)