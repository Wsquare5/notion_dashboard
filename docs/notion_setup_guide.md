## Notion 数据库创建指南

### 步骤 1：创建数据库

1. 在 Notion 中创建新页面
2. 添加数据库 (Database - Full page)
3. 命名为 "Binance Trading Dashboard"

### 步骤 2：配置字段

#### 基础字段

| 字段名       | 类型  | 配置       |
| ------------ | ----- | ---------- |
| Ticker       | Title | 主标题字段 |
| Symbol       | Text  | -          |
| Last Updated | Date  | 包含时间   |

#### 价格字段

| 字段名      | 类型   | 配置                   |
| ----------- | ------ | ---------------------- |
| Spot Price  | Number | 格式：美元，6 位小数   |
| Perp Price  | Number | 格式：美元，6 位小数   |
| Index Price | Number | 格式：美元，6 位小数   |
| Mark Price  | Number | 格式：美元，6 位小数   |
| Basis       | Number | 格式：美元，6 位小数   |
| Basis %     | Number | 格式：百分比，3 位小数 |

#### 交易数据字段

| 字段名            | 类型   | 配置                             |
| ----------------- | ------ | -------------------------------- |
| 24h Volume (USDT) | Number | 格式：数字，千分位分隔，0 位小数 |
| 24h Change %      | Number | 格式：百分比，2 位小数           |
| Open Interest     | Number | 格式：数字，千分位分隔，0 位小数 |
| Funding Rate      | Number | 格式：百分比，4 位小数           |
| Next Funding Time | Date   | 包含时间                         |

#### 指数组成字段

| 字段名            | 类型      | 配置                 |
| ----------------- | --------- | -------------------- |
| Index Composition | Rich text | -                    |
| Exchange Count    | Number    | 格式：数字，0 位小数 |
| Main Exchange     | Text      | -                    |

#### 基础信息字段

| 字段名             | 类型   | 配置                             |
| ------------------ | ------ | -------------------------------- |
| Circulating Supply | Number | 格式：数字，千分位分隔，0 位小数 |
| Total Supply       | Number | 格式：数字，千分位分隔，0 位小数 |
| Max Supply         | Number | 格式：数字，千分位分隔，0 位小数 |
| Market Cap         | Number | 格式：美元，千分位分隔，0 位小数 |
| FDV                | Number | 格式：美元，千分位分隔，0 位小数 |

#### 历史数据字段

| 字段名         | 类型   | 配置                             |
| -------------- | ------ | -------------------------------- |
| ATH Price      | Number | 格式：美元，6 位小数             |
| ATH Date       | Date   | 仅日期                           |
| ATL Price      | Number | 格式：美元，6 位小数             |
| ATL Date       | Date   | 仅日期                           |
| ATH Market Cap | Number | 格式：美元，千分位分隔，0 位小数 |

### 步骤 3：创建视图

#### 视图 1：🔥 实时交易

- **布局**: 表格
- **显示字段**: Ticker, Spot Price, Perp Price, Basis %, 24h Volume, 24h Change %, Open Interest, Funding Rate, Last Updated
- **排序**: 24h Volume (USDT) 降序
- **筛选**: Open Interest > 0

#### 视图 2：📊 基础分析

- **布局**: 表格
- **显示字段**: Ticker, Spot Price, Market Cap, FDV, Circulating Supply, ATH Price, ATL Price, Index Composition
- **排序**: Market Cap 降序
- **筛选**: Market Cap > 0

#### 视图 3：🎯 套利机会

- **布局**: 表格
- **显示字段**: Ticker, Spot Price, Perp Price, Basis, Basis %, Funding Rate, Index Composition, Main Exchange
- **排序**: Basis % 绝对值降序
- **筛选**: Basis % < -0.5% 或 > 0.5%

#### 视图 4：💰 市值监控

- **布局**: 表格
- **显示字段**: Ticker, Spot Price, Market Cap, FDV, ATH Price, ATH Market Cap, 24h Change %
- **排序**: Market Cap 降序
- **筛选**: 可自定义市值范围

### 步骤 4：获取数据库 ID

1. 创建完成后，右键数据库标题
2. 选择 "Copy link to view"
3. 从 URL 中提取数据库 ID
4. 更新 `config.json` 中的 `database_id`

### 步骤 5：测试连接

```bash
cd /Users/wanjinwoo/Desktop/Work/trading
python3 Binance/scripts/binance_to_notion.py --symbols BROCCOLI714 --test
```
