# Binance Trading Dashboard - Notion Database Template

## 📊 双表关联数据库设计

### 🔄 **数据库架构说明**

我们将创建两个关联的数据库：

- **📈 实时交易数据表** - 频繁更新，专注交易指标
- **📋 代币基础资料表** - 静态数据，专注基本信息

---

## 📈 **表 1: 实时交易数据 (Real-time Trading Data)**

### **基础字段**

| 字段名           | 类型        | 格式 | 说明                 |
| ---------------- | ----------- | ---- | -------------------- |
| **Symbol**       | Title       | -    | 代币符号（主键）     |
| **Token Info**   | Relation    | -    | 关联到代币基础资料表 |
| **Last Updated** | Date & Time | -    | 最后更新时间         |
| **Data Status**  | Select      | -    | 完整/部分/错误       |

### **实时价格数据**

| 字段名          | 类型   | 格式      | 说明     |
| --------------- | ------ | --------- | -------- |
| **Spot Price**  | Number | $0.000000 | 现货价格 |
| **Perp Price**  | Number | $0.000000 | 合约价格 |
| **Index Price** | Number | $0.000000 | 指数价格 |
| **Mark Price**  | Number | $0.000000 | 标记价格 |

### **交易数据**

| 字段名              | 类型   | 格式 | 说明               |
| ------------------- | ------ | ---- | ------------------ |
| **Spot Volume 24h** | Number | $0   | 现货 24 小时交易量 |
| **Perp Volume 24h** | Number | $0   | 合约 24 小时交易量 |
| **Open Interest**   | Number | $0   | 持仓量             |

### **核心指标**

| 字段名           | 类型   | 格式    | 说明                     |
| ---------------- | ------ | ------- | ------------------------ |
| **Funding Rate** | Number | 0.0000% | 资金费率                 |
| **Basis**        | Number | 0.00%   | 基差：(Perp-Index)/Index |
| **Market Cap**   | Number | $0      | 市值（实时计算）         |
| **FDV**          | Number | $0      | 完全稀释估值（实时计算） |

### **指数组成透明度**

| 字段名                | 类型      | 说明                     |
| --------------------- | --------- | ------------------------ |
| **Index Summary**     | Text      | 指数组成简要摘要         |
| **Index Composition** | Rich Text | 详细的交易所构成信息     |
| **Top Exchange**      | Text      | 权重最大的交易所         |
| **Exchange Count**    | Number    | 参与指数计算的交易所数量 |

---

## 📋 **表 2: 代币基础资料 (Token Basic Info)**

### **基础信息**

| 字段名           | 类型     | 说明                 |
| ---------------- | -------- | -------------------- |
| **Symbol**       | Title    | 代币符号（主键）     |
| **CoinGecko ID** | Text     | CoinGecko 映射 ID    |
| **Trading Data** | Relation | 关联到实时交易数据表 |
| **Info Updated** | Date     | 基础信息最后更新日期 |

### **供应量数据（静态）**

| 字段名                 | 类型   | 格式 | 说明       |
| ---------------------- | ------ | ---- | ---------- |
| **Circulating Supply** | Number | 0    | 流通量     |
| **Total Supply**       | Number | 0    | 总供应量   |
| **Max Supply**         | Number | 0    | 最大供应量 |

### **历史高低点（静态）**

| 字段名             | 类型   | 格式      | 说明           |
| ------------------ | ------ | --------- | -------------- |
| **ATH Price**      | Number | $0.000000 | 历史最高价     |
| **ATH Date**       | Date   | -         | 历史最高价日期 |
| **ATH Market Cap** | Number | $0        | 历史最高市值   |
| **ATL Price**      | Number | $0.000000 | 历史最低价     |
| **ATL Date**       | Date   | -         | 历史最低价日期 |
| **ATL Market Cap** | Number | $0        | 历史最低市值   |

### **计算字段（Rollup from Trading Data）**

| 字段名                 | 类型    | 说明                                           |
| ---------------------- | ------- | ---------------------------------------------- |
| **Current Price**      | Rollup  | 从交易表获取当前现货价格                       |
| **Current Market Cap** | Rollup  | 从交易表获取当前市值                           |
| **Distance from ATH**  | Formula | (ATH Price - Current Price) / ATH Price × 100% |
| **Distance from ATL**  | Formula | (Current Price - ATL Price) / ATL Price × 100% |

---

## 🎯 视图设计方案

### **📈 实时交易数据表 - 视图设计**

#### **1. 🚨 交易监控台**

- **显示字段：** Symbol, Spot Price, Perp Price, Basis, Funding Rate, Last Updated
- **排序：** 按 Basis 绝对值降序
- **筛选：** Data Status = "完整"
- **用途：** 快速发现套利机会

#### **2. 💹 流动性仪表板**

- **显示字段：** Symbol, Perp Volume 24h, Open Interest, Market Cap, Exchange Count
- **排序：** 按 Open Interest 降序
- **筛选：** Open Interest > $1M
- **用途：** 分析市场流动性

#### **3. 🌐 指数透明度分析**

- **显示字段：** Symbol, Index Price, Index Summary, Top Exchange, Exchange Count
- **排序：** 按 Exchange Count 降序
- **筛选：** 有指数组成数据
- **用途：** 了解价格构成机制

### **� 代币基础资料表 - 视图设计**

#### **1. 🏆 历史表现总览**

- **显示字段：** Symbol, Current Price, ATH Price, ATL Price, Distance from ATH, Distance from ATL
- **排序：** 按 Distance from ATH 升序
- **用途：** 分析历史价格表现

#### **2. 📊 供应量分析**

- **显示字段：** Symbol, Circulating Supply, Total Supply, Max Supply, Current Market Cap
- **排序：** 按 Market Cap 降序
- **用途：** 代币经济学分析

---

## 🔗 **数据库创建步骤**

### **步骤 1: 创建代币基础资料表**

1. 新建数据库，命名：`Token Basic Info`
2. 添加所有基础信息、供应量、ATH/ATL 字段
3. 先创建这个表，因为交易表需要关联到这里

### **步骤 2: 创建实时交易数据表**

1. 新建数据库，命名：`Real-time Trading Data`
2. 添加实时价格、交易数据、核心指标、指数组成字段
3. 创建 Relation 字段`Token Info`，关联到`Token Basic Info`表

### **步骤 3: 设置关联关系**

1. 在交易数据表中：`Token Info` → 关联到基础资料表
2. 在基础资料表中：`Trading Data` → 关联到交易数据表
3. 设置 Rollup 字段获取当前价格和市值

---

## 🚀 Notion API 配置

### **表 1: 实时交易数据表**

```json
{
  "Symbol": { "type": "title" },
  "Token_Info": {
    "type": "relation",
    "relation": { "database_id": "基础资料表ID" }
  },
  "Last_Updated": { "type": "date" },
  "Data_Status": {
    "type": "select",
    "options": [
      { "name": "完整", "color": "green" },
      { "name": "部分", "color": "yellow" },
      { "name": "错误", "color": "red" }
    ]
  },
  "Spot_Price": { "type": "number", "format": "dollar" },
  "Perp_Price": { "type": "number", "format": "dollar" },
  "Index_Price": { "type": "number", "format": "dollar" },
  "Mark_Price": { "type": "number", "format": "dollar" },
  "Spot_Volume_24h": { "type": "number", "format": "dollar" },
  "Perp_Volume_24h": { "type": "number", "format": "dollar" },
  "Open_Interest": { "type": "number", "format": "dollar" },
  "Funding_Rate": { "type": "number", "format": "percent" },
  "Basis": { "type": "number", "format": "percent" },
  "Market_Cap": { "type": "number", "format": "dollar" },
  "FDV": { "type": "number", "format": "dollar" },
  "Index_Summary": { "type": "rich_text" },
  "Index_Composition": { "type": "rich_text" },
  "Top_Exchange": { "type": "rich_text" },
  "Exchange_Count": { "type": "number" }
}
```

### **表 2: 代币基础资料表**

```json
{
  "Symbol": { "type": "title" },
  "CoinGecko_ID": { "type": "rich_text" },
  "Trading_Data": {
    "type": "relation",
    "relation": { "database_id": "交易数据表ID" }
  },
  "Info_Updated": { "type": "date" },
  "Circulating_Supply": { "type": "number" },
  "Total_Supply": { "type": "number" },
  "Max_Supply": { "type": "number" },
  "ATH_Price": { "type": "number", "format": "dollar" },
  "ATH_Date": { "type": "date" },
  "ATH_Market_Cap": { "type": "number", "format": "dollar" },
  "ATL_Price": { "type": "number", "format": "dollar" },
  "ATL_Date": { "type": "date" },
  "ATL_Market_Cap": { "type": "number", "format": "dollar" },
  "Current_Price": {
    "type": "rollup",
    "rollup": {
      "relation_property_name": "Trading_Data",
      "rollup_property_name": "Spot_Price",
      "function": "show_original"
    }
  },
  "Current_Market_Cap": {
    "type": "rollup",
    "rollup": {
      "relation_property_name": "Trading_Data",
      "rollup_property_name": "Market_Cap",
      "function": "show_original"
    }
  }
}
```

---

## 📝 **详细操作指南**

### **🛠️ Notion 数据库创建流程**

#### **第一步：创建代币基础资料表**

1. 在 Notion 中创建新页面 → 输入`/database` → 选择"Table - Full page"
2. 数据库标题：`Token Basic Info`
3. 按顺序添加字段：
   ```
   Symbol (Title) - 代币符号
   CoinGecko ID (Text) - CoinGecko映射ID
   Info Updated (Date) - 信息更新日期
   Circulating Supply (Number) - 流通量
   Total Supply (Number) - 总供应量
   Max Supply (Number) - 最大供应量
   ATH Price (Number, $) - 历史最高价
   ATH Date (Date) - 最高价日期
   ATH Market Cap (Number, $) - 历史最高市值
   ATL Price (Number, $) - 历史最低价
   ATL Date (Date) - 最低价日期
   ATL Market Cap (Number, $) - 历史最低市值
   ```

#### **第二步：创建实时交易数据表**

1. 创建另一个数据库：`Real-time Trading Data`
2. 添加字段：
   ```
   Symbol (Title) - 代币符号
   Last Updated (Date & Time) - 最后更新时间
   Data Status (Select) - 完整/部分/错误 (绿/黄/红色)
   Spot Price (Number, $) - 现货价格
   Perp Price (Number, $) - 合约价格
   Index Price (Number, $) - 指数价格
   Mark Price (Number, $) - 标记价格
   Spot Volume 24h (Number, $) - 现货交易量
   Perp Volume 24h (Number, $) - 合约交易量
   Open Interest (Number, $) - 持仓量
   Funding Rate (Number, %) - 资金费率
   Basis (Number, %) - 基差
   Market Cap (Number, $) - 市值
   FDV (Number, $) - 完全稀释估值
   Index Summary (Text) - 指数组成摘要
   Index Composition (Rich Text) - 详细指数构成
   Top Exchange (Text) - 主要交易所
   Exchange Count (Number) - 交易所数量
   ```

#### **第三步：设置表关联**

1. 在交易数据表中添加：`Token Info (Relation)` → 选择关联到`Token Basic Info`表
2. 在基础资料表中添加：`Trading Data (Relation)` → 选择关联到`Real-time Trading Data`表
3. 在基础资料表中添加 Rollup 字段：
   - `Current Price (Rollup)` → 从 Trading Data 的 Spot Price 获取
   - `Current Market Cap (Rollup)` → 从 Trading Data 的 Market Cap 获取

---

## 🔑 **Notion API 设置指南**

### **获取 Notion API 密钥的步骤：**

1. **创建 Integration：**

   - 访问：https://www.notion.so/my-integrations
   - 点击 "New integration"
   - 填写信息：
     - Name: `Binance Trading Bot`
     - Logo: 可选
     - Associated workspace: 选择你的工作区
   - 点击 "Submit"

2. **复制 API 密钥：**

   - 创建后会显示 "Internal Integration Token"
   - 格式：`secret_xxxxxxxxxx`
   - **重要：保存好这个密钥，只显示一次！**

3. **分享数据库给 Integration：**

   - 打开你创建的两个数据库
   - 点击右上角 "Share"
   - 点击 "Invite"
   - 搜索你的 Integration 名称(`Binance Trading Bot`)
   - 给予 "Can edit" 权限

4. **获取数据库 ID：**
   - 在数据库页面，复制 URL 中的 ID 部分
   - 格式：`https://notion.so/xxxxx?v=yyyy`
   - 数据库 ID 就是 `xxxxx` 部分（32 个字符）

---

## 🎨 **优势对比：双表 vs 单表**

### **✅ 双表架构优势：**

- **界面清爽：** 每个表专注特定用途，避免字段过多
- **更新效率：** 实时数据和静态数据分离，减少不必要的 API 调用
- **灵活查看：** 可以单独查看交易数据或基础信息
- **性能更好：** 频繁更新的字段集中在一个表，加载速度更快
- **扩展性强：** 后续可以轻松添加新的关联表（如解锁时间表）

### **🔗 关联功能：**

- 在交易数据表中可以快速跳转到对应的基础信息
- 在基础信息表中可以看到实时的价格和市值
- Rollup 字段自动聚合关联表的数据
- 支持跨表筛选和排序

---

## 📊 **示例数据预览**

### **📈 实时交易数据表**

| Symbol      | Spot Price | Perp Price | Basis  | Funding Rate | Market Cap | Index Summary                           |
| ----------- | ---------- | ---------- | ------ | ------------ | ---------- | --------------------------------------- |
| BROCCOLI714 | $0.023200  | $0.023150  | -0.19% | 0.005%       | $22.5M     | binance (67%), mxc (10%), +4 more       |
| BROCCOLIF3B | -          | $0.018092  | 0.80%  | 0.16%        | $18.1M     | mxc (43%), pancakeswapV3 (43%), +1 more |

### **📋 代币基础资料表**

| Symbol      | Current Price | ATH Price | Distance from ATH | Circulating Supply | Total Supply  |
| ----------- | ------------- | --------- | ----------------- | ------------------ | ------------- |
| BROCCOLI714 | $0.023200     | $0.257985 | 91.0%             | 971,060,585        | 971,060,585   |
| BROCCOLIF3B | $0.018092     | $0.110665 | 83.6%             | 1,000,000,000      | 1,000,000,000 |
