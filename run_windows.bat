@echo off
setlocal EnableDelayedExpansion

title Bilibili Subtitle Studio Launcher

echo ========================================
echo   Bilibili Subtitle Studio 启动器
echo ========================================

REM 1. 检测 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未检测到 Python，请先安装 Python 并添加到 PATH 环境变量。
    pause
    exit /b 1
)

REM 2. 创建虚拟环境
if not exist ".venv" (
    echo [INFO] 正在创建虚拟环境 (.venv)...
    python -m venv .venv
)

call .venv\Scripts\activate.bat
echo [INFO] 正在检查依赖...
pip install -r requirements.txt

python main.py

if %errorlevel% neq 0 (
    echo.
    echo [注意] 程序运行结束或异常退出
    pause
)
