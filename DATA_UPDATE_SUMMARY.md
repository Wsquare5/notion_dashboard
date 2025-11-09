# 📊 Binance Trading Data Update Summary

## 运行命令

### 基本用法

```bash
# 更新所有币种（仅更新价格/交易量/资金费率等实时数据）⭐️ 推荐日常使用
python3 scripts/update_binance_trading_data.py

# 更新所有币种（同时更新元数据：供应量 + Funding Cycle）
python3 scripts/update_binance_trading_data.py --update-metadata

# 更新指定币种
python3 scripts/update_binance_trading_data.py BTC ETH SOL

# 更新指定币种（同时更新元数据）
python3 scripts/update_binance_trading_data.py --update-metadata BTC ETH SOL

# 向后兼容：--update-supply 仍可使用（等同于 --update-metadata）
python3 scripts/update_binance_trading_data.py --update-supply

# 查看帮助
python3 scripts/update_binance_trading_data.py --help
```

---

## 📈 每次更新的数据字段

### 1️⃣ **实时交易数据**（每次都更新）

#### Spot Market（现货市场）

- **Spot Price** - 现货价格
- **Spot vol 24h** - 现货 24 小时交易量（USDT）
- **Price change** - 24 小时价格变化（百分比，保存为小数）

#### Perpetual Futures（永续合约）

- **Perp Price** - 合约价格
- **Perp vol 24h** - 合约 24 小时交易量（USDT）
- **Funding** - 资金费率（正数表示多头付空头）
- **Funding Cycle** - 资金费率周期（1h/4h/8h，需要 `--update-metadata` 才会更新）
- **OI** (Open Interest) - 未平仓合约总价值（USD）
- **Basis** - 基差（合约价格与指数价格的差异）
- **Index Composition** - 指数组成（如果是混合指数）

### 2️⃣ **元数据**（仅在使用 `--update-metadata` 参数时更新）

#### Supply Data（供应量）

- **Circulating Supply** - 流通供应量（需要 `--update-metadata` 才会从 CMC 刷新）
- **Total Supply** - 总供应量（需要 `--update-metadata` 才会从 CMC 刷新）
- **Max Supply** - 最大供应量（需要 `--update-metadata` 才会从 CMC 刷新）
- **Funding Cycle** - 资金费率周期（1h/4h/8h，需要 `--update-metadata` 才会刷新）

**注意**：

- 默认情况下（不加 `--update-metadata`），MC 和 FDV 计算会使用 Notion 中已有的供应量数据
- Funding Cycle 不常变化，默认不更新，需要手动指定参数才会刷新

#### Market Cap（市值）

- **MC** (Market Cap) - 市值
  - 计算方式：`Circulating Supply × Price / Multiplier`
  - Price 优先级：Perp Price > Spot Price
  - 对于 1000X 和 1000000X 币种会自动除以对应的 multiplier
- **FDV** (Fully Diluted Valuation) - 完全稀释市值
  - 计算方式：`Total Supply × Price / Multiplier`
  - 同样支持 multiplier 币种

### 3️⃣ **Binance 分类标签**（每次都更新）

- **Categories** - 币种分类（Multi-select）
  - 来源：Binance Perpetual API 的 `underlyingSubType` 字段
  - 包含 23 个分类：
    - **AI** (65 个币种) - 人工智能项目
    - **DeFi** (145 个币种) - 去中心化金融
    - **Meme** (58 个币种) - Meme 币
    - **Layer-1** (62 个币种) - 一层公链
    - **Layer-2** (25 个币种) - 二层扩容
    - **Gaming** (32 个币种) - 游戏类
    - **Metaverse** (15 个币种) - 元宇宙
    - **NFT** (13 个币种) - NFT 相关
    - **Infrastructure** (66 个币种) - 基础设施
    - **PoW** (19 个币种) - 工作量证明
    - **Payment** (9 个币种) - 支付类
    - **Storage** (12 个币种) - 存储类
    - **Index** (3 个币种) - 指数产品
    - **Pre-Market** (3 个币种) - 盘前交易
    - **Alpha** (34 个币种) - Alpha 项目
    - 等等...

---

## 🆕 创建新页面时的额外数据（仅首次）

当发现新的 Binance 合约时，会自动创建页面并包含以下静态信息：

### CMC 基本信息（仅创建时）

- **Symbol** - 币种符号（标题字段）
- **Logo** - 币种图标
- **Website** - 官方网站
- **Genesis Date** - 上线日期

这些信息只在创建页面时设置一次，之后不会更新（除非手动运行同步脚本）。

---

## 🔧 特殊处理

### 1. Multiplier 币种（1000X / 1000000X）

- **1000X 系列**（如 1000PEPE, 1000BONK）
  - MC = (Circulating Supply × Price) / 1000
  - FDV = (Total Supply × Price) / 1000
- **1000000X 系列**（如 1000000BOB, 1000000MOG, 1MBABYDOGE）
  - MC = (Circulating Supply × Price) / 1000000
  - FDV = (Total Supply × Price) / 1000000

### 2. 数据回退机制

如果 CMC API 不可用或返回空数据：

- **Circulating Supply** 会从 Notion 已有数据读取
- **Total Supply** 会从 Notion 已有数据读取
- 确保 MC 和 FDV 仍然能正确计算

### 3. 黑名单过滤

- 黑名单币种（BTTC, RAYSOL, EUR）会被跳过，不会创建或更新

---

## 📊 更新频率建议

### 实时数据（每次都变）

- Spot Price, Perp Price
- Spot/Perp Volume 24h
- Funding Rate
- Open Interest
- Basis
- Price Change

**建议更新频率**：

- **高频交易者**：每 5-15 分钟
- **日常监控**：每 1-4 小时
- **长期持有**：每天 1-2 次

### 半动态数据（偶尔变）

- Circulating Supply（每天可能变化）
- Total Supply（很少变化）
- Max Supply（基本不变）
- Categories（新上线时可能调整）

**建议更新频率**：

- **供应量数据**：每天 1-2 次（使用 `--update-supply` 参数）
- **分类标签**：每次更新都会自动刷新

### 静态数据（基本不变）

- Logo, Website, Genesis Date

**建议更新频率**：不需要定期更新，有需要时手动运行：

```bash
python3 scripts/sync_cmc_to_notion.py
```

---

## ⚙️ 自动化设置

### macOS LaunchAgent（推荐）

已配置的定时任务：

```bash
# 位置
~/Library/LaunchAgents/com.binance.daily_update.plist

# 查看状态
launchctl list | grep binance

# 手动触发
launchctl start com.binance.daily_update

# 查看日志
tail -f /Users/wanjinwoo/Desktop/Work/trading/Binance/update_log.txt
```

### 或者使用 cron

````bash
### 自动化命令示例：

```bash
# 每4小时更新实时数据（推荐，不更新元数据）⭐️
0 */4 * * * cd /Users/wanjinwoo/Desktop/Work/trading/Binance && python3 scripts/update_binance_trading_data.py >> update_log.txt 2>&1

# 每天早上9点更新元数据（供应量 + Funding Cycle）
0 9 * * * cd /Users/wanjinwoo/Desktop/Work/trading/Binance && python3 scripts/update_binance_trading_data.py --update-metadata >> metadata_log.txt 2>&1
````

# 每小时更新一次（高频）

0 \* \* \* \* cd /Users/wanjinwoo/Desktop/Work/trading/Binance && python3 scripts/update_binance_trading_data.py >> update_log.txt 2>&1

# 每天更新一次（低频）

0 9 \* \* \* cd /Users/wanjinwoo/Desktop/Work/trading/Binance && python3 scripts/update_binance_trading_data.py >> update_log.txt 2>&1

````

---

## 🎯 数据质量保证

### 自动功能
1. **自动匹配新币种**
   - 发现 Binance 新上线的合约
   - 自动搜索 CMC 匹配 ID
   - 自动创建 Notion 页面

2. **重复页面检测**
   - 创建前双重检查
   - 防止重复创建

3. **错误重试机制**
   - 失败的币种会自动重试
   - 最多重试 5 轮

4. **黑名单过滤**
   - 自动跳过不想跟踪的币种

### 数据来源
- **价格/交易量/资金费率**：Binance REST API（实时）
- **供应量/市值**：CoinMarketCap Pro API（每次请求）
- **分类标签**：Binance Perpetual API（实时）
- **基本信息**：CoinMarketCap（仅创建时）

---

## 📝 总结

**每次运行更新脚本时：**
1. ✅ 所有实时交易数据（价格、交易量、资金费率等）
2. ✅ 所有供应量数据（流通量、总量、最大量）
3. ✅ 自动计算 MC 和 FDV（支持 multiplier 币种）
4. ✅ Binance 分类标签
5. ✅ 自动发现并创建新币种页面
6. ✅ 过滤黑名单币种
7. ✅ 错误重试机制

**不会更新的：**
- ❌ Logo（除非是新创建的页面）
- ❌ Website（除非是新创建的页面）
- ❌ Genesis Date（除非是新创建的页面）

如需更新这些静态信息，请运行：
```bash
python3 scripts/sync_cmc_to_notion.py [币种符号]
````

---

## 🔍 监控和调试

### 查看最近更新

```bash
tail -f update_log.txt
```

### 测试单个币种

```bash
python3 scripts/update_binance_trading_data.py BTC
```

### 测试多个币种

```bash
python3 scripts/update_binance_trading_data.py BTC ETH SOL
```

### 查看详细统计

脚本会在最后输出：

- 成功更新数量
- 新创建数量
- 跳过数量
- 错误数量
- 失败的币种列表

---

**最后更新时间**: 2025-11-09
