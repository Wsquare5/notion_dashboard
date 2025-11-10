# 🎯 日常更新操作指南

## 三种使用方式（从简单到复杂）

---

### ⭐ 方式 1：快捷脚本（最推荐）

```bash
# 1. 进入项目目录
cd /Users/wanjinwoo/Desktop/Work/trading/Binance

# 2. 快速更新（8分钟，只更新交易数据）
./quick_update.sh

# 3. 完整更新（15分钟，包含供应量等元数据）
./full_update.sh
```

**优点**：

- ✅ 简单直接，一个命令搞定
- ✅ 自动保存日志到 `logs/` 目录
- ✅ 显示开始和结束时间

---

### ✨ 方式 2：全局别名（最方便）

**一次性设置：**

```bash
# 添加别名到 ~/.zshrc
cat /Users/wanjinwoo/Desktop/Work/trading/Binance/aliases.sh >> ~/.zshrc
source ~/.zshrc
```

**之后在任何目录都可以运行：**

```bash
bn-update    # 快速更新（8分钟）
bn-full      # 完整更新（15分钟）
bn-menu      # 打开交互式菜单
bn-log       # 查看最新日志
bn-cd        # 快速切换到项目目录
```

**优点**：

- ✅ 在任何目录都能运行
- ✅ 命令简短易记
- ✅ 不用每次 cd 到项目目录

---

### 🔧 方式 3：直接命令（最灵活）

```bash
cd /Users/wanjinwoo/Desktop/Work/trading/Binance

# 快速更新所有币种
python3 update.py --workers 20

# 完整更新（包含元数据）
python3 update.py --workers 20 --update-metadata

# 只更新指定币种
python3 update.py BTC ETH BNB --workers 20

# 使用更多线程（更快但可能触发限速）
python3 update.py --workers 30
```

**优点**：

- ✅ 灵活控制参数
- ✅ 可以只更新指定币种
- ✅ 适合测试和调试

---

## 📅 推荐的更新频率

```bash
# 每 4-8 小时：快速更新
bn-update
# 或
./quick_update.sh

# 每天 1 次：完整更新（建议凌晨时段）
bn-full
# 或
./full_update.sh
```

---

## 🤖 自动化更新（定时任务）

### 使用 crontab

```bash
# 编辑定时任务
crontab -e

# 添加以下内容：
# 每 6 小时快速更新
0 */6 * * * cd /Users/wanjinwoo/Desktop/Work/trading/Binance && ./quick_update.sh

# 每天凌晨 2 点完整更新
0 2 * * * cd /Users/wanjinwoo/Desktop/Work/trading/Binance && ./full_update.sh
```

### 使用 launchd (macOS)

```bash
# 1. 复制 plist 文件
cp com.binance.daily_update.plist ~/Library/LaunchAgents/

# 2. 加载定时任务
launchctl load ~/Library/LaunchAgents/com.binance.daily_update.plist

# 3. 查看状态
launchctl list | grep binance
```

---

## 📊 查看更新日志

```bash
# 查看最新日志（方式1）
bn-log

# 查看最新日志（方式2）
tail -f logs/update_*.log

# 查看指定日志
cat logs/update_20251110_143052.log

# 查看最近的更新记录
ls -lt logs/ | head -10
```

---

## ❓ 常见操作

### 测试更新（只更新几个币种）

```bash
python3 update.py BTC ETH BNB --workers 5
```

### 查看脚本帮助

```bash
python3 update.py --help
```

### 交互式菜单（图形界面）

```bash
python3 menu.py
# 或
bn-menu
```

---

## 🎯 推荐工作流

**日常更新（推荐）：**

```bash
# 早上起来运行一次
bn-update

# 下午或晚上再运行一次
bn-update

# 睡前查看日志
bn-log
```

**配置定时任务后：**

```bash
# 什么都不用做，自动运行
# 偶尔检查一下日志即可
bn-log
```

---

## 💡 小贴士

1. **首次使用建议**：

   - 先用 `python3 update.py BTC ETH --workers 5` 测试
   - 确认没问题后再运行完整更新

2. **网络问题**：

   - 脚本有自动重试 3 次机制
   - 大部分网络错误会自动恢复
   - 失败的币种会在日志中显示

3. **更新时间**：

   - 快速更新：8.1 分钟（534 个币种）
   - 完整更新：~15 分钟（包含 CMC API 调用）

4. **日志管理**：
   - 日志自动保存在 `logs/` 目录
   - 定期清理旧日志：`rm logs/update_202411*.log`

---

**🎉 现在你可以轻松管理 Binance 数据更新了！**
