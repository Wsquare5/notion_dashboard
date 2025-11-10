# 🚀 快速使用指南

## 最简单的方式

直接运行交互式菜单：

```bash
python3 update_menu.py
```

或者：

```bash
./update.sh
```

## 菜单选项说明

### [1] 快速更新 ⭐️ 推荐日常使用

- **更新内容**：价格、交易量、资金费率、OI、基差、MC、FDV
- **不更新**：供应量、Funding Cycle
- **速度**：快（~10 分钟）
- **API**：不调用 CMC API
- **推荐频率**：每 1-4 小时

### [2] 更新静态字段 💡 不定期使用

- **更新内容**：快速更新的所有数据 + Funding Cycle（1h/4h/8h）+ Categories + Index Composition
- **不更新**：供应量
- **速度**：较快（~15 分钟）
- **API**：不调用 CMC API
- **推荐频率**：有新币上市时或每周/每月 1 次

### [3] 完整更新

- **更新内容**：所有数据（包括供应量 + 静态字段）
- **速度**：慢（~25 分钟）
- **API**：调用 CMC API
- **推荐频率**：每天 1 次或有需要时

### [4-6] 指定币种更新

- 只更新您输入的币种
- 三种模式：快速、静态字段、完整更新

## 推荐使用方案

### 方案一：全自动（推荐）⭐️

设置 cron 定时任务，自动更新：

```bash
# 编辑 crontab
crontab -e

# 添加以下行
# 每4小时快速更新（只更新实时数据）
0 */4 * * * cd /path/to/Binance && python3 scripts/update_binance_trading_data.py >> logs/update.log 2>&1

# 每周一早上更新静态字段（Funding Cycle + Categories + Index Composition）
0 9 * * 1 cd /path/to/Binance && python3 scripts/update_binance_trading_data.py --update-static-fields >> logs/static.log 2>&1

# 每天早上10点完整更新（包括供应量）
0 10 * * * cd /path/to/Binance && python3 scripts/update_binance_trading_data.py --update-metadata >> logs/metadata.log 2>&1
```

这样设置后，您只需要：

- 偶尔查看日志确认运行正常
- 有需要时运行菜单进行临时更新
- 有新币上市时手动运行选项 2

### 方案二：手动按需更新

每天运行一次交互式菜单：

```bash
python3 update_menu.py
```

- 每天选择 `1`（快速更新实时数据）
- 有新币上市时选择 `2`（更新静态字段）
- 需要查看特定币种时选择 `4`

### 方案三：混合方式

- 自动化：每 4 小时快速更新（cron）
- 手动：需要时运行菜单进行完整更新

## 命令行速查

如果您熟悉命令行，可以直接运行：

```bash
# 快速更新（只更新实时数据）
python3 scripts/update_binance_trading_data.py

# 更新静态字段（Funding Cycle + Categories + Index Composition）
python3 scripts/update_binance_trading_data.py --update-static-fields

# 完整更新（包括供应量）
python3 scripts/update_binance_trading_data.py --update-metadata

# 更新指定币种
python3 scripts/update_binance_trading_data.py BTC ETH SOL

# 更新指定币种 + 静态字段
python3 scripts/update_binance_trading_data.py --update-static-fields BTC ETH

# 查看帮助
python3 scripts/update_binance_trading_data.py --help
```

## 查看日志

```bash
# 实时查看最新日志
tail -f logs/update.log

# 查看最近的更新记录
tail -100 logs/update.log

# 搜索特定币种
grep "BTC" logs/update.log
```

## 常见问题

**Q: 运行后没有反应？**

- 请稍等，脚本在后台获取数据
- 第一次运行可能需要 10-20 分钟

**Q: 如何停止运行？**

- 按 `Ctrl + C` 中断

**Q: 更新失败怎么办？**

- 检查网络连接
- 查看日志文件：`logs/update.log`
- 重新运行菜单选择相同选项

**Q: 如何更新单个币种？**

- 选择菜单选项 `4`
- 输入币种符号（例如：BTC ETH）

## 开始使用

现在就试试：

```bash
python3 update_menu.py
```

选择 `1` 进行快速更新！
