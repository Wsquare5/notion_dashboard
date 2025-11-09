#!/usr/bin/env python3
"""
恢复丢失的Notion页面
使用历史数据和当前Binance数据重建页面
"""

import requests
import json
import time
from pathlib import Path

CONFIG_FILE = Path('config.json')


def load_config():
    """加载配置"""
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_missing_symbols():
    """加载缺失的币种列表"""
    with open('missing_symbols.txt', 'r') as f:
        return [line.strip() for line in f if line.strip()]


def load_cmc_mapping():
    """加载CMC映射"""
    try:
        with open('binance_cmc_mapping.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('mapping', {})
    except:
        return {}


def get_binance_contracts():
    """获取当前Binance上的所有永续合约"""
    try:
        response = requests.get('https://fapi.binance.com/fapi/v1/exchangeInfo', timeout=10)
        if response.status_code == 200:
            data = response.json()
            contracts = set()
            for symbol_info in data['symbols']:
                if (symbol_info['contractType'] == 'PERPETUAL' and 
                    symbol_info['quoteAsset'] == 'USDT' and
                    symbol_info['status'] == 'TRADING'):
                    contracts.add(symbol_info['baseAsset'])
            return contracts
        return set()
    except Exception as e:
        print(f"  ⚠️  获取Binance合约失败: {e}")
        return set()


def fetch_binance_data(symbol: str):
    """获取Binance交易数据"""
    data = {}
    
    try:
        # 24h行情
        response = requests.get(
            f'https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}USDT',
            timeout=5
        )
        if response.status_code == 200:
            ticker = response.json()
            data['perp_price'] = float(ticker['lastPrice'])
            data['price_change_24h'] = float(ticker['priceChangePercent'])
            data['volume_24h'] = float(ticker['quoteVolume'])
    except:
        pass
    
    try:
        # 持仓量
        response = requests.get(
            f'https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}USDT',
            timeout=5
        )
        if response.status_code == 200:
            oi_data = response.json()
            data['open_interest'] = float(oi_data['openInterest'])
    except:
        pass
    
    try:
        # 资金费率
        response = requests.get(
            f'https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}USDT',
            timeout=5
        )
        if response.status_code == 200:
            premium = response.json()
            data['funding_rate'] = float(premium['lastFundingRate'])
    except:
        pass
    
    return data


def create_notion_page(config: dict, symbol: str, cmc_data: dict, binance_data: dict) -> bool:
    """创建Notion页面"""
    api_key = config['notion']['api_key']
    database_id = config['notion']['database_id']
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }
    
    # 构建properties
    properties = {
        'Symbol': {
            'title': [{'text': {'content': symbol}}]
        }
    }
    
    # 添加CMC数据
    if cmc_data and cmc_data.get('cmc_slug'):
        if 'name' in cmc_data:
            properties['Name'] = {
                'rich_text': [{'text': {'content': cmc_data['name']}}]
            }
        
        properties['CMC Slug'] = {
            'rich_text': [{'text': {'content': cmc_data['cmc_slug']}}]
        }
        
        if cmc_data.get('cmc_id'):
            properties['CMC ID'] = {
                'number': cmc_data['cmc_id']
            }
    
    # 添加Binance交易数据
    if binance_data.get('perp_price'):
        properties['Perp Price'] = {
            'number': round(binance_data['perp_price'], 8)
        }
    
    if binance_data.get('price_change_24h') is not None:
        properties['24h Change'] = {
            'number': round(binance_data['price_change_24h'], 2)
        }
    
    if binance_data.get('volume_24h'):
        properties['24h Volume'] = {
            'number': round(binance_data['volume_24h'], 0)
        }
    
    if binance_data.get('open_interest'):
        properties['Open Interest'] = {
            'number': round(binance_data['open_interest'], 2)
        }
    
    if binance_data.get('funding_rate') is not None:
        properties['Funding Rate'] = {
            'number': round(binance_data['funding_rate'] * 100, 4)
        }
    
    payload = {
        'parent': {'database_id': database_id},
        'properties': properties
    }
    
    try:
        response = requests.post(
            'https://api.notion.com/v1/pages',
            headers=headers,
            json=payload,
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"    ❌ 创建失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("🔧 Notion页面恢复工具")
    print("=" * 60)
    
    # 加载配置
    config = load_config()
    
    # 加载缺失的币种
    print("\n📋 加载缺失的币种列表...")
    missing_symbols = load_missing_symbols()
    print(f"✅ 找到 {len(missing_symbols)} 个缺失的币种")
    
    # 获取当前Binance合约
    print("\n🔍 检查Binance当前合约...")
    current_contracts = get_binance_contracts()
    print(f"✅ Binance当前有 {len(current_contracts)} 个永续合约")
    
    # 过滤出仍在Binance上交易的币种
    active_missing = [s for s in missing_symbols if s in current_contracts]
    inactive_missing = [s for s in missing_symbols if s not in current_contracts]
    
    print(f"\n📊 分类结果:")
    print(f"  ✅ 仍在交易: {len(active_missing)} 个")
    print(f"  ⚠️  已下架: {len(inactive_missing)} 个")
    
    # 加载CMC映射
    print("\n📚 加载CMC映射...")
    cmc_mapping = load_cmc_mapping()
    print(f"✅ CMC映射包含 {len(cmc_mapping)} 个币种")
    
    # 询问用户
    print("\n" + "=" * 60)
    print(f"准备恢复 {len(active_missing)} 个仍在交易的币种")
    print("=" * 60)
    
    confirm = input("\n是否开始恢复？(yes/no): ").strip().lower()
    if confirm != 'yes':
        print("❌ 取消恢复")
        return
    
    # 开始恢复
    print(f"\n🚀 开始恢复页面...\n")
    
    success = 0
    failed = 0
    
    for i, symbol in enumerate(active_missing, 1):
        print(f"[{i}/{len(active_missing)}] {symbol}")
        
        # 获取CMC数据
        cmc_data = cmc_mapping.get(symbol, {})
        if not cmc_data or not cmc_data.get('cmc_id'):
            print(f"  ⚠️  无CMC映射")
        
        # 获取Binance数据
        print(f"  📈 获取交易数据...")
        binance_data = fetch_binance_data(symbol)
        
        if not binance_data:
            print(f"  ⚠️  无法获取交易数据")
        
        # 创建页面
        print(f"  📝 创建Notion页面...")
        if create_notion_page(config, symbol, cmc_data, binance_data):
            success += 1
            price_info = f"${binance_data.get('perp_price', 0):.4f}" if binance_data.get('perp_price') else ""
            print(f"  ✅ 成功 {price_info}")
        else:
            failed += 1
            print(f"  ❌ 失败")
        
        time.sleep(0.5)  # 避免请求过快
    
    # 总结
    print(f"\n" + "=" * 60)
    print(f"📊 恢复完成")
    print(f"=" * 60)
    print(f"✅ 成功: {success}/{len(active_missing)}")
    print(f"❌ 失败: {failed}/{len(active_missing)}")
    
    if inactive_missing:
        print(f"\n⚠️  {len(inactive_missing)} 个币种已下架，未恢复")
        print(f"已下架币种列表已保存到: inactive_symbols.txt")
        with open('inactive_symbols.txt', 'w') as f:
            for symbol in sorted(inactive_missing):
                f.write(f'{symbol}\n')


if __name__ == '__main__':
    main()
