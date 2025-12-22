#!/usr/bin/env python3
"""
每日行情总结脚本
功能：
1. 从主数据库读取所有币种的当前数据
2. 筛选出涨跌幅前5名和后5名
3. 写入"每日行情"数据库

使用方法：
python3 scripts/daily_market_summary.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import List, Dict

# 配置文件路径
BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "config" / "config.json"
DAILY_MARKET_CONFIG = BASE_DIR / "config" / "daily_market_config.json"


def load_config():
    """加载配置"""
    with CONFIG_FILE.open('r') as f:
        config = json.load(f)
    
    # 加载每日行情数据库配置
    if DAILY_MARKET_CONFIG.exists():
        with DAILY_MARKET_CONFIG.open('r') as f:
            daily_config = json.load(f)
            config['daily_market_database_id'] = daily_config.get('database_id')
    else:
        print("⚠️  未找到每日行情数据库配置！")
        print(f"请创建配置文件：{DAILY_MARKET_CONFIG}")
        print("格式：")
        print('{')
        print('  "database_id": "your_daily_market_database_id"')
        print('}')
        sys.exit(1)
    
    return config


def get_all_symbols_from_notion(notion_token: str, database_id: str) -> tuple:
    """从主数据库读取所有币种数据"""
    print("📥 正在读取主数据库...")
    
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    url = f"https://api.notion.com/v1/databases/{database_id}/query"

    # Build a session that does not trust environment proxies and has retries
    session = requests.Session()
    session.headers.update(headers)
    session.trust_env = False  # ignore system/OS proxy env vars to avoid unexpected proxy use

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=(429, 502, 503, 504),
        allowed_methods=("GET", "POST")
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    all_pages = []
    has_more = True
    start_cursor = None

    try:
        while has_more:
            payload = {}
            if start_cursor:
                payload["start_cursor"] = start_cursor

            # Use session.post which will automatically retry per strategy
            try:
                resp = session.post(url, json=payload, timeout=30)
                resp.raise_for_status()
            except requests.exceptions.ProxyError as e:
                # Proxy errors are often environmental (VPN/proxy/firewall). If we have some pages
                # already collected return them with a warning; otherwise re-raise for visibility.
                if all_pages:
                    print(f"⚠️  Warning: Notion proxy error during pagination, returning {len(all_pages)} pages collected so far: {e}")
                    return all_pages
                else:
                    raise
            except requests.exceptions.RequestException as e:
                # For other request errors, try to surface a helpful message
                if all_pages:
                    print(f"⚠️  Warning: Notion request failed, returning {len(all_pages)} pages collected so far: {e}")
                    return all_pages
                else:
                    raise

            data = resp.json()
            all_pages.extend(data.get('results', []))
            has_more = data.get('has_more', False)
            start_cursor = data.get('next_cursor')

    except Exception as exc:
        # Bubble up a clearer error for the caller if nothing was collected
        print(f"\n❌ 无法从 Notion 读取页面: {exc}")
        print("建议检查：Notion token、网络/VPN/系统代理设置，或将 session.trust_env 设置为 True 以使用环境代理。")
        raise

    fetch_time = datetime.now()
    print(f"✅ 读取到 {len(all_pages)} 个币种 (fetch_time={fetch_time.isoformat()})")
    return all_pages, fetch_time


def extract_symbol_data(pages: List[Dict]) -> List[Dict]:
    """提取币种数据：Symbol, Price Change%, Current Price"""
    symbols_data = []
    
    for page in pages:
        props = page['properties']
        
        # 获取 Symbol
        symbol_prop = props.get('Symbol', {})
        if symbol_prop.get('type') == 'title':
            texts = symbol_prop.get('title', [])
            if not texts:
                continue
            symbol = texts[0].get('plain_text', '').strip()
        else:
            continue
        
        if not symbol:
            continue
        
        # 获取 Price change
        price_change = None
        price_change_prop = props.get('Price change', {})
        if price_change_prop.get('type') == 'number':
            price_change = price_change_prop.get('number')
        
        if price_change is None:
            continue
        
        # 只扫描有 Perp Price 的币种
        perp_price = None
        perp_price_prop = props.get('Perp Price', {})
        if perp_price_prop.get('type') == 'number':
            perp_price = perp_price_prop.get('number')
        
        # 必须有 Perp Price 才计入统计
        if perp_price is None:
            continue
        
        symbols_data.append({
            'symbol': symbol,
            'price_change': price_change,
            'perp_price': perp_price
        })
    
    return symbols_data


def get_top_movers(symbols_data: List[Dict], top_n: int = 5) -> Dict:
    """获取涨跌幅前N名"""
    # 按涨跌幅排序
    sorted_data = sorted(symbols_data, key=lambda x: x['price_change'], reverse=True)
    
    top_gainers = sorted_data[:top_n]
    top_losers = sorted_data[-top_n:][::-1]  # 反转，让最大跌幅排在前面
    
    return {
        'gainers': top_gainers,
        'losers': top_losers
    }


def create_daily_summary(config, top_gainers, top_losers, header_time: datetime = None):
    """创建每日总结到 Notion（一条记录包含所有信息）"""
    
    notion_token = config['notion']['api_key']
    daily_db_id = config.get('daily_market_database_id')
    
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # 使用传入的获取数据时间作为表头时间（fallback 到当前时间）
    if header_time is None:
        header_time = datetime.now()
    date_str = header_time.strftime("%Y-%m-%d %H:%M")
    
    print(f"\n📊 {date_str} 行情总结")
    print("=" * 70)
    
    # 构建涨幅榜文本（不包含标题）
    gainers_text = ""
    print("\n🚀 涨幅榜 Top 5:")
    for i, item in enumerate(top_gainers, 1):
        symbol = item['symbol']
        change = item['price_change'] * 100  # 转换为百分比
        gainers_text += f"{i}. {symbol} +{change:.2f}%\n"
        print(f"  {i}. {symbol:12s} +{change:6.2f}%")
    
    # 构建跌幅榜文本（不包含标题）
    losers_text = ""
    print("\n📉 跌幅榜 Top 5:")
    for i, item in enumerate(top_losers, 1):
        symbol = item['symbol']
        change = item['price_change'] * 100  # 转换为百分比
        losers_text += f"{i}. {symbol} {change:.2f}%\n"
        print(f"  {i}. {symbol:12s} {change:6.2f}%")
    
    # 合并成一条记录
    combined_text = gainers_text + losers_text
    
    # 创建单条 Notion 页面
    page_data = {
        "parent": {"database_id": daily_db_id},
        "properties": {
            "Date": {
                "title": [
                    {
                        "text": {
                            "content": date_str
                        }
                    }
                ]
            },
            "涨幅前5": {
                "rich_text": [
                    {
                        "text": {
                            "content": gainers_text.strip()
                        }
                    }
                ]
            },
            "跌幅前5": {
                "rich_text": [
                    {
                        "text": {
                            "content": losers_text.strip()
                        }
                    }
                ]
            }
        }
    }
    
    try:
        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json=page_data
        )
        if response.status_code == 200:
            print(f"\n✅ 已写入 Notion（1条记录）")
        else:
            print(f"\n❌ 写入失败: {response.text}")
    except Exception as e:
        print(f"\n❌ 写入出错: {str(e)}")


def main():
    print("=" * 80)
    print("📊 每日行情总结脚本")
    print("=" * 80)
    
    # 加载配置
    config = load_config()
    
    notion_token = config['notion']['api_key']
    main_db_id = config['notion']['database_id']
    daily_db_id = config.get('daily_market_database_id')
    
    if not daily_db_id:
        print("❌ 未配置每日行情数据库ID！")
        sys.exit(1)
    
    # 读取主数据库，并获取读取时的时间
    all_pages, fetch_time = get_all_symbols_from_notion(notion_token, main_db_id)

    # 仅保留在 fetch_time 当天有更新的页面（根据 last_edited_time / created_time）
    fetch_date_iso = fetch_time.date().isoformat()
    pages_today = []
    for p in all_pages:
        last_ts = p.get('last_edited_time') or p.get('created_time')
        if last_ts and last_ts.startswith(fetch_date_iso):
            pages_today.append(p)

    print(f"📥 共读取 {len(all_pages)} 个页面，{fetch_date_iso} 有更新的页面: {len(pages_today)} 个")

    # 提取数据（只从今天有更新的页面）
    symbols_data = extract_symbol_data(pages_today)
    print(f"📊 有效数据：{len(symbols_data)} 个币种")
    
    if len(symbols_data) == 0:
        print("❌ 没有有效数据！")
        sys.exit(1)
    
    # 获取涨跌幅前5名
    top_movers = get_top_movers(symbols_data, top_n=5)
    
    # 创建每日总结，使用 fetch_time 作为表头时间
    create_daily_summary(config, top_movers['gainers'], top_movers['losers'], header_time=fetch_time)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
