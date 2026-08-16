#!/bin/bash
# 便捷的自动修复脚本启动器

echo "🤖 Gemini CLI 自动代码执行和修复系统"
echo "======================================"

if [ $# -eq 0 ]; then
    echo "用法: $0 <python_file>"
    echo "示例: $0 my_script.py"
    exit 1
fi

PYTHON_FILE="$1"

if [ ! -f "$PYTHON_FILE" ]; then
    echo "❌ 错误：文件 '$PYTHON_FILE' 不存在"
    exit 1
fi

echo "📁 目标文件: $PYTHON_FILE"
echo "🚀 启动自动修复系统..."
echo ""

# 运行自动修复系统
python "$(dirname "$0")/gemini_auto_fixer.py" "$PYTHON_FILE"

echo ""
echo "✨ 完成！"