#!/usr/bin/env python3
"""
批量补全缺失 CMC 元数据的页面
"""
import sys
from pathlib import Path
import json
import time

sys.path.insert(0, str(Path.cwd()))

from scripts.update_binance_trading_data import CMCClient, NotionClient
import requests

# 加载配置
with open('config/config.json', 'r') as f:
    config = json.load(f)

with open('config/api_config.json', 'r') as f:
    api_config = json.load(f)

with open('config/binance_cmc_mapping.json', 'r') as f:
    cmc_data = json.load(f)
    
# Handle nested mapping structure (like update.py does)
if 'mapping' in cmc_data:
    cmc_mapping = cmc_data['mapping']
else:
    cmc_mapping = cmc_data

# 初始化客户端
cmc_client = CMCClient(api_config['coinmarketcap']['api_key'])
notion = NotionClient(config['notion']['api_key'], config['notion']['database_id'])

print("=" * 80)
print("🔧 批量补全缺失 CMC 元数据")
print("=" * 80)

# 1. 查询所有页面
print("\n📥 正在加载所有 Notion 页面...")
all_pages = notion.query_database()
print(f"✅ 加载了 {len(all_pages)} 个页面")

# 2. 找出缺失 CMC 元数据的页面
print("\n🔍 检查哪些页面缺失 CMC 元数据...")
missing_metadata = []

for page in all_pages:
    props = page['properties']
    
    # 获取 Symbol
    symbol_prop = props.get('Symbol', {})
    if not symbol_prop.get('title'):
        continue
    symbol = symbol_prop['title'][0]['text']['content']
    
    # 检查是否有 CMC mapping
    if symbol not in cmc_mapping:
        continue
    
    cmc_id = cmc_mapping[symbol].get('cmc_id')
    if not cmc_id:
        continue
    
    # 检查是否缺失元数据（检查 Name 字段）
    name_prop = props.get('Name', {})
    has_name = bool(name_prop.get('rich_text'))
    
    if not has_name:
        missing_metadata.append({
            'page_id': page['id'],
            'symbol': symbol,
            'cmc_id': cmc_id,
            'created_time': page['created_time']
        })

print(f"⚠️  发现 {len(missing_metadata)} 个页面缺失 CMC 元数据")

if not missing_metadata:
    print("\n✅ 所有页面的 CMC 元数据都是完整的！")
    sys.exit(0)

# 显示前 10 个
print("\n前 10 个缺失元数据的页面:")
for item in missing_metadata[:10]:
    print(f"  - {item['symbol']} (CMC ID: {item['cmc_id']}, 创建于 {item['created_time'][:10]})")

if len(missing_metadata) > 10:
    print(f"  ... 还有 {len(missing_metadata) - 10} 个")

# 3. 询问是否继续
print("\n" + "=" * 80)
response = input(f"是否批量更新这 {len(missing_metadata)} 个页面？(y/n): ").strip().lower()

if response != 'y':
    print("❌ 已取消")
    sys.exit(0)

# 4. 批量更新
print("\n🚀 开始批量更新...")
success_count = 0
error_count = 0
rate_limit_hit = False

for i, item in enumerate(missing_metadata, 1):
    symbol = item['symbol']
    cmc_id = item['cmc_id']
    page_id = item['page_id']
    
    try:
        # 获取 CMC 数据
        cmc_full_data = cmc_client.get_token_data(cmc_id)
        
        if not cmc_full_data:
            print(f"[{i}/{len(missing_metadata)}] {symbol} ⚠️  CMC API 返回空数据")
            error_count += 1
            continue
        
        metadata = cmc_full_data['metadata']
        quote_data = cmc_full_data['quote']
        quote = quote_data.get('quote', {}).get('USD', {})
        
        # 构建更新属性
        properties = {}
        
        # Name
        if metadata.get('name'):
            properties['Name'] = {
                "rich_text": [{"text": {"content": metadata['name']}}]
            }
        
        # CMC ID
        properties['CMC ID'] = {
            "number": cmc_id
        }
        
        # Website
        websites = metadata.get('urls', {}).get('website', [])
        if websites and websites[0]:
            properties['Website'] = {
                "url": websites[0]
            }
        
        # Logo (作为 URL)
        if metadata.get('logo'):
            properties['Logo'] = {
                "url": metadata['logo']
            }
        
        # Genesis Date
        if metadata.get('date_added'):
            date_str = metadata['date_added'][:10]  # 取前 10 位 YYYY-MM-DD
            properties['Genesis Date'] = {
                "date": {"start": date_str}
            }
        
        # Circulating Supply
        if quote_data.get('circulating_supply'):
            properties['Circulating Supply'] = {
                "number": float(quote_data['circulating_supply'])
            }
        
        # Total Supply
        if quote_data.get('total_supply'):
            properties['Total Supply'] = {
                "number": float(quote_data['total_supply'])
            }
        
        # Max Supply
        if quote_data.get('max_supply'):
            properties['Max Supply'] = {
                "number": float(quote_data['max_supply'])
            }
        
        # FDV
        if quote.get('fully_diluted_market_cap'):
            properties['FDV'] = {
                "number": float(quote['fully_diluted_market_cap'])
            }
        
        # 更新页面
        icon_url = metadata.get('logo')
        notion.update_page(page_id, properties, icon_url)
        
        print(f"[{i}/{len(missing_metadata)}] {symbol} ✅")
        success_count += 1
        
        # 速率限制：每秒最多 3 个请求
        time.sleep(0.35)
        
    except Exception as e:
        error_msg = str(e)
        if '429' in error_msg or 'rate_limit' in error_msg.lower():
            print(f"[{i}/{len(missing_metadata)}] {symbol} ⚠️  触发 CMC API 速率限制")
            rate_limit_hit = True
            break
        else:
            print(f"[{i}/{len(missing_metadata)}] {symbol} ❌ {error_msg[:50]}")
            error_count += 1

# 5. 总结
print("\n" + "=" * 80)
print("📊 更新完成")
print("=" * 80)
print(f"✅ 成功: {success_count}")
print(f"❌ 失败: {error_count}")
if rate_limit_hit:
    print(f"⚠️  剩余: {len(missing_metadata) - success_count - error_count} (触发了 CMC API 速率限制)")
    print("\n💡 建议：等待几分钟后重新运行此脚本继续更新")
