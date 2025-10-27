#!/usr/bin/env python3
"""
增强的CoinGecko匹配算法
使用多种策略提高匹配率：模糊匹配、名称匹配、手动校对等
"""

import json
import requests
import time
from difflib import SequenceMatcher
from typing import List, Dict, Optional, Tuple

def load_coingecko_coins():
    """获取CoinGecko完整代币列表"""
    print("📥 获取CoinGecko代币列表...")
    
    try:
        response = requests.get('https://api.coingecko.com/api/v3/coins/list', timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ 获取失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None

def fuzzy_match_symbol(target_symbol: str, coins_list: List[Dict], threshold: float = 0.6) -> List[Tuple[Dict, float]]:
    """模糊匹配代币符号"""
    matches = []
    target_upper = target_symbol.upper()
    
    for coin in coins_list:
        coin_symbol = coin['symbol'].upper()
        coin_name = coin['name'].upper()
        coin_id = coin['id'].upper()
        
        # 1. 精确匹配符号
        if coin_symbol == target_upper:
            matches.append((coin, 1.0))
            continue
        
        # 2. 符号模糊匹配
        symbol_similarity = SequenceMatcher(None, target_upper, coin_symbol).ratio()
        if symbol_similarity >= threshold:
            matches.append((coin, symbol_similarity))
            continue
        
        # 3. 名称包含匹配
        if target_upper in coin_name or coin_name in target_upper:
            name_similarity = 0.8  # 给名称匹配一个固定分数
            matches.append((coin, name_similarity))
            continue
        
        # 4. ID包含匹配
        if target_upper.replace('1000', '') in coin_id:
            id_similarity = 0.7  # 给ID匹配一个固定分数
            matches.append((coin, id_similarity))
    
    # 按相似度排序
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches[:10]  # 返回前10个最佳匹配

def enhanced_match_unmatched_symbols():
    """增强匹配未匹配的代币"""
    
    # 读取现有映射
    with open('binance_coingecko_mapping.json', 'r', encoding='utf-8') as f:
        mapping_data = json.load(f)
    
    # 找出未匹配的代币
    unmatched_symbols = []
    for symbol, info in mapping_data['mapping'].items():
        if info['coingecko_id'] is None:
            unmatched_symbols.append(symbol)
    
    print(f"🔍 开始增强匹配 {len(unmatched_symbols)} 个未匹配代币...")
    
    # 获取CoinGecko列表
    coins_list = load_coingecko_coins()
    if not coins_list:
        print("❌ 无法获取CoinGecko列表")
        return
    
    # 手动规则和猜测（基于常见模式）
    manual_mappings = {
        '1000000BOB': None,  # 可能是新代币，暂时没有
        '1000000MOG': None,  # 可能是新代币，暂时没有
        'AVAAI': None,       # AI相关代币，可能很新
        'BEAMX': 'beam-2',   # 可能是Beam的变种
        'BROCCOLI714': None, # 测试代币
        'BROCCOLIF3B': None, # 测试代币
        'BTCDOM': None,      # Bitcoin Dominance，不是真实代币
        'BTTC': 'bittorrent', # BitTorrent Chain
        'DODOX': 'dodo',     # DODO的变种
        'EUR': None,         # 法币，不是加密货币
        'FXS': 'frax-share', # Frax Share
        'LUNA2': 'terra-luna-2', # Terra Luna 2.0
        'MYRO': 'myro',      # Solana生态的MYRO
        'RAYSOL': None,       # 可能是Raydium相关的复合代币
        'RONIN': 'ronin',    # Ronin Network
        'VELODROME': 'velodrome-finance'  # Velodrome
    }
    
    enhanced_matches = {}
    
    for symbol in unmatched_symbols:
        print(f"\n=== 处理 {symbol} ===")
        
        # 1. 检查手动映射
        if symbol in manual_mappings:
            manual_id = manual_mappings[symbol]
            if manual_id:
                print(f"📝 手动映射: {symbol} -> {manual_id}")
                enhanced_matches[symbol] = {
                    'coingecko_id': manual_id,
                    'match_type': 'manual',
                    'confidence': 1.0
                }
            else:
                print(f"❌ 手动确认无匹配: {symbol}")
                enhanced_matches[symbol] = {
                    'coingecko_id': None,
                    'match_type': 'manual_none',
                    'confidence': 1.0
                }
            continue
        
        # 2. 模糊匹配
        fuzzy_matches = fuzzy_match_symbol(symbol, coins_list, threshold=0.6)
        
        if fuzzy_matches:
            print(f"🔍 找到 {len(fuzzy_matches)} 个候选匹配:")
            for i, (coin, score) in enumerate(fuzzy_matches[:5]):
                print(f"  {i+1}. {coin['id']} ({coin['symbol']}) - {coin['name']} | 相似度: {score:.2f}")
            
            # 取最佳匹配
            best_match, best_score = fuzzy_matches[0]
            if best_score >= 0.8:
                print(f"✅ 自动采用最佳匹配: {symbol} -> {best_match['id']}")
                enhanced_matches[symbol] = {
                    'coingecko_id': best_match['id'],
                    'match_type': 'fuzzy_auto',
                    'confidence': best_score
                }
            else:
                print(f"⚠️  最佳匹配分数较低 ({best_score:.2f})，需要手动确认")
                enhanced_matches[symbol] = {
                    'coingecko_id': best_match['id'],
                    'match_type': 'fuzzy_manual',
                    'confidence': best_score,
                    'candidates': [(c['id'], c['symbol'], c['name'], s) for c, s in fuzzy_matches[:3]]
                }
        else:
            print(f"❌ 未找到任何匹配")
            enhanced_matches[symbol] = {
                'coingecko_id': None,
                'match_type': 'no_match',
                'confidence': 0.0
            }
    
    return enhanced_matches

def update_mapping_with_enhanced_matches(enhanced_matches: Dict):
    """更新映射文件"""
    
    # 读取现有映射
    with open('binance_coingecko_mapping.json', 'r', encoding='utf-8') as f:
        mapping_data = json.load(f)
    
    # 更新匹配结果
    updated_count = 0
    for symbol, match_info in enhanced_matches.items():
        if match_info['coingecko_id']:
            mapping_data['mapping'][symbol] = {
                'coingecko_id': match_info['coingecko_id'],
                'match_type': match_info['match_type'],
                'timestamp': time.time(),
                'confidence': match_info.get('confidence', 1.0)
            }
            updated_count += 1
            print(f"✅ 更新: {symbol} -> {match_info['coingecko_id']}")
        else:
            mapping_data['mapping'][symbol]['match_type'] = match_info['match_type']
            print(f"❌ 确认无匹配: {symbol}")
    
    # 更新元数据
    if 'metadata' in mapping_data:
        mapping_data['metadata']['matched_symbols'] += updated_count
        mapping_data['metadata']['match_rate'] = mapping_data['metadata']['matched_symbols'] / mapping_data['metadata']['total_symbols'] * 100
        mapping_data['metadata']['last_enhanced'] = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # 保存更新后的映射
    with open('binance_coingecko_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(mapping_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 更新统计:")
    print(f"  新增匹配: {updated_count}")
    print(f"  新匹配率: {mapping_data['metadata']['match_rate']:.1f}%")
    
    # 保存需要手动确认的结果
    manual_review = {}
    for symbol, match_info in enhanced_matches.items():
        if match_info['match_type'] == 'fuzzy_manual':
            manual_review[symbol] = match_info
    
    if manual_review:
        with open('manual_review_needed.json', 'w', encoding='utf-8') as f:
            json.dump(manual_review, f, indent=2, ensure_ascii=False)
        print(f"📝 {len(manual_review)} 个代币需要手动确认，详见 manual_review_needed.json")

if __name__ == "__main__":
    print("🚀 开始增强CoinGecko匹配...")
    
    # 执行增强匹配
    enhanced_matches = enhanced_match_unmatched_symbols()
    
    if enhanced_matches:
        # 更新映射文件
        update_mapping_with_enhanced_matches(enhanced_matches)
        print("✅ 增强匹配完成！")
    else:
        print("❌ 增强匹配失败")