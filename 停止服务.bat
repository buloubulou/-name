@echo off
chcp 65001 >nul
title 停止 LobeAudio

echo 正在停止 LobeAudio 服务...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8787" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)
echo 已停止。
pause
