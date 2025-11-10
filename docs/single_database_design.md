# Binance Trading Dashboard - 单一数据源设计

## 数据库结构

### 主数据库：Binance Trading Data

包含所有字段，通过不同视图实现分类查看。

#### 字段分组设计

**🏷️ 基础标识字段**

- `Ticker` (Title) - 代币标识符
- `Symbol` (Text) - 完整交易对符号
- `Last Updated` (Date) - 最后更新时间

**💰 实时价格字段**

- `Spot Price` (Number) - 现货价格
- `Perp Price` (Number) - 合约价格
- `Index Price` (Number) - 指数价格
- `Mark Price` (Number) - 标记价格
- `Basis` (Number) - 基差 (Perp - Index)
- `Basis %` (Number) - 基差百分比

**📊 交易数据字段**

- `24h Volume (USDT)` (Number) - 24 小时交易量
- `24h Change %` (Number) - 24 小时价格变化
- `Open Interest` (Number) - 持仓量
- `Funding Rate` (Number) - 资金费率
- `Next Funding Time` (Date) - 下次资金费率时间

**🏦 指数组成字段**

- `Index Composition` (Rich Text) - 指数构成详情
- `Exchange Count` (Number) - 参与交易所数量
- `Main Exchange` (Text) - 主要交易所

**💎 基础信息字段**

- `Circulating Supply` (Number) - 流通量
- `Total Supply` (Number) - 总供应量
- `Max Supply` (Number) - 最大供应量
- `Market Cap` (Number) - 市值 (计算)
- `FDV` (Number) - 完全稀释市值 (计算)

**📈 历史数据字段**

- `ATH Price` (Number) - 历史最高价
- `ATH Date` (Date) - ATH 日期
- `ATL Price` (Number) - 历史最低价
- `ATL Date` (Date) - ATL 日期
- `ATH Market Cap` (Number) - ATH 时市值

## 视图配置方案

### 视图 1：实时交易面板 🔥

**目的**: 专注于实时交易数据
**显示字段**:

- Ticker, Spot Price, Perp Price, Basis %
- 24h Volume, 24h Change %, Open Interest
- Funding Rate, Next Funding Time
- Last Updated

**筛选器**:

- 按交易量排序 (降序)
- 只显示有合约的代币

**布局**: 表格视图，按交易量排序

### 视图 2：基础分析面板 📊

**目的**: 代币基本面和供应信息
**显示字段**:

- Ticker, Spot Price, Market Cap, FDV
- Circulating Supply, Total Supply, Max Supply
- ATH Price, ATH Date, ATL Price, ATL Date
- Index Composition, Exchange Count

**筛选器**:

- 按市值排序 (降序)
- 可按供应量范围筛选

**布局**: 表格视图，按市值排序

### 视图 3：套利机会 🎯

**目的**: 发现套利和异常
**显示字段**:

- Ticker, Spot Price, Perp Price, Basis, Basis %
- Index Price, Mark Price, Funding Rate
- Index Composition, Main Exchange

**筛选器**:

- 按基差绝对值排序
- Basis % > 0.5% 或 < -0.5%
- 资金费率异常筛选

**布局**: 表格视图，按基差排序

### 视图 4：市值监控 💰

**目的**: 市值和估值分析  
**显示字段**:

- Ticker, Spot Price, Market Cap, FDV
- ATH Price, ATH Market Cap
- 24h Change %, 24h Volume
- Market Cap/ATH Market Cap 比率

**筛选器**:

- 按市值排序
- 可设置市值范围筛选
- ATH 回撤比例筛选

**布局**: 画廊视图或表格视图

## 字段属性详细配置

### 数值字段格式

```
Spot Price: 数字格式，6位小数，美元符号
Perp Price: 数字格式，6位小数，美元符号
Basis: 数字格式，6位小数，美元符号
Basis %: 百分比格式，3位小数
24h Volume: 数字格式，0位小数，千分位分隔符
Market Cap: 数字格式，0位小数，千分位分隔符，美元符号
Funding Rate: 百分比格式，4位小数
24h Change %: 百分比格式，2位小数
```

### 公式字段

```
Basis = Perp Price - Index Price
Basis % = (Perp Price - Index Price) / Index Price * 100
Market Cap = Spot Price × Circulating Supply
FDV = Spot Price × Total Supply
ATH Ratio = Spot Price / ATH Price * 100
```

## 实施优势

1. **API 兼容性**: 单一数据源避免多数据源 API 限制
2. **灵活查看**: 多视图满足不同分析需求
3. **性能优化**: 一次写入，多视图读取
4. **易于维护**: 统一的数据结构和更新逻辑
5. **扩展性强**: 可轻松添加新字段和视图

## 下一步行动

1. 在 Notion 中创建新的单一数据源数据库
2. 配置所有字段和属性
3. 创建 4 个预设视图
4. 修改同步脚本适配新结构
5. 测试数据同步和视图显示
