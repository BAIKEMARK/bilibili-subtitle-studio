@echo off
setlocal EnableDelayedExpansion

title Bilibili Subtitle Studio Launcher

echo ========================================
echo   Bilibili Subtitle Studio 启动器
echo ========================================

REM 1. 检测 Python
python --version >nul 2>&1
pip install -r requirements.txt --disable-pip-version-check
if %errorlevel% neq 0 echo [WARN] 依赖安装失败，尝试继续...

echo.
echo =====================
echo  请选择运行模式:
echo  1. [命令行 CLI] - 默认
echo  2. [网页 WebUI]
echo =====================
set /p mode="请输入选项 [1/2]: "

if "%mode%"=="2" (
    echo [INFO] 正在启动 Streamlit Web 界面...
    streamlit run app.py
) else (
    echo [INFO] 正在启动命令行工具...
    python main.py
)

if %errorlevel% neq 0 (
    echo.
    echo [注意] 程序运行异常或被终止
    pause
)
