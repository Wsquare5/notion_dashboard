# 推荐更新计划

## 问题分析

- 网络代理连接不稳定，容易出现 `ConnectionResetError(54, 'Connection reset by peer')`
- Notion API 有速率限制（约 3-5 请求/秒）
- 625 个币种全量更新需要大量 API 调用

## 推荐更新频率

⚠️ **重要：所有币种必须同时更新**，确保数据时间点一致，便于纵向比较。

### 1. CMC 基础数据（流通量、供应量、FDV）

```bash
# 每天 1 次 - 凌晨 2:00
# 预计耗时：~3-5 分钟（625 个币种）
0 2 * * * cd /Users/wanjinwoo/Desktop/Work/trading/Binance && python3 scripts/sync_cmc_to_notion.py >> logs/cmc_daily.log 2>&1
```

**原因：**

- Circulating Supply 每天变化不大
- 减少 CMC API 调用（有月度限额）
- 为当天的 MC 计算提供最新流通量

### 2. Binance 交易数据（价格、成交量、OI、Funding、MC）

```bash
# 每 6 小时 1 次 - 2:30, 8:30, 14:30, 20:30
# 预计耗时：~5-8 分钟（625 个币种 + 200ms 延迟）
30 2,8,14,20 * * * cd /Users/wanjinwoo/Desktop/Work/trading/Binance && python3 scripts/update_binance_trading_data.py >> logs/binance_$(date +\%Y\%m\%d_\%H).log 2>&1
```

**原因：**

- 价格和成交量实时性要求较高
- 6 小时间隔足够追踪趋势
- **所有币种在同一批次更新，确保数据时间点一致**
- 每个请求间隔 200ms，避免代理连接重置

## 代码改进

### ✅ 已添加功能

1. **请求间隔**：每 10 个币种暂停 500ms，避免触发速率限制
2. **自动重试**：失败的币种最多重试 5 轮（已有功能）
3. **错误恢复**：网络错误时跳过，不中断整个流程

### 🔄 其他优化建议

#### A. 调整请求延迟（根据网络稳定性）

**当前设置：每个币种间隔 200ms**

- 总耗时：625 × 0.2s = 125s ≈ 2 分钟额外延迟
- 加上 API 请求时间，预计总共 5-8 分钟

**如果仍出现大量连接错误，可以增加延迟：**

修改 `update_binance_trading_data.py` 第 665 行：

```python
# 方案 1：增加到 300ms（推荐）
if i > 1:
    time.sleep(0.3)  # 总耗时约 3 分钟额外延迟

# 方案 2：增加到 500ms（更稳定）
if i > 1:
    time.sleep(0.5)  # 总耗时约 5 分钟额外延迟
```

**权衡：**

- ✅ 延迟越大，网络错误越少
- ❌ 延迟越大，总耗时越长
- 💡 建议：先用 200ms 测试，如果错误率 >5%，再增加到 300-500ms

## 手动运行建议

### 完整更新（首次或修复数据）

```bash
# 1. 先更新 CMC 基础数据
python3 scripts/sync_cmc_to_notion.py

# 2. 等待 5 分钟（避免速率限制）
sleep 300

# 3. 更新 Binance 交易数据
python3 scripts/update_binance_trading_data.py
```

### 测试单个币种

```bash
# 测试前先确认网络连接
DRY_SYMBOLS=BTC,ETH,SOL python3 scripts/update_binance_trading_data.py
```

## 监控建议

### 检查日志中的错误

```bash
# 统计错误次数
grep "❌" logs/binance_*.log | wc -l

# 查看哪些币种频繁失败
grep "⚠️  Notion query failed" logs/binance_*.log | cut -d']' -f2 | sort | uniq -c | sort -rn

# 查看网络错误类型
grep "ConnectionResetError\|ProxyError\|TimeoutError" logs/binance_*.log
```

### 健康检查脚本

```bash
# 检查有多少币种缺少最新数据（超过 12 小时未更新）
python3 << 'EOF'
import requests, json
from datetime import datetime, timedelta

config = json.load(open('config.json'))
headers = {'Authorization': f"Bearer {config['notion']['api_key']}", 'Notion-Version': '2022-06-28'}

# 查询所有页面
url = f"https://api.notion.com/v1/databases/{config['notion']['database_id']}/query"
res = requests.post(url, headers=headers, json={}, timeout=30)
pages = res.json()['results']

outdated = []
for p in pages:
    last_edited = datetime.fromisoformat(p['last_edited_time'].replace('Z', '+00:00'))
    if datetime.now(last_edited.tzinfo) - last_edited > timedelta(hours=12):
        symbol = p['properties']['Symbol']['title'][0]['text']['content']
        outdated.append(symbol)

print(f"超过 12 小时未更新的币种数量: {len(outdated)}")
if outdated[:10]:
    print(f"示例: {', '.join(outdated[:10])}")
EOF
```

## 总结

### ✅ 推荐方案：所有币种同时更新

**更新频率：**

- CMC 数据：每天 1 次（凌晨 2:00）
- Binance 数据：每 6 小时 1 次（2:30, 8:30, 14:30, 20:30）

**优势：**

- ✅ 所有币种数据时间点一致，方便纵向比较
- ✅ 每个请求间隔 200ms，避免代理连接重置
- ✅ 自动重试机制（最多 5 轮），确保数据完整性
- ✅ 预计每次更新 5-8 分钟完成

**性能估算：**

```
625 个币种 × (Binance API 调用 + CMC API 调用 + Notion 更新)
= 625 × (0.2s Binance + 0.1s CMC + 0.3s Notion + 0.2s 延迟)
≈ 500 秒 = 8 分钟
```

**如果网络仍不稳定：**

1. 增加延迟到 300-500ms（总耗时 10-15 分钟）
2. 改为每 12 小时更新一次，减少总请求次数
3. 监控日志，找出频繁失败的币种单独处理
