# Binance API 速率限制说明

## 问题分析

### Binance API 官方限制

- **IP 限制**: 2,400 请求权重/分钟
- **请求权重**:
  - `exchangeInfo`: 40 权重
  - `ticker/24hr`: 40 权重（单个 symbol）
  - `premiumIndex`: 10 权重
  - `openInterest`: 1 权重
  - `fundingRate`: 1 权重

### 当前脚本的请求量

- 总币种数: **618 个**
- 每个币种需要: **52 权重**
  - Spot ticker: 40
  - Perp ticker: 40（已包含在 perp 请求中）
  - Premium Index: 10
  - Open Interest: 1
  - Funding Rate: 1
- **总权重**: 80 + (52 × 618) = **32,216 权重**
- **超出限制**: 13.4 倍

### 为什么会被封禁？

使用 20 个并发 workers，在 1-2 分钟内发送所有请求，瞬间超过 2,400 权重/分钟的限制，触发 IP 封禁。

## 解决方案

### 方案 1: 使用分批更新脚本（推荐）

```bash
# 自动分批处理，避免触发限制
python3 update_with_rate_limit.py

# 参数说明：
# - 每批 40 个币种
# - 每批间隔 90 秒
# - 总耗时约 23 分钟（618/40 = 16批 × 90秒）
```

### 方案 2: 手动分批更新

```bash
# 分批更新，每批 40 个币种
python3 update.py BTC ETH BNB SOL ... (40个) --workers 5

# 等待 90 秒

python3 update.py DOGE SHIB PEPE ... (40个) --workers 5

# 继续...
```

### 方案 3: 使用 Binance API Key（最佳）

1. 注册 Binance 账号并创建 API Key
2. API Key 用户限制提升到 **6,000 权重/分钟**
3. 在 `config/api_config.json` 中添加：

```json
{
  "binance": {
    "api_key": "your_api_key",
    "api_secret": "your_secret"
  }
}
```

4. 修改代码使用 API Key 认证

### 方案 4: 使用 WebSocket（长期方案）

- 订阅 WebSocket 流接收实时数据
- 无频率限制
- 需要重构代码架构

## 临时处理

### 如果已被封禁

1. **检查封禁时间**:

   ```bash
   # 封禁通常持续 10-120 分钟
   # 错误信息会包含解封时间戳
   ```

2. **切换网络**:

   - 使用 VPN
   - 切换到手机热点
   - 使用其他网络环境

3. **等待封禁解除**

### 当前封禁情况

如果看到 `418 I'm a teapot` 错误，说明被封禁。错误信息中包含解封时间戳（Unix 毫秒时间戳）。

## 最佳实践

### 日常更新建议

1. **使用分批脚本**: `python3 update_with_rate_limit.py`

   - 优点: 自动控制速率，不会触发封禁
   - 缺点: 需要 20-30 分钟完成

2. **减少更新频率**:

   - 从每天 2 次改为每天 1 次
   - 使用定时任务在低峰期运行

3. **只更新必要的币种**:

   ```bash
   # 只更新关注的币种
   python3 update.py BTC ETH BNB SOL
   ```

4. **使用缓存**:
   - exchangeInfo 结果缓存 1 小时
   - 减少不必要的初始化请求

## 监控和日志

### 查看请求统计

```bash
# 脚本会显示：
# - 总请求数
# - 失败次数
# - 耗时统计
```

### 错误类型

- `418`: IP 被封禁（请求过多）
- `429`: 速率限制（临时限制，会自动重试）
- `5xx`: Binance 服务器错误

## 未来改进

1. 实现请求权重计数器
2. 智能速率控制（动态调整并发数）
3. 切换到 WebSocket 实时数据
4. 添加 API Key 支持
5. 实现请求缓存层
