# 定时任务设置指南 - Binance 数据自动更新

## 概述

本指南介绍如何在 macOS 上设置每天自动更新 Binance 数据的定时任务。

## 文件说明

### 1. `scripts/daily_update.sh`

每日更新脚本，执行以下操作：

- 重新生成 perp-only 代币列表
- 更新所有 perp-only 代币的 Binance 交易数据到 Notion
- 重新计算 MC/FDV
- 记录详细日志（保留最近 30 天）

### 2. `com.binance.daily_update.plist`

macOS launchd 配置文件，用于定时执行脚本。

- **默认时间**: 每天上午 9:00
- **日志位置**: `logs/` 目录

## 快速设置步骤

### 方法一：使用 launchd（推荐 - macOS 原生）

#### 1. 测试脚本运行

```bash
cd /Users/wanjinwoo/Desktop/Work/trading/Binance
./scripts/daily_update.sh
```

如果成功，会在 `logs/` 目录生成日志文件。

#### 2. 安装 launchd 服务

```bash
# 复制 plist 文件到 LaunchAgents 目录
cp com.binance.daily_update.plist ~/Library/LaunchAgents/

# 加载服务
launchctl load ~/Library/LaunchAgents/com.binance.daily_update.plist

# 验证服务已加载
launchctl list | grep binance
```

#### 3. 手动测试运行

```bash
# 立即运行一次（不等到定时时间）
launchctl start com.binance.daily_update
```

#### 4. 查看日志

```bash
# 查看 launchd 系统日志
tail -f ~/Desktop/Work/trading/Binance/logs/launchd_stdout.log
tail -f ~/Desktop/Work/trading/Binance/logs/launchd_stderr.log

# 查看脚本生成的详细日志
ls -lt ~/Desktop/Work/trading/Binance/logs/daily_update_*.log | head -1
```

#### 5. 修改定时时间

编辑 `~/Library/LaunchAgents/com.binance.daily_update.plist`：

```xml
<!-- 改为每天下午 6:00 -->
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>18</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

修改后重新加载：

```bash
launchctl unload ~/Library/LaunchAgents/com.binance.daily_update.plist
launchctl load ~/Library/LaunchAgents/com.binance.daily_update.plist
```

#### 6. 停止/卸载服务

```bash
# 临时停止
launchctl stop com.binance.daily_update

# 完全卸载
launchctl unload ~/Library/LaunchAgents/com.binance.daily_update.plist
rm ~/Library/LaunchAgents/com.binance.daily_update.plist
```

---

### 方法二：使用 cron（备选方案）

#### 1. 编辑 crontab

```bash
crontab -e
```

#### 2. 添加定时任务

```bash
# 每天上午 9:00 运行
0 9 * * * /Users/wanjinwoo/Desktop/Work/trading/Binance/scripts/daily_update.sh

# 或者每天上午 9:00 和下午 6:00 各运行一次
0 9,18 * * * /Users/wanjinwoo/Desktop/Work/trading/Binance/scripts/daily_update.sh
```

#### 3. 验证 cron 任务

```bash
crontab -l
```

#### 4. 查看日志

```bash
ls -lt ~/Desktop/Work/trading/Binance/logs/daily_update_*.log | head -1
```

---

## 自定义配置

### 修改更新频率

在 `scripts/daily_update.sh` 中可以注释或修改步骤：

```bash
# 只更新 Binance 数据，不重新计算 MC/FDV
# 注释掉 Step 3

# 同时更新 CMC 元数据（如果需要）
# 在 Step 2 后添加：
# python3 scripts/sync_cmc_to_notion.py >> "$LOG_FILE" 2>&1
```

### 更新所有代币（不只是 perp-only）

修改 `scripts/daily_update.sh` 中的 Step 2：

```bash
# 改为更新所有代币
python3 scripts/update_binance_trading_data.py >> "$LOG_FILE" 2>&1
```

### 添加通知（可选）

在 `scripts/daily_update.sh` 末尾添加 macOS 通知：

```bash
# 发送系统通知
osascript -e 'display notification "Binance 数据更新完成" with title "定时任务"'
```

---

## 常见问题

### Q: 如何确认任务是否运行？

A: 检查 `logs/` 目录中的日志文件，每次运行都会生成带时间戳的日志。

### Q: 任务没有运行怎么办？

A:

1. 检查 `logs/launchd_stderr.log` 查看错误
2. 确认脚本有执行权限：`chmod +x scripts/daily_update.sh`
3. 手动运行脚本测试：`./scripts/daily_update.sh`
4. 检查 Python 环境是否正确配置

### Q: 如何接收失败通知？

A: 可以在脚本中添加邮件或其他通知方式，或者使用监控工具如 `healthchecks.io`。

### Q: 日志太多怎么办？

A: 脚本会自动删除 30 天前的日志。如需修改，编辑脚本最后的清理命令：

```bash
# 改为保留 7 天
find "$LOG_DIR" -name "daily_update_*.log" -mtime +7 -delete
```

---

## 推荐配置

**生产环境推荐**：

- 使用 launchd（更稳定，macOS 原生）
- 每天上午 9:00 运行（市场活跃时段）
- 保留 30 天日志用于排查问题
- 定期检查日志确保正常运行

**开发/测试**：

- 先手动运行几次确认脚本稳定
- 使用 `launchctl start` 测试定时任务
- 观察几天后再设置为长期运行

---

## 监控建议

1. **首周监控**：每天检查日志，确保任务正常运行
2. **定期抽查**：每周查看一次最新日志
3. **错误告警**：如果任务关键，可以添加外部监控服务

---

## 相关脚本

- `scripts/filter_perp_only.py` - 生成 perp-only 列表
- `scripts/update_binance_trading_data.py` - 更新 Binance 交易数据
- `scripts/recalculate_mc_fdv.py` - 重新计算市值和 FDV
- `scripts/sync_cmc_to_notion.py` - 同步 CMC 元数据（可选）

---

生成时间: 2025-10-26
