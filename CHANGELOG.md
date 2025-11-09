# 变更日志 - 静态字段更新功能

## v2.0 - 2025-11-09

### 🎯 主要变更

**将 Categories、Funding Cycle 和 Index Composition 合并为统一的静态字段更新选项**

### ✨ 新功能

#### 1. 新增命令行参数

- `--update-static-fields` - 更新静态字段（Funding Cycle + Categories + Index Composition）
- 不调用 CMC API，速度快
- 适合不定期运行（有新币上市或分类调整时）

#### 2. 更新策略分级

现在有三个清晰的更新级别：

**级别 1：快速更新（默认）**

```bash
python3 scripts/update_binance_trading_data.py
```

- 只更新实时数据
- 速度最快 (~10 分钟)
- 不调用任何外部 API

**级别 2：静态字段更新**

```bash
python3 scripts/update_binance_trading_data.py --update-static-fields
```

- 实时数据 + 静态字段
- 速度较快 (~15 分钟)
- 从 Binance API 获取，不调用 CMC API

**级别 3：完整更新**

```bash
python3 scripts/update_binance_trading_data.py --update-metadata
```

- 所有数据（实时 + 静态 + 供应量）
- 速度较慢 (~25 分钟)
- 调用 CMC API

### 🔧 代码修改

#### `scripts/update_binance_trading_data.py`

**函数签名更新：**

```python
def build_trading_properties(..., update_static_fields: bool = False)
```

**条件更新逻辑：**

- Funding Cycle: `if (update_static_fields or is_new_page)`
- Categories: `if (update_static_fields or is_new_page)`
- Index Composition: `if (update_static_fields or is_new_page)`

**参数处理：**

```python
update_static = args.update_static_fields or args.update_funding_cycle or args.update_metadata
```

**向后兼容：**

- `--update-funding-cycle` 仍然有效，映射到 `--update-static-fields`
- 帮助信息标记为 "Deprecated"

#### `update_menu.py`

**菜单选项调整：**

- 从 7 个选项减少到 6 个
- 选项 2: 更新静态字段
- 选项 5: 指定币种 + 静态字段
- 移除了独立的分类同步选项

**选项说明优化：**

- 更清晰地说明每个选项更新的内容
- 添加使用场景和推荐频率

### 📚 文档更新

#### 新增文档

1. **STATIC_FIELDS_UPDATE.md**

   - 静态字段概念说明
   - 三种更新模式详细对比
   - 使用策略和自动化建议
   - 字段更新频率建议表

2. **STATIC_FIELDS_SUMMARY.md**
   - 完整的功能总结
   - 更新内容对比表
   - 测试验证记录
   - 推荐自动化方案

#### 更新文档

1. **QUICK_START.md**
   - 更新菜单选项说明
   - 更新 cron 定时任务示例
   - 增加静态字段更新命令

### 🎨 用户体验改进

#### 1. 更清晰的概念划分

- **实时数据** - 每次都更新
- **静态字段** - 按需更新
- **供应量数据** - 定期更新

#### 2. 更灵活的控制

- 用户可以独立控制是否更新静态字段
- 减少不必要的 API 调用
- 提高更新效率

#### 3. 更合理的默认行为

- 快速更新不再更新 Categories（避免每次都调用 API）
- 静态字段只在需要时更新
- 完整更新包含所有内容

### 📊 性能对比

| 更新模式 | 耗时     | CMC API | Binance API | 推荐频率    |
| -------- | -------- | ------- | ----------- | ----------- |
| 快速更新 | ~10 分钟 | ❌      | ✅ (基础)   | 每 1-4 小时 |
| 静态字段 | ~15 分钟 | ❌      | ✅ (扩展)   | 每周/每月   |
| 完整更新 | ~25 分钟 | ✅      | ✅ (扩展)   | 每天 1 次   |

### 🔄 迁移指南

#### 从旧版本升级

**如果您使用了 cron 定时任务：**

旧配置：

```bash
0 */4 * * * python3 scripts/update_binance_trading_data.py
0 9 * * * python3 scripts/update_binance_trading_data.py --update-funding-cycle
0 10 * * * python3 scripts/update_binance_trading_data.py --update-metadata
```

新配置（推荐）：

```bash
# 每 4 小时快速更新
0 */4 * * * python3 scripts/update_binance_trading_data.py

# 每周一更新静态字段
0 9 * * 1 python3 scripts/update_binance_trading_data.py --update-static-fields

# 每天完整更新
0 10 * * * python3 scripts/update_binance_trading_data.py --update-metadata
```

**旧命令仍然有效：**

```bash
# 这个仍然工作（等同于 --update-static-fields）
python3 scripts/update_binance_trading_data.py --update-funding-cycle
```

### 🐛 Bug 修复

无

### ⚠️ 破坏性变更

无 - 完全向后兼容

### 📝 下一步

建议用户：

1. 测试新的 `--update-static-fields` 参数
2. 更新 cron 定时任务配置
3. 调整自动化策略以优化性能

---

## v1.0 - 之前的版本

### 功能

- 基本的数据更新功能
- `--update-metadata` 参数
- `--update-funding-cycle` 参数
- 交互式菜单（7 个选项）

### 问题

- Categories 每次都更新（不必要）
- Funding Cycle 每次都更新（不必要）
- Index Composition 每次都更新（不必要）
- 没有清晰的更新级别划分
