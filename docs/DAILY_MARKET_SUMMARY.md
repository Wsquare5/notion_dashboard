# 📊 每日行情总结功能

自动统计并记录每天涨跌幅最大的币种到 Notion 数据库。

---

## 🚀 快速开始

### 1️⃣ 在 Notion 中创建数据库

创建一个名为"每日行情"的数据库，包含以下字段：

- **Date** (日期类型) - 记录日期
- **涨跌幅** (文本类型) - 记录涨跌幅信息

### 2️⃣ 运行设置向导

```bash
python3 scripts/setup_daily_market.py
```

按照提示输入你的"每日行情"数据库 ID。

### 3️⃣ 测试运行

```bash
# 方式 1：使用快捷脚本
./daily_summary.sh

# 方式 2：直接运行 Python 脚本
python3 scripts/daily_market_summary.py
```

---

## 📊 功能说明

脚本会自动：

1. 从主数据库读取所有币种的当前数据
2. 按涨跌幅排序
3. 筛选出：
   - 🚀 涨幅榜 Top 5
   - 📉 跌幅榜 Top 5
4. 写入"每日行情"数据库

---

## ⏰ 设置定时任务

### 使用 crontab（推荐）

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天早上9点和晚上9点运行）
0 9 * * * cd /Users/wanjinwoo/Desktop/Work/trading/Binance && ./daily_summary.sh >> logs/daily_summary.log 2>&1
0 21 * * * cd /Users/wanjinwoo/Desktop/Work/trading/Binance && ./daily_summary.sh >> logs/daily_summary.log 2>&1
```

### 使用 launchd (macOS)

创建 `~/Library/LaunchAgents/com.binance.daily_summary.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.binance.daily_summary</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/wanjinwoo/Desktop/Work/trading/Binance/daily_summary.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Hour</key>
            <integer>9</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
        <dict>
            <key>Hour</key>
            <integer>21</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
    </array>
    <key>StandardOutPath</key>
    <string>/Users/wanjinwoo/Desktop/Work/trading/Binance/logs/daily_summary.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/wanjinwoo/Desktop/Work/trading/Binance/logs/daily_summary_error.log</string>
</dict>
</plist>
```

加载定时任务：

```bash
launchctl load ~/Library/LaunchAgents/com.binance.daily_summary.plist
```

---

## 📋 输出示例

```
================================================================================
📊 每日行情总结脚本
================================================================================
📥 正在读取主数据库...
✅ 读取到 534 个币种
📊 有效数据：534 个币种

📊 2025-11-10 09:00 行情总结
================================================================================

🚀 涨幅榜 Top 5:
  1. BTC          +15.23%  当前价格: $45123.45
      ✅ 已写入 Notion
  2. ETH          +12.56%  当前价格: $3456.78
      ✅ 已写入 Notion
  3. BNB          +10.34%  当前价格: $567.89
      ✅ 已写入 Notion
  4. SOL          +9.87%   当前价格: $123.45
      ✅ 已写入 Notion
  5. XRP          +8.56%   当前价格: $0.6789
      ✅ 已写入 Notion

📉 跌幅榜 Top 5:
  1. DOGE         -8.45%   当前价格: $0.0789
      ✅ 已写入 Notion
  2. SHIB         -7.23%   当前价格: $0.000012
      ✅ 已写入 Notion
  3. PEPE         -6.78%   当前价格: $0.000045
      ✅ 已写入 Notion
  4. FLOKI        -5.67%   当前价格: $0.000034
      ✅ 已写入 Notion
  5. BONK         -4.89%   当前价格: $0.000023
      ✅ 已写入 Notion

================================================================================
✅ 每日行情总结完成！
```

---

## 🔧 配置文件

配置文件位置：`config/daily_market_config.json`

```json
{
  "database_id": "your_database_id",
  "description": "每日行情数据库配置",
  "update_times": ["09:00", "21:00"],
  "top_n": 5
}
```

---

## 🆘 故障排除

### 问题 1：找不到配置文件

```bash
# 重新运行设置向导
python3 scripts/setup_daily_market.py
```

### 问题 2：Notion API 错误

检查：

- 数据库 ID 是否正确
- Notion Token 是否有权限访问该数据库
- 数据库字段名称是否正确（区分大小写）

### 问题 3：没有数据

确保主数据库有数据且包含 `Price Change%` 字段。

---

## 📈 未来功能（规划）

- [ ] 异常情况检测（交易量暴增、资金费率异常等）
- [ ] Telegram 推送通知
- [ ] 历史数据对比（真实 24h 变化）
- [ ] 市场整体趋势分析
- [ ] 自定义筛选条件
- [ ] 多种通知方式（邮件、微信等）

---

## 📝 更新日志

### v1.0.0 (2025-11-10)

- ✅ 基础功能实现
- ✅ 涨跌幅 Top 5 统计
- ✅ 写入 Notion 数据库
- ✅ 定时任务支持

---

**如有问题或建议，欢迎反馈！** 💬
