# 🚀 Binance Trading Data → Notion Sync

自动同步 Binance 现货和永续合约交易数据到 Notion，包括价格、交易量、资金费率、市值等信息。

## 📋 目录

- [快速开始](#快速开始)
- [交互式更新菜单](#交互式更新菜单)
- [命令行使用](#命令行使用)
- [自动化定时更新](#自动化定时更新)
- [数据说明](#数据说明)

Files added:

- `scripts/binance_to_notion.py` - main sync script (Python)
- `requirements.txt` - Python dependencies
- `.env.example` - example environment variables file
- `overrides.json` - manual mapping for tricky symbols -> CoinGecko IDs

Requirements

- Python 3.9+
- A Notion integration and a target Notion database (see steps below)

Setup

1. Create and activate a virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in `NOTION_TOKEN` and `NOTION_DATABASE_ID`.

Creating a Notion integration and database

1. In Notion, go to Settings & Members → Integrations → Develop your own integrations → New integration.
2. Give it a name and copy the "Internal Integration Token" into `NOTION_TOKEN` in your `.env`.
3. Create a new database (Table) in Notion with these properties (case-sensitive):

   - `Name` (Title)
   - `Symbol` (Rich Text)
   - `Price (USD)` (Number)
   - `Market Cap (USD)` (Number)
   - `Open Interest` (Number)
   - `24h Volume (USD)` (Number)
   - `CoinGecko ID` (Rich Text)
   - `Website` (URL)

4. Share the database with your integration (top-right Share → Invite → select your integration).
5. Copy the database ID from the URL and paste into `NOTION_DATABASE_ID` in `.env`.

---

## 🎯 快速开始

### 1. 交互式更新菜单（推荐）⭐️

最简单的使用方式，无需记忆命令：

```bash
python3 update_menu.py
```

**菜单选项**：

```
🚀 Binance Trading Data Update Menu
================================================================================

请选择更新模式：

  [1] 快速更新 - 只更新实时数据（价格、交易量、资金费率等）
      • 速度最快，不调用 CMC API
      • 推荐日常使用（每1-4小时）

  [2] 更新 Funding Cycle - 实时数据 + 资金费率周期
      • 不调用 CMC API，速度快
      • 推荐每天运行1次

  [3] 完整更新 - 实时数据 + 供应量 + Funding Cycle
      • 调用 CMC API，速度较慢
      • 推荐每天运行1次或有需要时使用

  [4] 指定币种更新 - 快速更新特定币种
  [5] 指定币种 + Funding Cycle
  [6] 指定币种 + 完整元数据
  [7] 同步分类标签 - 从 Binance API 同步分类

  [0] 退出
```

**使用示例**：

1. 运行 `python3 update_menu.py`
2. 输入数字选择操作（例如：输入 `1` 进行快速更新）
3. 等待执行完成
4. 按 Enter 返回菜单继续其他操作

---

## 💻 命令行使用

如果您熟悉命令行或需要在脚本中使用，可以直接运行：

### 基本用法

```bash
# 1. 快速更新（推荐日常使用）
python3 scripts/update_binance_trading_data.py

# 2. 更新 Funding Cycle
python3 scripts/update_binance_trading_data.py --update-funding-cycle

# 3. 完整更新（包括供应量）
python3 scripts/update_binance_trading_data.py --update-metadata

# 4. 更新指定币种
python3 scripts/update_binance_trading_data.py BTC ETH SOL

# 5. 更新指定币种 + Funding Cycle
python3 scripts/update_binance_trading_data.py --update-funding-cycle BTC ETH

# 6. 同步分类标签
python3 scripts/sync_binance_categories.py
```

### 参数说明

| 参数                     | 说明                                  | CMC API   | 速度   |
| ------------------------ | ------------------------------------- | --------- | ------ |
| 无参数                   | 只更新实时数据                        | ❌ 不调用 | 快 ⚡️ |
| `--update-funding-cycle` | 更新实时数据 + Funding Cycle          | ❌ 不调用 | 快 ⚡️ |
| `--update-metadata`      | 更新实时数据 + 供应量 + Funding Cycle | ✅ 调用   | 慢 🐢  |

---

## ⏰ 自动化定时更新

### 使用 cron（推荐）

编辑 crontab：

```bash
crontab -e
```

添加以下任务：

```bash
# 每4小时快速更新（只更新价格、交易量等实时数据）⭐️
0 */4 * * * cd /Users/wanjinwoo/Desktop/Work/trading/Binance && python3 scripts/update_binance_trading_data.py >> logs/update.log 2>&1

# 每天早上9点更新 Funding Cycle
0 9 * * * cd /Users/wanjinwoo/Desktop/Work/trading/Binance && python3 scripts/update_binance_trading_data.py --update-funding-cycle >> logs/funding_cycle.log 2>&1

# 每天早上10点完整更新（包括供应量）
0 10 * * * cd /Users/wanjinwoo/Desktop/Work/trading/Binance && python3 scripts/update_binance_trading_data.py --update-metadata >> logs/metadata.log 2>&1
```

### 使用 macOS LaunchAgent

已配置文件：`com.binance.daily_update.plist`

```bash
# 加载任务
launchctl load ~/Library/LaunchAgents/com.binance.daily_update.plist

# 查看状态
launchctl list | grep binance

# 手动触发
launchctl start com.binance.daily_update

# 查看日志
tail -f logs/update.log
```

---

## 📊 数据说明

### 实时数据（每次都更新）

**交易数据**：

- Spot Price（现货价格）
- Perp Price（合约价格）
- Spot vol 24h（现货 24h 交易量）
- Perp vol 24h（合约 24h 交易量）
- Funding（资金费率）
- OI（未平仓量）
- Basis（基差）
- Price change（24h 涨跌幅）

**市值计算**：

- MC（市值）= Circulating Supply × Price
- FDV（完全稀释市值）= Total Supply × Price
- 自动支持 1000X 和 1000000X multiplier 币种

### 元数据（需要参数才更新）

**供应量数据**（`--update-metadata`）：

- Circulating Supply（流通供应量）
- Total Supply（总供应量）
- Max Supply（最大供应量）

**周期数据**（`--update-funding-cycle` 或 `--update-metadata`）：

- Funding Cycle（资金费率周期：1h/4h/8h）

**分类数据**（每次都更新）：

- Categories（币种分类：AI、DeFi、Meme、Layer-1 等 23 个分类）

---

## 📁 项目结构

```
Binance/
├── update_menu.py                           # 🎯 交互式更新菜单（推荐使用）
├── config.json                              # Notion 配置
├── api_config.json                          # CMC API 配置
├── binance_cmc_mapping.json                 # CMC ID 映射（600+ 币种）
├── blacklist.json                           # 黑名单
├── scripts/
│   ├── update_binance_trading_data.py      # 主更新脚本
│   ├── sync_binance_categories.py          # 同步分类标签
│   ├── sync_cmc_to_notion.py               # 同步 CMC 基本信息
│   ├── auto_match_new_symbols.py           # 自动匹配新币种
│   └── ...
├── logs/                                    # 日志文件
└── data/                                    # 数据缓存

```

---

## 🔧 高级功能

### 自动匹配新币种

当 Binance 上线新合约时，脚本会自动：

1. 检测新币种
2. 搜索 CMC 匹配
3. 创建 Notion 页面
4. 同步基本信息

### 黑名单管理

编辑 `blacklist.json` 添加不想跟踪的币种：

```json
{
  "symbols": ["BTTC", "EUR", "RAYSOL"],
  "reason": "User requested exclusion"
}
```

### Multiplier 币种支持

自动识别并正确计算：

- 1000X 系列（1000PEPE, 1000BONK 等）
- 1000000X 系列（1000000BOB, 1MBABYDOGE 等）

---

## 📖 文档

- [DATA_UPDATE_SUMMARY.md](DATA_UPDATE_SUMMARY.md) - 详细的数据更新说明
- [FUNDING_CYCLE_UPDATE.md](FUNDING_CYCLE_UPDATE.md) - Funding Cycle 更新说明
- [LATEST_UPDATES.md](LATEST_UPDATES.md) - 最新更新日志

---

## ❓ 常见问题

**Q: 每次更新需要多长时间？**

- 快速更新（无参数）：约 10-15 分钟（600 币种）
- Funding Cycle 更新：约 15-20 分钟
- 完整更新（含供应量）：约 20-30 分钟

**Q: 为什么要分开更新？**

- 实时数据（价格、交易量）变化频繁，需要高频更新
- 元数据（供应量、Funding Cycle）变化少，低频更新节省 API 配额

**Q: 推荐的更新频率是？**

- 日常监控：每 4 小时快速更新
- Funding Cycle：每天 1 次
- 供应量数据：每天 1 次或有需要时

**Q: 如何查看更新日志？**

```bash
tail -f logs/update.log
```

---

## 🎉 开始使用

最简单的方式：

```bash
python3 update_menu.py
```

选择 `1` 进行快速更新，几分钟后就能在 Notion 中看到最新数据！
