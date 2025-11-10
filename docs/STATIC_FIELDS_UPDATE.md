# 静态字段更新说明

## 什么是静态字段？

静态字段是指不经常变化的数据，包括：

1. **Funding Cycle（资金费率周期）** - 1h、4h 或 8h
2. **Categories（分类标签）** - AI、DeFi、Meme、Layer-1 等（最多 23 种）
3. **Index Composition（指数成分）** - 永续合约价格的构成来源

这些字段不像价格、交易量那样实时变化，通常只在以下情况需要更新：

- 有新币种上市
- Binance 调整了某个币的资金费率周期
- Binance 更新了分类标签
- 永续合约的价格指数成分发生变化

## 更新选项对比

### 选项 1：快速更新（默认）

```bash
python3 scripts/update_binance_trading_data.py
```

**更新内容：**

- ✅ Spot Price（现货价格）
- ✅ Perp Price（永续价格）
- ✅ Spot vol 24h（现货 24h 交易量）
- ✅ Perp vol 24h（永续 24h 交易量）
- ✅ Funding（资金费率）
- ✅ OI（持仓量）
- ✅ Basis（基差）
- ✅ MC（市值）
- ✅ FDV（完全稀释估值）
- ❌ Funding Cycle
- ❌ Categories
- ❌ Index Composition
- ❌ Supply（供应量数据）

**特点：**

- 速度最快（~10 分钟）
- 不调用 CMC API
- 适合高频率更新（每 1-4 小时）

---

### 选项 2：更新静态字段

```bash
python3 scripts/update_binance_trading_data.py --update-static-fields
```

**更新内容：**

- ✅ 所有选项 1 的实时数据
- ✅ **Funding Cycle（资金费率周期）**
- ✅ **Categories（分类标签）**
- ✅ **Index Composition（指数成分）**
- ❌ Supply（供应量数据）

**特点：**

- 速度较快（~15 分钟）
- 不调用 CMC API
- 适合不定期运行（有新币上市或分类变化时）

---

### 选项 3：完整更新

```bash
python3 scripts/update_binance_trading_data.py --update-metadata
```

**更新内容：**

- ✅ 所有选项 1 的实时数据
- ✅ **Funding Cycle（资金费率周期）**
- ✅ **Categories（分类标签）**
- ✅ **Index Composition（指数成分）**
- ✅ **Circulating Supply（流通供应量）**
- ✅ **Total Supply（总供应量）**
- ✅ **Max Supply（最大供应量）**

**特点：**

- 速度最慢（~25 分钟）
- 调用 CMC API（可能有限额）
- 适合每天运行 1 次

---

## 使用交互式菜单

运行菜单：

```bash
python3 update_menu.py
```

菜单选项：

- **[1]** 快速更新 - 只更新实时数据
- **[2]** 更新静态字段 - 实时数据 + Funding Cycle + Categories + Index Composition
- **[3]** 完整更新 - 实时数据 + 供应量 + 静态字段
- **[4-6]** 指定币种的对应更新

## 推荐使用策略

### 日常自动化

```bash
# 方案一：只关注实时数据
# crontab: 每 4 小时快速更新
0 */4 * * * cd /path/to/Binance && python3 scripts/update_binance_trading_data.py

# 方案二：定期更新静态字段
# crontab: 每 4 小时快速更新 + 每周一更新静态字段
0 */4 * * * cd /path/to/Binance && python3 scripts/update_binance_trading_data.py
0 9 * * 1 cd /path/to/Binance && python3 scripts/update_binance_trading_data.py --update-static-fields

# 方案三：完整更新
# crontab: 每天早上完整更新
0 9 * * * cd /path/to/Binance && python3 scripts/update_binance_trading_data.py --update-metadata
```

### 手动按需更新

**什么时候用选项 1（快速更新）？**

- 想快速查看最新价格和交易量
- 每天多次查看行情
- 不关心分类标签和资金费率周期

**什么时候用选项 2（更新静态字段）？**

- 发现有新币上市了
- 想检查某个币的资金费率周期
- 想查看最新的分类标签
- 不需要更新供应量数据（节省 CMC API 调用）

**什么时候用选项 3（完整更新）？**

- 需要最新的供应量数据计算市值
- 每天定期全面更新
- 不在意 CMC API 限额

## 向后兼容性

旧的 `--update-funding-cycle` 参数仍然可用，但已标记为废弃：

```bash
# 这个仍然有效，但推荐使用 --update-static-fields
python3 scripts/update_binance_trading_data.py --update-funding-cycle
```

## 常见问题

**Q: 为什么要分开静态字段和供应量？**
A: 因为静态字段可以从 Binance API 获取（不消耗 CMC API 额度），而供应量需要调用 CMC API。分开后可以更灵活地控制 API 使用。

**Q: 多久更新一次静态字段合适？**
A: 建议每周或每月更新一次，除非：

- 有新币上市（立即更新）
- Binance 公告调整了资金费率周期（立即更新）
- 发现分类标签不准确（手动更新）

**Q: Index Composition 有什么用？**
A: 显示永续合约价格的数据来源，例如 "Binance: 100.00%" 表示 100% 来自 Binance 现货价格。

**Q: Categories 的数据从哪里来？**
A: 直接从 Binance Perpetual API 获取，是官方分类标签（最多 23 种）。

## 字段更新频率建议

| 字段                              | 更新频率    | 原因             |
| --------------------------------- | ----------- | ---------------- |
| Price, Volume, Funding, OI, Basis | 每 1-4 小时 | 实时变化         |
| MC, FDV                           | 每 1-4 小时 | 基于实时价格计算 |
| Funding Cycle                     | 每周/每月   | 很少变化         |
| Categories                        | 每周/每月   | 偶尔调整         |
| Index Composition                 | 每周/每月   | 基本不变         |
| Circulating Supply                | 每天 1 次   | 缓慢增长         |
| Total/Max Supply                  | 每周 1 次   | 固定或缓慢变化   |
