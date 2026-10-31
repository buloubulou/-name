@echo off
chcp 65001 >nul
title LobeAudio 安装程序
cd /d %~dp0

echo ============================================
echo   LobeAudio 音频同步工具 - 安装程序
echo ============================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [X] 未检测到 Python
    echo.
    echo 请先安装 Python 3.9 或更高版本:
    echo   https://www.python.org/downloads/
    echo.
    echo 安装时务必勾选 "Add Python to PATH" 选项!
    echo.
    pause
    exit /b 1
)

echo [1/2] 检测到 Python 版本:
python --version
echo.

echo [2/2] 正在安装依赖库(首次约需 1-2 分钟)...
python -m pip install numpy soundcard lameenc websockets -i https://pypi.tuna.tsinghua.edu.cn/simple --quiet

if %errorlevel% neq 0 (
    echo.
    echo [X] 安装失败,请检查网络后重新运行本文件
    echo     如果仍然失败,可尝试换源:
    echo     python -m pip install numpy soundcard lameenc websockets
    pause
    exit /b 1
)

echo.
echo ============================================
echo   [OK] 安装完成!
echo ============================================
echo.
echo 接下来:
echo   1. 双击 "启动服务.bat" 启动服务
echo   2. 手机连接同一个 WiFi
echo   3. 手机浏览器打开窗口里显示的地址
echo.
echo 如果手机打不开页面:
echo   右键 "放行防火墙.bat" - 以管理员身份运行
echo.
pause
