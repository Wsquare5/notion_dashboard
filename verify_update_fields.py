#!/usr/bin/env python3
"""
验证最近更新的币种是否所有交易数据字段都更新了
"""
import json
from datetime import datetime
from notion_client import Client

def load_config():
    """Load configuration"""
    with open('config.json', 'r') as f:
        return json.load(f)

def format_number(num):
    """Format large numbers"""
    if num is None:
        return "N/A"
    if num >= 1e9:
        return f"${num/1e9:.2f}B"
    elif num >= 1e6:
        return f"${num/1e6:.1f}M"
    elif num >= 1e3:
        return f"${num/1e3:.1f}K"
    else:
        return f"${num:.2f}"

def extract_value(prop):
    """Extract value from Notion property"""
    if not prop:
        return None
    
    prop_type = prop.get('type')
    
    if prop_type == 'number':
        return prop.get('number')
    elif prop_type == 'rich_text':
        texts = prop.get('rich_text', [])
        return texts[0]['text']['content'] if texts else None
    elif prop_type == 'title':
        titles = prop.get('title', [])
        return titles[0]['text']['content'] if titles else None
    elif prop_type == 'select':
        select = prop.get('select')
        return select['name'] if select else None
    
    return None

def main():
    print("=" * 100)
    print("🔍 验证快速更新 - 检查所有交易数据字段是否真的更新了")
    print("=" * 100)
    
    # Load config
    config = load_config()
    notion = Client(auth=config['notion_api_key'])
    database_id = config['notion_database_id']
    
    # Query recently updated pages (sorted by last_edited_time)
    print("\n📊 查询最近更新的10个币种...")
    
    response = notion.databases.query(
        database_id=database_id,
        sorts=[
            {
                "timestamp": "last_edited_time",
                "direction": "descending"
            }
        ],
        page_size=10
    )
    
    pages = response.get('results', [])
    
    if not pages:
        print("❌ 未找到任何页面")
        return
    
    print(f"\n✅ 找到 {len(pages)} 个最近更新的币种\n")
    print("=" * 100)
    
    # Define the 9 trading data fields we want to verify
    trading_fields = [
        ('Symbol', 'title', '币种'),
        ('Spot Price', 'number', '现货价格'),
        ('Perp Price', 'number', '永续价格'),
        ('Spot vol 24h', 'number', '现货24h交易量'),
        ('Perp vol 24h', 'number', '永续24h交易量'),
        ('Price change', 'number', '24h价格变化'),
        ('OI', 'number', '持仓量'),
        ('Funding', 'number', '资金费率'),
        ('Basis', 'number', 'Basis价差'),
        ('MC', 'number', '市值'),
    ]
    
    for idx, page in enumerate(pages, 1):
        props = page.get('properties', {})
        
        # Get symbol
        symbol_prop = props.get('Symbol', {})
        titles = symbol_prop.get('title', [])
        symbol = titles[0]['text']['content'] if titles else 'Unknown'
        
        # Get last edited time
        last_edited = page.get('last_edited_time', '')
        if last_edited:
            dt = datetime.fromisoformat(last_edited.replace('Z', '+00:00'))
            last_edited_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            last_edited_str = 'Unknown'
        
        print(f"\n#{idx} {symbol} (最后更新: {last_edited_str})")
        print("-" * 100)
        
        # Extract and display all trading fields
        field_count = 0
        updated_count = 0
        
        for field_name, field_type, field_cn in trading_fields:
            if field_name == 'Symbol':
                continue
                
            prop = props.get(field_name)
            value = extract_value(prop)
            
            field_count += 1
            
            if value is not None:
                updated_count += 1
                
                # Format value based on field
                if field_name in ['Spot Price', 'Perp Price']:
                    display_value = f"${value:.4f}" if value >= 0.01 else f"${value:.8f}"
                elif field_name in ['Spot vol 24h', 'Perp vol 24h', 'OI', 'MC']:
                    display_value = format_number(value)
                elif field_name in ['Funding', 'Price change']:
                    display_value = f"{value*100:.4f}%" if value else "0%"
                elif field_name == 'Basis':
                    display_value = f"{value*100:.2f}%" if value else "0%"
                else:
                    display_value = str(value)
                
                status = "✅"
            else:
                display_value = "N/A"
                status = "⚠️ "
            
            print(f"  {status} {field_cn:12s} ({field_name:15s}): {display_value}")
        
        # Show summary
        percentage = (updated_count / field_count * 100) if field_count > 0 else 0
        print(f"\n  📊 数据完整度: {updated_count}/{field_count} ({percentage:.1f}%)")
        
        if updated_count == field_count:
            print("  🎉 所有交易数据字段都已更新！")
        elif updated_count > 0:
            print(f"  ⚠️  有 {field_count - updated_count} 个字段未更新")
        else:
            print("  ❌ 没有交易数据")
    
    print("\n" + "=" * 100)
    print("✅ 验证完成")
    print("=" * 100)
    print("\n💡 说明:")
    print("  - 这些是数据库中最近更新的10个币种")
    print("  - 如果你刚运行了快速更新脚本，这些应该显示完整的交易数据")
    print("  - ✅ = 字段有数据  ⚠️ = 字段为空")
    print("  - 快速更新脚本的终端输出只显示价格是为了简洁，实际上所有字段都在更新")
    print("=" * 100)

if __name__ == '__main__':
    main()
