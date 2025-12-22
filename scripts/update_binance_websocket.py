#!/usr/bin/env python3
"""
使用 WebSocket 更新 Binance 数据到 Notion
解决 REST API 速率限制问题

优势:
- 无速率限制
- 实时数据更新
- 单个连接订阅所有币种
"""

import json
import asyncio
import websockets
import time
import subprocess
from pathlib import Path
from typing import Dict, Set
from datetime import datetime

# Configuration
BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / 'config' / 'config.json'
CMC_MAPPING_FILE = BASE_DIR / 'config' / 'binance_cmc_mapping.json'

class BinanceWebSocketClient:
    """Binance WebSocket 客户端"""
    
    def __init__(self):
        self.spot_ws = "wss://stream.binance.com:9443/ws"
        self.perp_ws = "wss://fstream.binance.com/ws"
        self.data_cache = {}
        self.proxy_disabled = False
        
    def disable_proxy(self):
        """临时禁用系统proxy（仅在需要时调用一次）"""
        if not self.proxy_disabled:
            try:
                subprocess.run(['networksetup', '-setsocksfirewallproxystate', 'Wi-Fi', 'off'], 
                             capture_output=True, check=False)
                self.proxy_disabled = True
            except:
                pass  # 如果失败，忽略
    
    def restore_proxy(self):
        """恢复系统proxy"""
        if self.proxy_disabled:
            try:
                subprocess.run(['networksetup', '-setsocksfirewallproxystate', 'Wi-Fi', 'on'], 
                             capture_output=True, check=False)
                self.proxy_disabled = False
            except:
                pass
        
    async def subscribe_combined_streams(self, symbols: list):
        """订阅组合数据流"""
        
        # 构建订阅流名称
        streams = []
        for symbol in symbols:
            symbol_lower = symbol.lower()
            # Spot 24hr ticker
            streams.append(f"{symbol_lower}usdt@ticker")
            # Perp 24hr ticker
            streams.append(f"{symbol_lower}usdt@ticker")
            # Mark price & funding rate
            streams.append(f"{symbol_lower}usdt@markPrice")
        
        # Binance WebSocket 限制：每个连接最多 200 个流
        # 我们需要分批订阅
        batch_size = 50  # 每批 50 个币种 = 150 个流
        
        print(f"📊 总共 {len(symbols)} 个币种")
        print(f"📦 分成 {(len(symbols) + batch_size - 1) // batch_size} 批订阅")
        print()
        
        tasks = []
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            task = self.subscribe_batch(batch, i // batch_size + 1)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
    
    async def subscribe_batch(self, symbols: list, batch_num: int):
        """订阅一批币种的数据流"""
        
        # 构建合约 WebSocket URL
        streams = []
        for symbol in symbols:
            symbol_lower = symbol.lower()
            streams.append(f"{symbol_lower}usdt@ticker")
            streams.append(f"{symbol_lower}usdt@markPrice")
        
        stream_names = '/'.join(streams)
        url = f"{self.perp_ws}/stream?streams={stream_names}"
        
        print(f"🔌 批次 {batch_num}: 连接 WebSocket...")
        print(f"   币种: {', '.join(symbols[:5])}...")
        
        # 临时禁用系统proxy
        self.disable_proxy()
        
        try:
            async with websockets.connect(url, ping_interval=20, close_timeout=10) as websocket:
                print(f"✅ 批次 {batch_num}: 已连接")
                
                # 接收并处理消息
                message_count = 0
                start_time = time.time()
                
                async for message in websocket:
                    data = json.loads(message)
                    
                    if 'data' in data:
                        stream_data = data['data']
                        event_type = stream_data.get('e')
                        
                        if event_type == '24hrTicker':
                            # 24小时价格变动统计
                            self.process_ticker(stream_data)
                        elif event_type == 'markPriceUpdate':
                            # Mark 价格和资金费率
                            self.process_mark_price(stream_data)
                        
                        message_count += 1
                        
                        # 每收到 100 条消息显示一次进度
                        if message_count % 100 == 0:
                            elapsed = time.time() - start_time
                            rate = message_count / elapsed
                            print(f"   批次 {batch_num}: 收到 {message_count} 条消息 ({rate:.1f} msg/s)")
                    
                    # 收集足够数据后可以更新 Notion
                    if message_count >= len(symbols) * 2:  # 每个币种至少 2 条消息
                        print(f"✅ 批次 {batch_num}: 数据收集完成，共 {message_count} 条消息")
                        break
                        
        except Exception as e:
            print(f"❌ 批次 {batch_num}: WebSocket 错误: {e}")
    
    def process_ticker(self, data: dict):
        """处理 24hr ticker 数据"""
        symbol = data['s'].replace('USDT', '')
        
        if symbol not in self.data_cache:
            self.data_cache[symbol] = {}
        
        self.data_cache[symbol].update({
            'price': float(data['c']),  # 最新价格
            'price_change_24h': float(data['p']),  # 24h 价格变动
            'price_change_pct': float(data['P']),  # 24h 价格变动百分比
            'volume_24h': float(data['q']),  # 24h 成交量（USDT）
            'high_24h': float(data['h']),  # 24h 最高价
            'low_24h': float(data['l']),  # 24h 最低价
            'timestamp': data['E']
        })
    
    def process_mark_price(self, data: dict):
        """处理 mark price 和 funding rate 数据"""
        symbol = data['s'].replace('USDT', '')
        
        if symbol not in self.data_cache:
            self.data_cache[symbol] = {}
        
        self.data_cache[symbol].update({
            'mark_price': float(data['p']),  # Mark 价格
            'index_price': float(data['i']),  # 指数价格
            'funding_rate': float(data['r']),  # 资金费率
            'next_funding_time': data['T']
        })
    
    def get_symbol_data(self, symbol: str) -> dict:
        """获取币种数据"""
        return self.data_cache.get(symbol, {})
    
    def get_all_data(self) -> dict:
        """获取所有数据"""
        return self.data_cache


async def main():
    """主函数"""
    
    print("=" * 80)
    print("🚀 Binance WebSocket 数据收集器")
    print("=" * 80)
    print()
    
    # 加载币种列表
    with open(CMC_MAPPING_FILE, 'r') as f:
        cmc_data = json.load(f)
        if 'mapping' in cmc_data:
            symbols = list(cmc_data['mapping'].keys())
        else:
            symbols = list(cmc_data.keys())
    
    print(f"📊 总共 {len(symbols)} 个币种需要订阅")
    print()
    
    # 创建 WebSocket 客户端
    client = BinanceWebSocketClient()
    
    # 订阅数据流
    print("🔌 开始订阅 WebSocket 数据流...")
    print()
    
    try:
        await client.subscribe_combined_streams(symbols[:100])  # 先测试 100 个币种
    finally:
        # 确保恢复proxy
        client.restore_proxy()
    
    # 显示收集到的数据
    print()
    print("=" * 80)
    print("📊 数据收集完成")
    print("=" * 80)
    print()
    
    all_data = client.get_all_data()
    print(f"✅ 成功收集 {len(all_data)} 个币种的数据")
    print()
    
    # 显示前 5 个币种的数据作为示例
    print("示例数据（前 5 个币种）:")
    for i, (symbol, data) in enumerate(list(all_data.items())[:5]):
        print(f"\n{symbol}:")
        for key, value in data.items():
            print(f"  {key}: {value}")
    
    # 保存数据到文件
    output_file = BASE_DIR / 'data' / 'websocket_data.json'
    with open(output_file, 'w') as f:
        json.dump(all_data, f, indent=2)
    
    print()
    print(f"💾 数据已保存到: {output_file}")
    print()
    
    # 接下来可以将数据更新到 Notion
    print("下一步: 将数据更新到 Notion")
    print("运行: python3 scripts/update_notion_from_websocket.py")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
