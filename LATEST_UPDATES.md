# 🎯 最新更新说明

## 日期：2025-11-09

---

## ✅ 已完成的修改

### 1. **添加命令行参数支持**

现在可以通过命令行参数控制更新行为：

```bash
# 基本用法（推荐日常使用）- 不更新供应量
python3 scripts/update_binance_trading_data.py

# 更新供应量数据（每天1-2次即可）
python3 scripts/update_binance_trading_data.py --update-supply

# 更新指定币种
python3 scripts/update_binance_trading_data.py BTC ETH SOL

# 更新指定币种并刷新供应量
python3 scripts/update_binance_trading_data.py --update-supply BTC ETH
```

**优势**：

- ⚡️ 日常更新不调用 CMC API，速度更快（节省 API 配额）
- 🎯 可以选择性更新指定币种
- 🔧 灵活控制何时更新供应量数据

---

### 2. **修复 Funding Cycle 检测（支持 1h）**

之前只支持 4h 和 8h，现在增加了 1h 周期的支持。

**修改位置**：`BinanceDataFetcher.detect_funding_cycle()`

```python
# 现在支持 1h, 4h, 8h 三种周期
if 0.5 <= time_diff_hours <= 1.5:
    return 1
elif 3.5 <= time_diff_hours <= 4.5:
    return 4
elif 7.5 <= time_diff_hours <= 8.5:
    return 8
```

---

### 3. **优化 CMC API 调用策略**

**修改前**：

- 每次更新都调用 CMC API 获取供应量数据
- 导致更新速度慢，消耗 API 配额

**修改后**：

- **默认**：不调用 CMC API，使用 Notion 中已有的供应量计算 MC/FDV
- **可选**：添加 `--update-supply` 参数时才调用 CMC API 刷新供应量

**好处**：

- 🚀 日常更新速度提升（跳过 CMC API 调用）
- 💰 节省 CMC API 配额
- 📊 MC/FDV 仍然使用最新价格计算（只是供应量不变）
- 🔄 需要时可以手动刷新供应量

---

## 📊 更新数据对比

### 默认模式（无参数）

```bash
python3 scripts/update_binance_trading_data.py
```

**更新的数据**：

- ✅ 实时价格（Spot/Perp）
- ✅ 24h 交易量
- ✅ 资金费率 & 周期（1h/4h/8h）
- ✅ 未平仓量（OI）
- ✅ 基差（Basis）
- ✅ MC & FDV（使用已有供应量）
- ✅ 分类标签（Categories）
- ❌ **不更新**：Circulating/Total/Max Supply

**速度**：快（~1-2 秒/币种）

---

### Supply 更新模式（--update-supply）

```bash
python3 scripts/update_binance_trading_data.py --update-supply
```

**更新的数据**：

- ✅ 以上所有数据
- ✅ **额外更新**：Circulating Supply
- ✅ **额外更新**：Total Supply
- ✅ **额外更新**：Max Supply
- ✅ MC & FDV（使用最新供应量）

**速度**：稍慢（~2-3 秒/币种，因为调用 CMC API）

---

## 🎯 推荐使用方案

### 方案一：定时自动化（推荐）⭐️

**1. 高频更新价格数据（每 4 小时）**

```bash
0 */4 * * * cd /path/to/Binance && python3 scripts/update_binance_trading_data.py >> update_log.txt 2>&1
```

**2. 低频更新供应量（每天一次）**

```bash
0 9 * * * cd /path/to/Binance && python3 scripts/update_binance_trading_data.py --update-supply >> supply_log.txt 2>&1
```

---

### 方案二：按需手动更新

**日常监控**（实时数据）：

```bash
python3 scripts/update_binance_trading_data.py
```

**每周或有需要时**（刷新供应量）：

```bash
python3 scripts/update_binance_trading_data.py --update-supply
```

---

### 方案三：监控特定币种

**快速查看几个关注的币种**：

```bash
python3 scripts/update_binance_trading_data.py BTC ETH SOL BNB
```

**深度分析（含供应量）**：

```bash
python3 scripts/update_binance_trading_data.py --update-supply BTC ETH SOL
```

---

## 📝 总结

### 主要优势

1. ⚡️ **速度提升**：默认不调用 CMC API，更新速度快
2. 💰 **节省配额**：减少不必要的 CMC API 调用
3. 🎯 **灵活控制**：可以选择性更新供应量数据
4. 🔧 **精准定位**：支持指定币种更新
5. 🐛 **修复 Bug**：正确检测 1h 资金费率周期

### 数据质量保证

- MC 和 FDV 每次都会重新计算（使用最新价格）
- 供应量数据可以选择性刷新（`--update-supply`）
- 分类标签每次都会更新
- 所有实时交易数据每次都会更新

### 使用建议

- **日常使用**：不加参数，快速更新价格和交易数据
- **定期维护**：每天或每周使用 `--update-supply` 刷新供应量
- **特殊情况**：币种有增发、销毁等事件时立即使用 `--update-supply`

---

**最后更新**: 2025-11-09
