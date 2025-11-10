# 🚀 Binance to Notion - 快速交易数据同步

自动同步 Binance 交易数据到 Notion 数据库的高性能工具。

## ⚡ 核心特性

- **极速更新**：534个币种 8.1分钟完成（vs 旧版96分钟）= **11.9倍加速** 🚀
- **并行处理**：20个线程获取数据 + 10个线程写入 + 自动重试3次
- **完整数据**：现货/合约价格、交易量、资金费率、持仓量、基差、市值

---

## 🚀 快速开始

### 方式 1：快捷脚本（推荐）⭐

```bash
# 快速更新（8分钟）
./quick_update.sh

# 完整更新（包含元数据）
./full_update.sh
```

### 方式 2：全局命令（最方便）✨

```bash
# 1. 添加别名
cat aliases.sh >> ~/.zshrc && source ~/.zshrc

# 2. 之后可在任何目录运行：
bn-update    # 快速更新
bn-full      # 完整更新
bn-menu      # 交互式菜单
bn-log       # 查看日志
```

### 方式 3：直接命令

```bash
python3 update.py --workers 20
```

---

## ⏱️ 性能

| 操作 | 时间 | 说明 |
|------|------|------|
| 快速更新 | 8.1分钟 | 534个币种，11.9倍加速 ⚡ |
| 完整更新 | ~15分钟 | 包含CMC元数据 |

---

## 📊 更新内容

**交易数据**（每次更新）：现货/合约价格、交易量、资金费率、持仓量、基差、市值

**静态字段**（--update-metadata）：供应量、分类标签、资金周期

---

## 🔄 日常使用

```bash
# 每 4-8 小时运行一次
bn-update

# 或使用 crontab 自动化
0 */6 * * * cd /path/to/Binance && ./quick_update.sh
```

---

## 📖 更多文档

- [详细配置](docs/QUICK_START.md)
- [定时任务](docs/SCHEDULER_SETUP.md)
- [性能优化](docs/PERFORMANCE_OPTIMIZATION.md)

---

**Made with ❤️ for crypto traders**
