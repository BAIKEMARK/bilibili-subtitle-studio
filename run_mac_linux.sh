#!/bin/bash

# Bilibili Subtitle Studio - macOS/Linux 启动脚本
# 自动创建虚拟环境、安装依赖并运行程序

# 定义颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Bilibili Subtitle Studio 启动器 ===${NC}"

# 1. 检测 Python
if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo -e "${RED}❌ 错误: 未检测到 Python，请先安装 Python3。${NC}"
    exit 1
fi

echo -e "使用 Python: $($PYTHON_CMD --version)"

if [ ! -d ".venv" ]; then
    echo "正在创建虚拟环境 (.venv)..."
    python3 -m venv .venv
fi

# 激活虚拟环境并安装依赖
source .venv/bin/activate
echo "正在检查依赖更新..."
pip install -r requirements.txt --disable-pip-version-check

# 提供运行选项
echo "请选择运行模式:"
echo "1. 🖥️  命令行模式 (CLI) - 默认"
echo "2. 🌐 网页界面模式 (Web UI)"
read -p "请输入选项 [1-2]: " choice

if [ "$choice" == "2" ]; then
    echo "正在启动网页界面..."
    echo "提示: 按 Ctrl+C 停止运行"
    streamlit run app.py
else
    echo "正在启动命令行工具..."
    python main.py
fi

# 退出前暂停一下（防止终端直接关闭看不到报错）
if [ $? -ne 0 ]; then
    echo -e "${BLUE}----------------------------------------${NC}"
    echo -e "${RED}程序异常退出${NC}"
fi
