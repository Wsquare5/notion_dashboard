# Binance to Notion 更新工具 - 快捷命令
# 
# 将以下内容添加到你的 ~/.zshrc 文件中，然后运行 source ~/.zshrc
# 之后你就可以在任何目录直接运行这些命令：

# 基础路径
export BINANCE_NOTION_PATH="/Users/wanjinwoo/Desktop/Work/trading/Binance"

# 快捷命令别名
alias bn-update='cd $BINANCE_NOTION_PATH && ./quick_update.sh'
alias bn-full='cd $BINANCE_NOTION_PATH && ./full_update.sh'
alias bn-menu='cd $BINANCE_NOTION_PATH && python3 menu.py'
alias bn-log='ls -t $BINANCE_NOTION_PATH/logs/update_*.log 2>/dev/null | head -1 | xargs tail -100'
alias bn-cd='cd $BINANCE_NOTION_PATH'

# 使用说明：
# bn-update  : 快速更新（只更新交易数据，8分钟）
# bn-full    : 完整更新（包含元数据，稍慢）
# bn-menu    : 打开交互式菜单
# bn-log     : 查看最新日志
# bn-cd      : 切换到项目目录
