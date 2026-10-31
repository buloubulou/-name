@echo off
chcp 65001 >nul
title LobeAudio 音频同步服务
cd /d %~dp0

echo ============================================
echo   LobeAudio 音频同步服务
echo.
echo   启动后,用手机浏览器访问窗口里显示的地址
echo   保持本窗口开启,关闭窗口即停止服务
echo ============================================
echo.

python server.py

echo.
echo 服务已停止,按任意键退出...
pause >nul
