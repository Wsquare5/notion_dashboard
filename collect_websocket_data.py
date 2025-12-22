#!/usr/bin/env python3
"""
使用 WebSocket 收集所有币种的 Binance 数据
避免 REST API 速率限制

完全替代 REST API:
- 无速率限制
- 实时数据
- 支持所有618个币种
"""

import json
import asyncio
import websockets
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Configuration
BASE_DIR = Path(__file__).parent
CMC_MAPPING_FILE = BASE_DIR / 'config' / 'binance_cmc_mapping.json'

async def collect_token_data(symbols: list, duration: int = 30):
    """
    通过 WebSocket 收集币种数据
    
    Args:
        symbols: 币种列表（不含 USDT 后缀）
        duration: 收集时长（秒）
    """
    
    # 构建 WebSocket URL
    streams = []
    for symbol in symbols:
        symbol_lower = symbol.lower()
        streams.append(f"{symbol_lower}usdt@ticker")
        streams.append(f"{symbol_lower}usdt@markPrice")
    
    stream_names = '/'.join(streams)
    url = f"wss://fstream.binance.com/stream?streams={stream_names}"
    
    # 数据缓存
    data_cache = {}
    
    print(f"🔌 连接 Binance WebSocket (将使用系统代理)...")
    print(f"📊 币种: {', '.join(symbols)}")
    print(f"⏱️  收集时长: {duration} 秒")
    print()
    
    try:
        async with websockets.connect(url) as ws:
            print("✅ WebSocket 连接成功！")
            print("📡 接收数据中...\n")
            
            start_time = asyncio.get_event_loop().time()
            message_count = 0
            
            async for message in ws:
                # 检查是否超时
                if asyncio.get_event_loop().time() - start_time > duration:
                    print(f"\n⏱️  已收集 {duration} 秒数据，停止接收")
                    break
                
                try:
                    data = json.loads(message)
                    
                    if 'data' not in data:
                        continue
                    
                    stream_data = data['data']
                    event_type = stream_data.get('e')
                    symbol = stream_data.get('s', '').replace('USDT', '')
                    
                    if symbol not in data_cache:
                        data_cache[symbol] = {}
                    
                    if event_type == '24hrTicker':
                        # 24小时价格统计
                        data_cache[symbol].update({
                            'symbol': symbol,
                            'price': float(stream_data.get('c', 0)),
                            'high_24h': float(stream_data.get('h', 0)),
                            'low_24h': float(stream_data.get('l', 0)),
                            'volume_24h': float(stream_data.get('v', 0)),
                            'quote_volume_24h': float(stream_data.get('q', 0)),
                            'price_change_24h': float(stream_data.get('p', 0)),
                            'price_change_percent_24h': float(stream_data.get('P', 0)),
                            'last_update': datetime.now().isoformat()
                        })
                        
                        message_count += 1
                        print(f"📊 {symbol}: ${data_cache[symbol]['price']:,.4f}, "
                              f"24h {data_cache[symbol]['price_change_percent_24h']:+.2f}%, "
                              f"成交量 {data_cache[symbol]['volume_24h']:,.0f}")
                    
                    elif event_type == 'markPriceUpdate':
                        # 标记价格和资金费率
                        data_cache[symbol].update({
                            'mark_price': float(stream_data.get('p', 0)),
                            'funding_rate': float(stream_data.get('r', 0)),
                            'next_funding_time': stream_data.get('T')
                        })
                
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"⚠️  处理消息出错: {e}")
                    continue
            
            print(f"\n✅ 总共接收 {message_count} 条消息")
            
    except Exception as e:
        print(f"\n❌ WebSocket 连接错误: {e}")
        return None
    
    return data_cache


async def collect_all_tokens(batch_size: int = 66, duration: int = 30):
    """
    收集所有币种的数据
    batch_size: 每批币种数量（66个币种 × 2个流 = 132个流 < 200限制）
    """
    
    # 加载所有币种
    with open(CMC_MAPPING_FILE, 'r') as f:
        cmc_data = json.load(f)
        if 'mapping' in cmc_data:
            all_symbols = list(cmc_data['mapping'].keys())
        else:
            all_symbols = list(cmc_data.keys())
    
    print(f"📊 总共 {len(all_symbols)} 个币种")
    print(f"📦 每批 {batch_size} 个币种（{batch_size * 2} 个流）")
    print(f"⏱️  每批收集 {duration} 秒")
    print()
    
    # 分批处理
    all_data = {}
    num_batches = (len(all_symbols) + batch_size - 1) // batch_size
    
    for i in range(0, len(all_symbols), batch_size):
        batch_num = i // batch_size + 1
        batch_symbols = all_symbols[i:i + batch_size]
        
        print(f"🔄 批次 {batch_num}/{num_batches}: {len(batch_symbols)} 个币种")
        print(f"   {', '.join(batch_symbols[:5])}...")
        
        batch_data = await collect_token_data(batch_symbols, duration)
        
        if batch_data:
            all_data.update(batch_data)
            print(f"✅ 批次 {batch_num} 完成，已收集 {len(batch_data)} 个币种")
        else:
            print(f"⚠️  批次 {batch_num} 失败")
        
        print()
        
        # 批次之间短暂延迟
        if i + batch_size < len(all_symbols):
            await asyncio.sleep(2)
    
    return all_data


async def main():
    """主函数"""
    
    # 检查系统代理状态
    try:
        result = subprocess.run(['networksetup', '-getsocksfirewallproxy', 'Wi-Fi'], 
                               capture_output=True, text=True)
        if "Enabled: Yes" in result.stdout:
            print("✅ 检测到系统SOCKS代理已开启，将通过代理连接。")
        else:
            print("⚠️  未检测到系统SOCKS代理，将尝试直接连接。")
    except:
        pass # 忽略检查错误
    print()

    try:
        # 检查命令行参数
        if len(sys.argv) > 1:
            # 指定币种模式
            symbols = [s.upper() for s in sys.argv[1:]]
            print(f"🎯 指定币种模式: {len(symbols)} 个币种")
            print()
            data = await collect_token_data(symbols, duration=30)
        else:
            # 全量收集模式
            print("🌐 全量收集模式：收集所有币种")
            print()
            data = await collect_all_tokens(batch_size=66, duration=30)
        
        if data:
            print("\n" + "=" * 80)
            print("📋 收集结果汇总")
            print("=" * 80 + "\n")
            
            # 仅显示部分结果以避免刷屏
            count = 0
            for symbol, info in data.items():
                if count >= 10:
                    print("... (结果过多，仅显示前10条)")
                    break
                print(f"【{symbol}】")
                if 'price' in info:
                    print(f"  当前价格: ${info['price']:,.4f}")
                    print(f"  24h 涨跌: {info['price_change_percent_24h']:+.2f}%")
                    print(f"  24h 成交量: {info['volume_24h']:,.0f}")
                if 'funding_rate' in info:
                    print(f"  资金费率: {info['funding_rate']:.6f}%")
                print()
                count += 1
            
            # 保存到文件
            output_file = 'data/websocket_collected_data.json'
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"✅ 数据已保存到: {output_file}")
        else:
            print("❌ 未收集到数据")
    
    except Exception as e:
        print(f"程序主流程发生错误: {e}")


if __name__ == '__main__':
    asyncio.run(main())
