# 🎯 Funding Cycle 更新逻辑修改

## 日期：2025-11-09

---

## ✅ 修改内容

### 问题描述

用户指出 Funding Cycle 不是经常改变的数据，不应该每次都更新。

### 解决方案

将 Funding Cycle 与 Supply 数据一起归类为"元数据"（metadata），只在指定参数时才更新。

---

## 🔧 具体修改

### 1. **Funding Cycle 检测支持 1h 周期**

- 之前只支持 4h 和 8h
- 现在支持 1h、4h、8h 三种周期
- 测试通过：HIPPO、AIA、0G 等 1h 周期币种正确识别 ✅

### 2. **更新逻辑修改**

#### 默认模式（无参数）

```bash
python3 scripts/update_binance_trading_data.py
```

**更新的数据**：

- ✅ 实时价格（Spot/Perp）
- ✅ 24h 交易量
- ✅ 资金费率（Funding）
- ✅ 未平仓量（OI）
- ✅ 基差（Basis）
- ✅ MC & FDV（使用已有供应量）
- ✅ 分类标签（Categories）
- ❌ **不更新**：Circulating/Total/Max Supply
- ❌ **不更新**：Funding Cycle

#### 元数据更新模式（--update-metadata）

```bash
python3 scripts/update_binance_trading_data.py --update-metadata
```

**额外更新的数据**：

- ✅ Circulating Supply（从 CMC API）
- ✅ Total Supply（从 CMC API）
- ✅ Max Supply（从 CMC API）
- ✅ **Funding Cycle（1h/4h/8h）** ⭐️ 新增

### 3. **参数重命名**

#### 新参数名

- `--update-metadata` - 更新元数据（供应量 + Funding Cycle）

#### 向后兼容

- `--update-supply` - 仍可使用，等同于 `--update-metadata`

---

## 📖 使用方法

### 日常更新（推荐）⭐️

```bash
# 只更新实时数据（价格、交易量、资金费率等）
python3 scripts/update_binance_trading_data.py
```

- **速度**：快（~1-2 秒/币种）
- **不调用 CMC API**：节省配额
- **Funding Cycle**：不更新（使用已有值）

### 定期元数据更新

```bash
# 更新元数据（供应量 + Funding Cycle）
python3 scripts/update_binance_trading_data.py --update-metadata
```

- **速度**：稍慢（~2-3 秒/币种，调用 CMC API）
- **建议频率**：每天 1-2 次
- **Funding Cycle**：检测并更新最新周期

### 指定币种更新

```bash
# 快速查看几个币种
python3 scripts/update_binance_trading_data.py BTC ETH SOL

# 深度分析（含元数据）
python3 scripts/update_binance_trading_data.py --update-metadata BTC ETH
```

---

## 🚀 自动化建议

### 推荐 cron 配置

```bash
# 每4小时更新实时数据（不更新元数据）⭐️
0 */4 * * * cd /path/to/Binance && python3 scripts/update_binance_trading_data.py >> update_log.txt 2>&1

# 每天早上9点更新元数据（供应量 + Funding Cycle）
0 9 * * * cd /path/to/Binance && python3 scripts/update_binance_trading_data.py --update-metadata >> metadata_log.txt 2>&1
```

### 好处

- ⚡️ 高频更新（每 4 小时）只更新必要的实时数据
- 💰 节省 CMC API 配额（不每次都调用）
- 🎯 低频更新（每天 1 次）刷新不常变的元数据
- 🔄 Funding Cycle 每天检查一次是否变化

---

## 🧪 测试验证

### 测试 1：默认模式（不更新 Funding Cycle）

```bash
python3 scripts/update_binance_trading_data.py HIPPO
```

**结果**：✅

- 输出显示：`(prices/volumes/funding only)`
- 不调用 CMC API
- Funding Cycle 保持原值不变

### 测试 2：元数据模式（更新 Funding Cycle）

```bash
python3 scripts/update_binance_trading_data.py --update-metadata HIPPO AIA
```

**结果**：✅

- 输出显示：`(with metadata: Supply + Funding Cycle)`
- 显示 `[+CMC]` 标记
- Funding Cycle 检测并更新为 1h

### 测试 3：1h 周期检测

测试币种：HIPPO、AIA、0G

**结果**：✅ 全部正确识别为 1h 周期

- HIPPO: 1h ✅
- AIA: 1h ✅
- 0G: 1h ✅

### 测试 4：向后兼容

```bash
python3 scripts/update_binance_trading_data.py --update-supply BTC
```

**结果**：✅ `--update-supply` 参数仍可用

---

## 📊 数据更新频率建议

### 高频数据（每次都变）

- Spot/Perp Price
- Trading Volume
- Funding Rate
- Open Interest
- Basis

**建议频率**：每 1-4 小时

---

### 低频元数据（很少变）

- Circulating Supply（每天可能变化）
- Total Supply（很少变化）
- Max Supply（基本不变）
- **Funding Cycle（很少变化，新上线时可能调整）** ⭐️

**建议频率**：每天 1-2 次

---

### 静态数据（基本不变）

- Logo
- Website
- Genesis Date
- Categories（新上线时可能调整，但每次都会更新）

**建议频率**：

- Categories：每次更新都会刷新
- Logo/Website/Genesis：不需要定期更新，有需要时手动运行 `sync_cmc_to_notion.py`

---

## 🎯 总结

### 主要改进

1. ⚡️ **性能提升**：默认不更新 Funding Cycle，减少不必要的 API 调用
2. 🎯 **精准控制**：`--update-metadata` 参数统一控制元数据更新
3. 🔧 **功能增强**：Funding Cycle 现在支持 1h 周期
4. 🔄 **向后兼容**：`--update-supply` 仍可使用

### 使用建议

- **日常监控**：每 4 小时运行默认模式
- **元数据维护**：每天运行 1 次元数据模式
- **特殊情况**：币种增发、销毁、周期变更时手动运行元数据模式

---

**最后更新**: 2025-11-09
