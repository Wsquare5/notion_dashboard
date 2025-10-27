#!/usr/bin/env python3
"""
应用手动CoinGecko映射的脚本
读取manual_coingecko_mapping.json中的手动映射，更新到主映射文件中
"""

import json
import time
from pathlib import Path

def apply_manual_mapping():
    """应用手动映射到主映射文件"""
    
    manual_file = Path('manual_coingecko_mapping.json')
    main_file = Path('binance_coingecko_mapping.json')
    
    if not manual_file.exists():
        print("❌ manual_coingecko_mapping.json 文件不存在")
        return False
    
    if not main_file.exists():
        print("❌ binance_coingecko_mapping.json 文件不存在")
        return False
    
    # 读取手动映射
    try:
        with open(manual_file, 'r', encoding='utf-8') as f:
            manual_data = json.load(f)
    except Exception as e:
        print(f"❌ 读取手动映射文件失败: {e}")
        return False
    
    # 读取主映射文件
    try:
        with open(main_file, 'r', encoding='utf-8') as f:
            main_data = json.load(f)
    except Exception as e:
        print(f"❌ 读取主映射文件失败: {e}")
        return False
    
    # 应用手动映射
    updated_count = 0
    added_matches = 0
    
    unmatched_tokens = manual_data.get('unmatched_tokens', {})
    
    print(f"🔍 处理 {len(unmatched_tokens)} 个手动映射...")
    
    for symbol, mapping_info in unmatched_tokens.items():
        coingecko_id = mapping_info.get('coingecko_id')
        
        if symbol in main_data['mapping']:
            # 更新现有条目
            old_id = main_data['mapping'][symbol].get('coingecko_id')
            
            if coingecko_id != old_id:
                main_data['mapping'][symbol].update({
                    'coingecko_id': coingecko_id,
                    'match_type': 'manual',
                    'timestamp': time.time(),
                    'notes': mapping_info.get('notes', '')
                })
                
                if coingecko_id:
                    print(f"✅ 更新: {symbol} -> {coingecko_id}")
                    if old_id is None:
                        added_matches += 1
                else:
                    print(f"❌ 确认无匹配: {symbol}")
                
                updated_count += 1
            else:
                print(f"⏭️  跳过未更改: {symbol}")
        else:
            # 添加新条目
            main_data['mapping'][symbol] = {
                'coingecko_id': coingecko_id,
                'match_type': 'manual',
                'timestamp': time.time(),
                'notes': mapping_info.get('notes', '')
            }
            
            if coingecko_id:
                print(f"➕ 新增: {symbol} -> {coingecko_id}")
                added_matches += 1
            else:
                print(f"➕ 新增无匹配: {symbol}")
            
            updated_count += 1
    
    # 更新元数据
    if 'metadata' in main_data:
        main_data['metadata']['matched_symbols'] += added_matches
        total_symbols = len(main_data['mapping'])
        matched_symbols = sum(1 for info in main_data['mapping'].values() if info.get('coingecko_id'))
        
        main_data['metadata'].update({
            'total_symbols': total_symbols,
            'matched_symbols': matched_symbols,
            'match_rate': matched_symbols / total_symbols * 100 if total_symbols > 0 else 0,
            'last_manual_update': time.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # 保存更新后的主映射文件
    try:
        with open(main_file, 'w', encoding='utf-8') as f:
            json.dump(main_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📊 更新统计:")
        print(f"  处理条目: {updated_count}")
        print(f"  新增匹配: {added_matches}")
        print(f"  总匹配率: {main_data['metadata']['match_rate']:.1f}%")
        print(f"  总代币数: {main_data['metadata']['total_symbols']}")
        print(f"  匹配成功: {main_data['metadata']['matched_symbols']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 保存主映射文件失败: {e}")
        return False

def validate_coingecko_ids():
    """验证填写的CoinGecko ID是否有效（可选功能）"""
    manual_file = Path('manual_coingecko_mapping.json')
    
    if not manual_file.exists():
        print("❌ manual_coingecko_mapping.json 文件不存在")
        return
    
    with open(manual_file, 'r', encoding='utf-8') as f:
        manual_data = json.load(f)
    
    unmatched_tokens = manual_data.get('unmatched_tokens', {})
    
    # 检查哪些已经填写了ID
    filled_count = 0
    empty_count = 0
    
    print("📋 手动映射状态检查:")
    
    for symbol, mapping_info in unmatched_tokens.items():
        coingecko_id = mapping_info.get('coingecko_id')
        
        if coingecko_id:
            print(f"✅ {symbol} -> {coingecko_id}")
            filled_count += 1
        else:
            print(f"⏳ {symbol} -> 待填写")
            empty_count += 1
    
    print(f"\n📊 填写进度:")
    print(f"  已填写: {filled_count}")
    print(f"  待填写: {empty_count}")
    print(f"  总计: {filled_count + empty_count}")
    
    if empty_count > 0:
        print(f"\n💡 提示: 还有 {empty_count} 个代币待填写，完成后运行此脚本应用更改")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'check':
        # 检查填写状态
        validate_coingecko_ids()
    else:
        # 应用手动映射
        print("🚀 开始应用手动CoinGecko映射...")
        
        if apply_manual_mapping():
            print("✅ 手动映射应用成功！")
        else:
            print("❌ 手动映射应用失败")
        
        print("\n💡 使用说明:")
        print("  1. 编辑 manual_coingecko_mapping.json 文件")
        print("  2. 填写 coingecko_id 字段")
        print("  3. 运行 python3 apply_manual_mapping.py 应用更改")
        print("  4. 运行 python3 apply_manual_mapping.py check 检查填写状态")