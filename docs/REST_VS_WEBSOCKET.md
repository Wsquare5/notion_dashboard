# REST API vs WebSocket 对比

## 当前使用的 REST API

### API 端点

你的脚本使用以下 Binance REST API 端点：

**Spot（现货）:**

- `GET /api/v3/exchangeInfo` - 获取交易对信息（40 权重）
- `GET /api/v3/ticker/24hr` - 获取 24 小时价格统计（40 权重/symbol）

**Futures（合约）:**

- `GET /fapi/v1/exchangeInfo` - 获取合约信息（40 权重）
- `GET /fapi/v1/ticker/24hr` - 获取 24 小时价格统计（40 权重/symbol）
- `GET /fapi/v1/premiumIndex` - 获取资金费率和标记价格（10 权重/symbol）
- `GET /fapi/v1/openInterest` - 获取持仓量（1 权重/symbol）
- `GET /fapi/v1/fundingRate` - 获取历史资金费率（1 权重/symbol）
- `GET /fapi/v1/constituents` - 获取指数成分（可选）

### 问题

- **权重限制**: 2,400 权重/分钟（无 API Key）
- **你的使用量**: 32,216 权重（618 个币种）
- **超出倍数**: 13.4x
- **结果**: IP 被封禁 1-2 小时

## WebSocket 方案

### 优势

1. **无速率限制** - 可以订阅任意数量的币种
2. **实时数据** - 数据推送，无需轮询
3. **单连接** - 一个连接订阅多个数据流
4. **低延迟** - 毫秒级数据更新

### WebSocket 流

**Futures（推荐）:**

```
wss://fstream.binance.com/ws/<symbol>@ticker
wss://fstream.binance.com/ws/<symbol>@markPrice
wss://fstream.binance.com/ws/<symbol>@forceOrder
```

**Spot:**

```
wss://stream.binance.com:9443/ws/<symbol>@ticker
wss://stream.binance.com:9443/ws/<symbol>@depth
```

### 数据示例

**24hr Ticker (价格统计):**

```json
{
  "e": "24hrTicker",
  "E": 1672515782136,
  "s": "BTCUSDT",
  "p": "500.00", // 价格变动
  "P": "2.11", // 价格变动百分比
  "c": "24100.00", // 最新价格
  "h": "24800.00", // 最高价
  "l": "23600.00", // 最低价
  "v": "123456.78", // 成交量（BTC）
  "q": "2987654321" // 成交额（USDT）
}
```

**Mark Price (资金费率):**

```json
{
  "e": "markPriceUpdate",
  "E": 1672515782136,
  "s": "BTCUSDT",
  "p": "24100.00", // Mark 价格
  "i": "24095.00", // 指数价格
  "r": "0.0001", // 资金费率
  "T": 1672531200000 // 下次结算时间
}
```

## 对比表

| 特性       | REST API           | WebSocket        |
| ---------- | ------------------ | ---------------- |
| 速率限制   | 2,400 权重/分钟    | 无限制           |
| 数据更新   | 轮询（手动请求）   | 推送（实时）     |
| 延迟       | 高（需要等待响应） | 低（毫秒级）     |
| 连接数     | 每个请求一个       | 单连接订阅多个流 |
| 适用场景   | 一次性查询         | 持续监控         |
| 被封禁风险 | 高（超限即封）     | 无               |

## 迁移方案

### 方案 1: 完全切换到 WebSocket（推荐）

**优点:**

- 完全解决速率限制问题
- 实时数据更新
- 可以持续运行

**缺点:**

- 需要重构代码架构
- 需要维护长连接
- 历史数据需要单独获取

**实现步骤:**

1. 创建 WebSocket 客户端
2. 订阅所有币种的数据流
3. 接收并缓存数据
4. 定时（如每 5 分钟）批量更新到 Notion

### 方案 2: 混合使用（临时方案）

**WebSocket 用于:**

- 价格数据（ticker）
- 资金费率（markPrice）

**REST API 用于:**

- 持仓量（openInterest）- 每天更新一次
- 资金费率周期（fundingRate）- 新币种时查询
- 指数成分（constituents）- 很少变化

**优点:**

- 大幅减少 REST API 请求
- 保留现有代码结构

**缺点:**

- 仍有被封禁风险（但概率低很多）

### 方案 3: 使用 Binance API Key

**优点:**

- REST API 限制提升到 6,000 权重/分钟
- 可以继续使用现有代码
- 实现简单

**缺点:**

- 仍有速率限制
- 需要 Binance 账号

## 推荐实施计划

### 阶段 1: 立即实施（解决当前问题）

1. 使用分批更新脚本 `update_with_rate_limit.py`
2. 减少更新频率（从每天 2 次改为 1 次）

### 阶段 2: 短期（1-2 周）

1. 测试 WebSocket 脚本 `scripts/update_binance_websocket.py`
2. 验证数据准确性
3. 创建 WebSocket → Notion 更新脚本

### 阶段 3: 长期（1 个月）

1. 完全切换到 WebSocket
2. 实现实时数据更新
3. 添加监控和告警

## 测试 WebSocket

### 测试脚本

```bash
# 测试 WebSocket 连接和数据接收
python3 scripts/update_binance_websocket.py

# 预期输出：
# - 成功连接到 WebSocket
# - 接收实时数据
# - 保存到 data/websocket_data.json
```

### 验证数据

```bash
# 查看收集到的数据
cat data/websocket_data.json | jq '.' | head -50
```

## 常见问题

### Q: WebSocket 会断开吗？

A: 会，需要实现自动重连机制。Binance 建议每 24 小时重连一次。

### Q: 如何获取历史数据？

A: WebSocket 只提供实时数据。历史数据仍需使用 REST API 或数据库存储。

### Q: 一个连接可以订阅多少个流？

A: 单个连接最多 200 个流。618 个币种 × 2 个流 = 1,236 个流，需要 7 个连接。

### Q: WebSocket 的数据准确吗？

A: 是的，与 REST API 数据一致，甚至更新更及时。

## 参考资料

- [Binance WebSocket 文档](https://binance-docs.github.io/apidocs/futures/en/#websocket-market-streams)
- [Binance API 速率限制](https://binance-docs.github.io/apidocs/futures/en/#limits)
- [WebSocket 最佳实践](https://binance-docs.github.io/apidocs/futures/en/#general-info)
